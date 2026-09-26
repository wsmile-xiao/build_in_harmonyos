# E6402 — 鸿蒙上 shell 时区工具失效：无 Olson 目录 + musl 按名字只查打包 tzdata + toybox date 无 `--date`

## 错误特征
```
date: Unknown option 'date=2024-07-01T09:00Z' (see "date --help")
date: bad date 2024-07-01T09:00
sh: cd: can't cd to /usr/share/zoneinfo
```
或无报错但时区列退化成 UTC、缩写显示为 `Asia` 之类的名字片段。

## 触发条件
- 构建系统: 无（脚本类工具），运行期 / test_package 阶段暴露
- 阶段: runtime / testing
- 脚本假设 GNU date + glibc 式 `/usr/share/zoneinfo` 目录（如 tzdiff 1.2.1）

## 根因分析
1. **无 Olson 目录**：OHOS NDK `libc.a` 中的时区路径只有 `/etc/tzdata_distro/tzdata`、
   `/etc/zoneinfo/tzdata`、`/usr/share/zoneinfo/tzdata`（Android 式打包格式）及
   `persist.time.timezone` 参数，没有展开的 `Area/City` 文件树（与 E315 设备调查一致）。
2. **musl 按名字只查打包库**：`TZ=Asia/Tokyo` 不看 TZDIR；`TZ=/绝对路径/Asia/Tokyo`（TZif）可用。
   NDK clang 静态探针经 qemu-aarch64 实测：绝对路径 → `09:00 JST`；按名字 → `00:00 Asia`。
3. **toybox date**：`date --version` 返回 0，脚本的 GNU 探测会走 GNU 分支；但 toybox 0.8.14
   没有 `--date` 长选项，且 `-d` 不接受 ISO `T` 分隔（接受空格形式与 `@epoch`）。

## 解决方案

### 推荐方案（不含平台宏）
- 补丁：`cd "${TZDIR:-/usr/share/zoneinfo}"`；`TZ=${zoneinfo}/${name}` 传绝对路径（参数本身已是绝对路径时原样使用，保持上游行为）；
  `date --date=X` → `date -d X`，`-t` 值中 `数字T数字` → `数字 数字`。
- 配方：`requires("tzdata/2026.3", visible=False)`，package() 把其 `tzdata/zoneinfo` 的 TZif
  文件复制到 `share/zoneinfo`；`bin/` 下 `#!/bin/sh` wrapper（E037：鸿蒙可能无 `/usr/bin/env`）用 `readlink -f` 定位前缀，
  TZDIR 未设置时指向随包数据，再 `exec sh libexec/<tool>`。
- 参考：`archives/t/tzdiff/1.2.1/`。

### 回退方案
脚本重度依赖 GNU date 自然语言解析时，依赖制品仓 GNU coreutils 并在 wrapper 前置 PATH；
时区数据仍需随包 + 绝对路径 TZ。

### 禁止做法
- ❌ 硬编码 `TZ=UTC` / `TZ=Asia/Shanghai`：不报错但换算全错。
- ❌ 在构建机/设备上 `mkdir`/`ln -s` 出 `/usr/share/zoneinfo`：不可复现，系统分区只读。
- ❌ 用 `__OHOS__` / `-D__OHOS__` 分支：共同子集方案在所有平台行为一致（R8/PF5）。

## 验证
```bash
env -i PATH=<toybox applets> TZDIR=<pkg>/share/zoneinfo \
  sh <pkg>/libexec/tzdiff/tzdiff -HH -N -n 1 -t 2024-07-01T09:00Z Asia/Tokyo
# 期望: 2024-07-01 18:00 JST
```

## 查重
- E315：R 语言的鸿蒙时区契约（param + R 自带 zoneinfo），不涉及 shell/toybox date 与绝对路径 TZ。
- E010 / E402 / DRAFT-ohos-toybox-ln-long-option：toybox 的 sed / gzip / ln 长选项问题，未覆盖 `date`。
- DRAFT-11103-teseq-mdate-sh-iso-date-vti：mdate-sh 解析 `ls` 输出，与 date/时区无关。

## 关联条目
- 相关: E315, E010, E402, DRAFT-ohos-toybox-ln-long-option
