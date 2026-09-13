# detenc

detenc 是一个轻量级、低内存占用的启发式字符编码检测命令行工具，用于判断西欧文本文件的字符编码。

## 功能概述

- 逐文件检测编码，可识别：US-ASCII、UTF-8、UTF-16BE、UTF-16LE、ISO-8859-15、WINDOWS-1252，无法判定时报 UNKNOWN
- 能区分 ISO-8859-15 与 WINDOWS-1252（含 € 符号差异）
- `-q` 仅输出编码名；`-o` 在 UNKNOWN 时输出首个不一致字节的偏移；`-v` 输出版本
- 流式扫描，内存占用极低（上游用于 GB 级数据源规范化）

## OHOS 适配

- 构建系统为纯 Makefile（无 configure/cmake）。`src/Makefile` 硬编码 `CC = gcc`，
  而 Makefile 内赋值优先于环境变量，必须以 make 命令行变量 `CC=clang` 覆盖。
- 上游 CFLAGS 仅 `-Wall`，配方补 `-O2`。
- 上游测试套件为 Ruby minitest（`make check` = 构建 + `cd test && rake test`）。
  测试文件使用 minitest 5.x 已移除的旧拼写 `MiniTest::Test`，需大小写修正补丁
  （与 Alpine APKBUILD 的 minitest.patch 思路一致）。
- 测试经 Ruby `Tempfile` 写入临时目录，依赖 TMPDIR；OHOS /tmp 只读（E002），
  构建时将 TMPDIR 显式指向 Conan 构建目录。
- 零第三方依赖，仅使用 stdio/string/unistd，musl 安全；无平台探测、特殊系统
  调用，不使用 /tmp。

## 依赖关系

- 编译依赖：无（仅 C 标准库）
- 运行依赖：无
- 上游测试依赖：ruby（>= 3.x，含内置 minitest）、rake、GNU make

## 参考资料

- 上游仓库：https://github.com/reevoo/detenc
- 许可证：MIT（源码内 COPYING）
