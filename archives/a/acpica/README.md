# acpica

ACPICA (ACPI Component Architecture) 是 Intel 开发的 ACPI (Advanced Configuration and Power Interface) 子系统实现，提供一组工具用于编译、反汇编和分析 ACPI 表。

## 主要工具

| 工具 | 功能 |
|------|------|
| iasl | ACPI ASL 编译器/反汇编器（核心工具） |
| acpixtract | 从 acpidump 输出中提取二进制 ACPI 表 |
| acpibin | ACPI 二进制表比较和分析 |
| acpidump | 转_dump 系统 ACPI 表 |
| acpiexec | AML 执行/调试器 |
| acpihelp | ACPI 名称和编码查询 |
| acpisrc | ACPI 源码转换工具 |

## 编译信息

- 构建系统: 自定义 Makefile（非 autotools/cmake）
- 编译参数: `make NOWERROR=TRUE ACPI_HOST=_LINUX`
- 安装参数: `make install NOWERROR=TRUE ACPI_HOST=_LINUX PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX`
- 无外部依赖（需要 bison, flex, m4）

## 许可证

BSD-2-Clause 或 Intel-ACPI