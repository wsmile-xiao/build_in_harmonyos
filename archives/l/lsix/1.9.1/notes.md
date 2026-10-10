# lsix 1.9.1 适配笔记

## 编译环境

- 构建系统: custom（单文件 bash 脚本安装，无编译）
- 编译日期: 2026-09-29
- 编译器: N/A（纯脚本，无 ELF 产物，无需签名）
- 状态: built

## 上游形态判定

lsix **不是** C/C++ 库，是单文件 341 行 bash 脚本（`#!/usr/bin/env bash`）：

- 无 `configure`/`Makefile`/`CMakeLists.txt`，无构建阶段
- 无 `tests/` 目录、无 CI、无测试脚本 → 上游测试清点 = 0
- 唯一交付物就是脚本本身 + LICENSE
- 依赖仅为运行时依赖：bash（>= 4，上游对 bash 3 有 sanity check 并尝试 `exec bash`）、ImageMagick 6/7（`magick`/`montage`，IM6 自动 alias 到 `convert`/`montage`）、可选 `gsed`/`stty`

因此完全不能套用传统 C/C++ 库适配方式（无 toolchain、无 sysroot、无交叉编译、无 ELF 签名问题）。适配方式 = **打补丁 + 脚本安装**。

## 编译步骤

```bash
# 1. 下载源码（conandata.yml 记录 URL + sha256）
conan create . --version=1.9.1 -pr:b default -pr:h ohos-aarch64 -s:h build_type=Release
#    source() 下载（codeload URL 需显式 filename="lsix-1.9.1.tar.gz"）；build() 为空；
#    package() 将 lsix 装入 res/
# 2. test_package 验证（见下）
conan test ./test_package lsix/1.9.1 -pr:b default -pr:h ohos-aarch64 -s:h build_type=Release
```

`package()` 将脚本原样安装为 `res/lsix`（普通文件，非 bin/ 可执行），并安装 LICENSE 到 licenses/。因为脚本无 ELF 头，`package_id` 用 `info.clear()` 抹平（同一脚本跨 profile 通用）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanrun PATH 下无 `stty`，原版脚本在 `cleanup()` 与 `autodetect()` 处报 `stty: command not found` | HarmonyOS PC conanrun 环境仅含依赖包 bindir，不含 coreutils stty；上游假定 GNU 环境必有 stty。实测（未打补丁原版 + 无 stty PATH）：bash 无 `set -e`，报错**不致命**，脚本仍产出完整 218 字节 sixel 流、rc=0 —— 但每次运行 stderr 都有噪声，且行为依赖"报错恰好非致命"这一脆弱前提 | 补丁 0001：两处 `stty` 调用加 `command -v stty >/dev/null 2>&1 &&` 守卫，缺失时优雅跳过。价值 = 消除 stderr 噪声 + 不依赖脆弱前提（有 stty 的环境行为不变） |
| 2 | 无终端（CI）时 `exit 1` 被 `trap cleanup EXIT` 内 `exit 0` 覆盖，rc=0 | 上游 `trap cleanup SIGINT SIGHUP SIGABRT EXIT` 在 main 之前注册；line 119 的 `exit 1` 触发 EXIT trap → cleanup 打印 `\e\\` 并 `exit 0` | 不修改（上游行为，不构成包缺陷）；测试按真实契约断言 rc=0 + 2 字节 stdout + stderr 报错 |
| 3 | magick 缺失时 rc=1 能保留 | `exit 1`（line 67）在 trap 注册（line 79）之前触发 | 记录为行为边界断言（与问题 2 不对称，恰好可用于区分两种失败路径） |
| 4 | stderr 出现 `montage: UnableToOpenConfigureFile delegates.xml` 告警 | imagemagick-full 包内 gs/freetype 降级告警，非 lsix 缺陷 | 记录为可接受告警，不断言 stderr 为空 |
| 5 | `--help` 无此选项概念 | 上游把所有非目录参数当文件名（含以 `-` 开头的）传给 ImageMagick | 测试断言“不挂起 + rc=0 + stdout 恰 2 字节 ESC bSlash + stderr 含 ImageMagick `NoDecodeDelegateForThisImageFormat` 原文”，而非伪造 --help 输出 |
| 6 | 脚本自身目录被加入 conanrun PATH 后，`bash --version | grep "version 3"` 分支误触发风险 | 上游 bash 3 sanity check 对 `BASH_VERSINFO[0] -eq 3` 才触发，OHOS bash 5.3 直接通过 | 无需处理，验证记录在 test.sh A2 |
| 7 | 动画 GIF 无参数时 `file.gif[0]` 语法 | ImageMagick 读帧语法，IM7 magick 正常支持 | 无需处理 |
| 8 | 需确认补丁是否"必要"（若原版不 crash 则补丁无意义？） | 实测对照：未打补丁原版 + 无 stty PATH 下，bash 无 `set -e`，`stty: command not found` 非致命 → 仍产出 218 字节 sixel 流、rc=0，但 stderr 每次都带 2 条噪声 | 补丁保留：价值是消除噪声 + 行为不依赖"报错恰好非致命"的脆弱前提；test.sh G 组以"无 stty 噪声"作为补丁生效的直接断言 |

