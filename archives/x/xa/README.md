# xa

`xa`（上游项目 xa65）是一个面向 6502/65C02/65816 系列 CPU 的多遍交叉汇编器，支持直接产出可执行文件或 o65 可重定位目标文件，并随附完整的 o65 链接/重定位/信息工具链。它是 8 位复古计算与嵌入式（6502 系）开发中最常用的汇编器之一，也常用于 C64/CBM 程序、Apple II、NES 风格代码等场景。

上游 [github.com/fachat/xa65](https://github.com/fachat/xa65)（作者 André Fachat，现由 Cameron Kaiser 维护，GPL-2.0-or-later）。

## 功能概述

- `xa` — 主程序：两遍/多遍汇编器，支持 `.byte/.word` 等伪操作、宏与条件汇编、包含文件、列表输出（plain/html）、标签表导出、多套兼容语法（`-XMASM`/`-XCA65`/`-XC`）、字符集转换（`-O`）、可重定位模式（`-R -c`）
- `file65` — 打印 o65 文件头信息（模式位、各段地址/长度、栈大小等）
- `ldo65` — o65 目标文件链接器
- `reloc65` — o65 目标文件重定位器（可指定段基址）
- `uncpk` — C64 cpk 归档管理器（创建/追加/列出/解包）
- `printcbm` — Commodore BASIC 程序列表反汇编（上游已标记弃用，但功能完整）

## 依赖关系

- 编译依赖：无（ANSI C + 系统 libc，上游为纯 POSIX Makefile 工程）
- 运行依赖：无（六个二进制仅链接系统 libc；上游测试套件额外需要 `perl` 与 `make`）
- Conan 依赖：无（`requirements()` 为空，W0 检查通过）

## OHOS 适配要点

- 上游 Makefile 未经平台修改即可用 OHOS SDK clang（aarch64-linux-ohos / armv8）交叉编译，**零平台补丁、无平台宏**（R8/PF5 合规）
- 上游 GitHub tag 归档以 `README + xa/` 两级布局发布，配方的 `source()` 将 `xa/` 子目录提升为工程根后再打补丁与构建
- 上游 44 例 Perl 回归全部保留执行：设备上 **44/44 通过**。唯一改动是 `tests/harness` 与 `tests/hextool` 的 shebang 可移植性（OHOS 无 `/usr/bin/perl`，且内核对 `perl -s` 作为单参数传给 `env(1)`），补丁在脚本内复刻 `-s` 开关解析，**测试断言与期望产物零改动**；详见 [2.4.1/notes.md](2.4.1/notes.md) 与 [2.4.1/reports/test-report.md](2.4.1/reports/test-report.md)
- 上游 `make install` 依赖 `install(1)`（OHOS/toybox 无此命令），配方 `package()` 改为直接 copy 六个二进制与 6 份 man 手册
- 构建时间远低于默认超时预算（完整 conan create 约数分钟，44 例上游回归约 1 分钟）

## 参考资料

- 上游仓库与发布：<https://github.com/fachat/xa65>
- 项目主页（发布说明）：<https://www.floodgap.com/retrotech/xa/>
- man 手册：`share/man/man1/xa.1` 等 6 份
- o65 格式说明：见上游 `xa/README.1st` 与 `man/ldo65.1`

## 版本

- `2.4.1` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8）；2 个测试脚本可移植性补丁，上游 44/44 通过；见 [2.4.1/notes.md](2.4.1/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/xa` | 6502/65C02/65816 交叉汇编器（arm64 ELF） |
| `bin/file65` | o65 文件信息打印工具 |
| `bin/ldo65` | o65 链接器 |
| `bin/reloc65` | o65 重定位器 |
| `bin/uncpk` | C64 cpk 归档工具 |
| `bin/printcbm` | CBM BASIC 列表反汇编工具 |
| `share/man/man1/*.1` | 6 份 man 手册（xa/file65/ldo65/reloc65/uncpk/printcbm） |
