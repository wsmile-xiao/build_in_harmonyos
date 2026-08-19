# arduino-mk 1.6.0 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile/脚本项目，无 C/C++ 源码需交叉编译)
- 编译日期: 2026-08-07
- 编译器: N/A (无需编译 C/C++ 代码)
- 状态: built

## 软件概述
arduino-mk (Arduino-Makefile) 是一套 .mk 文件和辅助 Python 脚本，用于从命令行编译和上传 Arduino 草图。
- GitHub: https://github.com/sudar/Arduino-Makefile
- Tag: 1.6.0 (注意：tag 不带 v 前缀)
- 正确下载 URL: https://github.com/sudar/Arduino-Makefile/archive/refs/tags/1.6.0.tar.gz

## 编译步骤

本项目是纯 Makefile/脚本包，无 configure/make 编译步骤。安装过程按照 Fedora spec 的布局手动完成：

1. 下载并解压源码 tarball
2. 手动安装文件到 staging 目录（$TEST_PREFIX）：
   - `*.mk` + `arduino-mk-vars.md` → `share/arduino/`
   - `bin/ard-reset-arduino` → `bin/` (Python 脚本，需 pySerial)
   - `bin/robotis-loader` → `bin/` (Python 脚本，需 pySerial)
   - `ard-reset-arduino.1`, `robotis-loader.1` → `share/man/man1/`
   - `licence.txt` → `share/doc/arduino-mk/`
   - `examples/` → `share/doc/arduino-mk/examples/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 404 | 任务给的 URL 用了 v1.6.0 前缀，实际 tag 是 1.6.0 | 改用 https://github.com/sudar/Arduino-Makefile/archive/refs/tags/1.6.0.tar.gz |
| 2 | init-build 嵌套源码误提升 | 脚本将 examples/ATtinyBlink 误判为主源码 | 手动重新解压 tarball 到 .orig 和 .work 目录（--strip-components=1） |
| 3 | install 命令不可用 | 鸿蒙环境无 install 命令 | 使用 cp + chmod 替代 |

## 源码修改

无源码修改。本项目是纯脚本/Makefile 包，无需适配 C/C++ 代码。

## 依赖版本

- Python 3 (ard-reset-arduino 和 robotis-loader 脚本依赖)
- pySerial (Python 包，通过 pip 安装，非 conan 依赖)
- Arduino IDE (外部工具，非 conan 依赖)

## 验证结果

```bash
# 验证安装产物
find $TEST_PREFIX -type f | wc -l  # 47 个文件
ls $TEST_PREFIX/share/arduino/     # 6 个 .mk 文件 + arduino-mk-vars.md
ls $TEST_PREFIX/bin/               # ard-reset-arduino, robotis-loader
ls $TEST_PREFIX/share/man/man1/    # 2 个 man page
```

## 构建产物类型

- 命令行工具：ard-reset-arduino, robotis-loader (Python 脚本) → 需要 commands.json (R38)
- 数据文件：*.mk (Makefile include 文件), arduino-mk-vars.md
- 文档：examples/, licence.txt, man pages

## 注意事项

- 上游测试（tests/script/runtests.sh）需要 Arduino IDE 和 avr-gcc 工具链，无法在 HarmonyOS 平台运行
- ard-reset-arduino 和 robotis-loader 需要 pySerial，运行时通过 pip 安装
- conandata.yml 中的 URL 必须使用正确的 tag（1.6.0 不带 v 前缀）
---

**编译结束**: 2026-08-07 13:01
**最终状态**: built
