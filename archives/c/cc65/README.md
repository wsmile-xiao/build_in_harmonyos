# cc65 — OpenHarmony 编译档案

## 软件简介
cc65 是一套面向 6502 系列 CPU（包括 MOS 6502、WDC 65C02、WDC 65C816 等）的 C 编译器开发套件，最初由 John R. Dye 移植自 Ron Cain 的 Small-C，现由社区维护。它包含 C 编译器、宏汇编器、链接器、库管理器等工具，支持 Commodore 64、Apple II、NES、Atari 等多种 6502 平台。

## 功能概述
- **cc65**：C 编译器，将 C 源码编译为 6502 汇编
- **ca65**：宏汇编器，将汇编源码汇编为目标文件
- **co65**：目标文件格式转换器
- **cl65**：编译驱动器，自动调用 cc65/ca65/ld65 完成编译链接
- **ld65**：链接器，将目标文件链接为可执行映像
- **ar65**：归档工具，管理静态库
- **da65**：反汇编器
- **od65**：目标文件转储工具
- **grc65**：GEOS 资源编译器
- **chrcvt65**：字符集转换工具
- **sim65**：6502 模拟器
- **sp65**：sprite/图片转换工具

## OHOS 适配要点
- Makefile 构建系统，使用 `CC=$(CROSS_COMPILE)gcc`，通过 `make CC={conan_cc}` 覆盖（R33）
- 仅构建 `src/` 目录（编译器工具链），`libsrc/`（6502 目标库）需运行刚构建的 cc65 工具，交叉编译环境跳过
- 无 configure 阶段，无平台识别问题
- 无外部依赖，自包含构建

## 依赖关系
- 无外部依赖

## 使用方式
```bash
# 查看 cc65 版本
cc65 --version

# 编译 C 源码为 6502 汇编（不链接）
cc65 -c test.c

# 使用 cl65 驱动器编译并链接（需目标库）
cl65 -t c64 test.c

# 查看支持的架构
cc65 --help
```

## 参考资料
- [cc65 官方网站](https://cc65.github.io/cc65/)
- [cc65 GitHub 仓库](https://github.com/cc65/cc65)