## 源码修改

补丁 `patches/0001-ohos-stty-optional.patch`（portability）：

- `cleanup()`: `stty echo` → `command -v stty >/dev/null 2>&1 && stty echo`
- `autodetect()`: `stty -echo` → `command -v stty >/dev/null 2>&1 && stty -echo`

共 2 处，均为最小侵入的守卫式修改，不改变有 stty 环境的行为。

## 依赖版本

- bash/5.3（解释器）
- imagemagick-full/7.1.2-23（magick、montage）
- 无构建依赖、无头文件、无库链接

## 验证结果

行为探针（本机直接执行 OHOS conan 包缓存中的 bash/magick，2026-09-29）：

```bash
# 纯红 4x4 PPM，强制 sixel，完整管线
LSIX_FORCE_SIXEL_SUPPORT=1 bash lsix red.ppm >red.out 2>red.err; echo rc=$?
# → rc=0, red.out 218 字节, 调色板 '#0;2;100;0;0'（纯红）, red.err 仅 delegates.xml 告警

# 双图 montage（红+蓝）
LSIX_FORCE_SIXEL_SUPPORT=1 bash lsix red.ppm blue.ppm >two.out 2>two.err
# → rc=0, two.out 266 字节, '#0;2;100;0;0' 红 / '#1;2;0;0;100' 蓝 / '#2;2;100;2;100' 白, 几何 756x126

# 无终端（不强制）
bash lsix red.ppm >noterm.out 2>noterm.err
# → rc=0, noterm.out 恰 2 字节 '\033\\', noterm.err 含 sixel 支持报错

# 无 magick（PATH 抽走）
env PATH=nopath bash lsix red.ppm
# → rc=1, stdout 空, stderr 首行 'Please install ImageMagick'

# --help（未知参数，强制 sixel）
LSIX_FORCE_SIXEL_SUPPORT=1 bash lsix --help
# → rc=0, stdout 恰 2 字节 '\033\\', stderr 含 montage 对文件名 --help 的
#   NoDecodeDelegateForThisImageFormat 报错 + MissingAnImageFilename, 不挂起

# G3 裸 shebang: env bash 可解析（OHOS env 存在）
env -i /bin/sh -c 'lsix' # 无 TERM/LD_LIBRARY_PATH 走降级路径，非包缺陷
```

test_package（真实消费场景，Conan 依赖 bash + imagemagick-full）：

```bash
conan test test_package lsix/1.9.1 -pr:b default -pr:h ohos-aarch64 -s:h build_type=Release
# → 7 组断言全部 PASS（A 布局/shebang/依赖, B 参数解析, C 缺 magick, D 无终端,
#    E 强制 sixel 管线, F 双图 montage, G 补丁无 stty 噪声）, rc=0
# conan create（含同款 test）与 conan test 两种入口均验证通过（2026-09-29）
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lsix/1.9.1` 脚本（包内 `res/lsix`） | 主交付物，补丁后版本 |
| `licenses/LICENSE` | GPL-3.0-or-later |
| `patches/0001-ohos-stty-optional.patch` | stty 可选化补丁 |
| `test_package/test.sh` | 7 组真实行为测试（A–G） |

## 知识定位（路径 A）

问题 1/8（stty 缺失，实测为非致命噪声而非 crash）在 ttygif 先例（imagemagick conanrun PATH 经验）和 E272（stty 缺失家族）中已有沉淀，lsix 的组合问题（脚本 + 无 stty + trap 行为）未超出已有知识覆盖范围，普适性不足以新增知识草稿或修改正式知识图谱。**走路径 A：仅完成交付物，不动知识库。**

## 注意事项

- 上游把所有参数当文件名（包括 `--help`），不要在其上构建 getopts 期望
- 无终端契约是 rc=0（不是 1），这是上游 trap 设计使然，不是包缺陷；不要“修复”它
- conanrun PATH 下 `bash --version` 检查（bash 3 分支）在 OHOS bash 5.3 下不会触发
- `realpath` 在 OHOS 可用，上游目录递归功能正常
- stderr 的 delegates.xml/gs/freetype 告警是 imagemagick-full 包的降级路径，非 lsix 问题
- 验证用的 profile 是 `-pr:h ohos-aarch64`（OHOS 6.0 / armv8 / clang 15），不是 `-pr:a=ohos-pc`
- B/D 组对 ESC 转义字节的断言用 `od -An -tx1` 十六进制精确比对（`1b5c`、流头 `1b50303b`），不依赖字符串 grep 的歧义
