# tzdiff 1.2.1 适配笔记

## 编译环境
- 构建系统: 无（纯 POSIX sh 脚本，headeronly/脚本工具族，只装不编）
- 编译日期: 2026-09-25
- 编译器: 不涉及（产物无 ELF）
- 状态: built（conan-verify G1-G4 通过，finish W3 通过）
- 源码: https://github.com/belgianbeer/tzdiff/archive/refs/tags/1.2.1.tar.gz
- SHA256: `3438af02d6f808e9984e1746d5fd2e4bbf6e53cdb866fc0d4ded74a382d48d62`

## 软件类型判定（R47 语言预检）
- 上游只有单个 `tzdiff`（`#!/bin/sh`，无扩展名）+ `tzdiff.1` man 页，无 manifest、
  无构建系统；lang_detect 统计不到源文件 → `detected=other`。
- 按已合入先例 ausweisapp-nftrules/2.5.1、boot-info-script/0.78 的范式，以
  `OHPCD_LANG=other` 声明任务语言通过预检（task=other, detected=other）。
  CI 能力矩阵：bash/sh 脚本类 ✅。

## 依赖（W0）
- `tzdata/2026.3`（IANA TZif 数据，Python 数据包形态）：
  `conan download tzdata/2026.3 -r=ohpcd --only-recipe` → recipe rev
  `f938db83df06a8229db8f2aa71ff7c6c`；二进制 `conan download "tzdata/2026.3:*"` 成功。
- 以 `requires(..., visible=False)` 引入：仅在 package() 时复制 zoneinfo，不向消费者传递。

## 鸿蒙平台差异（适配根因）

| # | 问题 | 根因（实证） | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `cd /usr/share/zoneinfo \|\| exit`，鸿蒙上直接退出 | 鸿蒙 PC 无展开的 Olson 目录。OHOS NDK `libc.a` 字符串显示 musl 只查打包格式 `/etc/tzdata_distro/tzdata`、`/etc/zoneinfo/tzdata`、`/usr/share/zoneinfo/tzdata` 与 `persist.time.timezone` 参数（与 E315 设备调查一致） | 补丁：`cd "${TZDIR:-/usr/share/zoneinfo}"`；package() 把 tzdata/2026.3 的 604 个 TZif 文件放到 `share/zoneinfo`；wrapper 在 TZDIR 未设置时指向它 |
| 2 | 按名字 `TZ=Asia/Tokyo` 在 OHOS musl 上不可用 | OHOS musl 按名字只查上面的打包库，不看 TZDIR | 补丁：`TZ=${zoneinfo}/${2}` 传绝对路径。探针 `probe.c` 用 NDK clang 静态链接、qemu-aarch64 实跑：`TZ=<zoneinfo>/Asia/Tokyo -> 1970-01-01 09:00 JST`、`TZ=Asia/Tokyo -> 00:00 "Asia"`（名字查找失败） |
| 3 | `date --date=@N` 在鸿蒙上报 `Unknown option 'date=@0'` | 鸿蒙用户态 `date` 是 toybox；toybox 0.8.14 `date --version` 返回 0（所以上游判定为 GNU 分支），但没有 `--date` 长选项 | 补丁：改用 GNU/toybox 共同子集 `date -d` |
| 4 | `-t 2024-07-01T09:00Z` 在 toybox 下 `bad date` | toybox `date -d` 不接受 ISO `T` 分隔，接受空格 | 补丁：`-t` 值中 `数字T数字` → `数字 数字`（GNU 同样接受，行为不变） |
| 5 | shebang/安装路径 | 鸿蒙无 /bin/bash，且可能没有 `/usr/bin/env`（E037）；hnp 部署可能以软链进 PATH | bin/tzdiff 为 `#!/bin/sh` wrapper（与上游 shebang 一致），`readlink -f` 解析真实位置，`exec sh libexec/tzdiff/tzdiff`（wrapper 结构同 acme.sh/boot-info-script 先例） |

## 源码修改
- `patches/0001-tzdiff.patch`（+7/-5，refresh-patch --auto 生成）：上表 1-4；时区参数本身是绝对路径时原样使用（不拼 zoneinfo 前缀，保持上游行为）。
  不含 `__OHOS__` 或任何平台宏；Linux/GNU 行为不变（TZDIR 缺省仍是 `/usr/share/zoneinfo`，
  `date -d` 与 `--date` 等价）；macOS/BSD（`date -j`）分支未改。

## 上游测试清点（R51 三步法）
1. 清点：1.2.1 tag 全部文件 = `tzdiff`、`tzdiff.1`、`README.md`、`LICENSE`、`.gitignore`
   （`git clone` 后 `ls -a` 实查）。无 `tests/` 目录、无 Makefile/check 目标、
   无 `.github/workflows`；ctest/pytest 注册数 0。**上游用例数 N=0**。
2. 运行：无可运行的上游测试。
3. 回填：上游 0/0；由 test_package 补全功能测试（见下）。

## 适配后测试（test_package/test_tzdiff.sh，8 个用例）

| # | 用例 | 类型 |
|---|------|------|
| 1 | `tzdiff -v` = `tzdiff 1.2.1` | 功能 |
| 2 | 随包 `share/zoneinfo/Asia/Tokyo` 头 4 字节 = `TZif` | 功能 |
| 3 | `-HH -N -n 3 -t 2024-07-01T09:00Z <绝对路径>/Asia/Tokyo America/New_York` 三行逐字比对（JST/EDT；绝对路径参数原样使用） | 功能 |
| 4 | `-t 2024-03-10T06:00Z America/New_York`：01:00 EST → 03:00 EDT（真实 DST 规则） | 功能 |
| 5 | 短名 `Tokyo` 在 zoneinfo 树内解析 + 表头行 | 功能 |
| 6 | **[鸿蒙特有]** TZDIR 契约：未设置 → 随包数据（鸿蒙无系统 Olson 树）；伪造 TZDIR 必须失败而非静默回退；显式 TZDIR 生效 | 鸿蒙特有 |
| 7 | 本地时间列 = 系统 `date -d @N` 同一时刻的输出 | 功能 |
| 8 | 通过 PATH 调用 wrapper（shebang + `command -v` 分支） | 功能 |

统计：上游 0 → 适配后 8（功能 7 + **鸿蒙特有 N=1**：用例 6）。用例 6 专测本次适配引入的契约——鸿蒙无系统
Olson 树时必须使用随包数据、伪造 TZDIR 必须失败；用例 7 在任何平台都成立，按保守口径计入功能测试。

### 执行证据
- conan-verify G2（`conan create -pr:h/-pr:b ci/conan/profiles/ohos-aarch64`）内 test_package：
  `[pass] 8/8 assertions (date=other, system zoneinfo=present)`（宿主 GNU 用户态）。
- toybox 用户态模拟（`date/env/sed/head/readlink/dirname/tr/wc/ls` 全部指向 toybox 0.8.14，
  sh=dash / bash 各一次）：`[pass] 8/8 assertions (date=toybox, ...)`。
- 鸿蒙形态模拟（toybox 用户态 + `unshare -m` 私有命名空间把 `/usr/share/zoneinfo` 遮成空 tmpfs）：
  打包产物 8/8 通过；同环境上游原脚本 `rc=2`（找不到时区）。
- 同 toybox 环境下上游原脚本：`date: Unknown option 'date=2024-07-01T09:00Z'`，rc=1。
- OHOS musl 绝对路径 TZ：静态探针 qemu-aarch64 实跑（见上表 #2）。

### 如实说明
- 产物无 ELF（纯 sh 脚本 + 数据），qemu 不适用于脚本本身；本机 x86 runner 上的 toybox
  是 x86_64 构建，**不等于在鸿蒙真机上实跑**。CI profile 使用设备路径
  `/data/service/hnp/bin`，CI 上 test_package 在鸿蒙用户态运行时用例 6/7 即为真机验证，结果以 CI 为准。

## 注意事项
- 随包 zoneinfo 固定为 tzdata 2026.3；用户可 `export TZDIR=<olson 目录>` 改用其他数据。
- 本地时间列依赖系统 `date` 自身的时区设置（鸿蒙由系统设置决定），tzdiff 不改写它。
---

**编译结束**: 2026-09-25 22:40
**最终状态**: built
