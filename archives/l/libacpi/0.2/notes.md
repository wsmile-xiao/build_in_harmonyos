# libacpi 0.2 — HarmonyOS PC 适配说明

## 概况

libacpi 是通用 ACPI 用户态库：从 `/proc/acpi`（老内核）或
`/sys/class/power_supply`、`/sys/class/thermal` 读取电池、AC 适配器、热区与风扇信息，
通过 `init_acpi_*`/`read_acpi_*` 与全局数组 `batteries`/`thermals`/`fans` 暴露给上层程序。

- 上游：http://www.ngolde.de/libacpi.html （源码来源为 Debian orig tarball）
- 构建：纯 Makefile（无 configure/autotools，所有开关在 `config.mk`）
- 依赖：无（仅 libc）
- 许可证：MIT

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | Makefile 变量注入 | 以 make 变量方式传入 `CC`/`LD`/`AR`/`RANLIB`/`CFLAGS`/`SOFLAGS`（`libmoe` 同法）；`AR`/`RANLIB` 用 `llvm-ar`/`llvm-ranlib` |
| 2 | **clang 15 的 `-fno-common`** | `libacpi.h` 直接**定义** `battery_t batteries[MAX_ITEMS]` 等全局数组（没有 `extern`）。2007 年的 gcc 默认 `-fcommon` 所以无事；现代 clang 默认 `-fno-common`，库与任何包含该头的消费者都会各产生一份同名符号 → 链接失败。库加 `-fcommon`，消费者（`test_package/CMakeLists.txt`）同样加 `-fcommon` |
| 3 | 安装布局 | 上游 `install` 规则基于 `${DESTDIR}${PREFIX}` → 传 `DESTDIR=` 与 `PREFIX=<package_folder>` 直接装入包目录；保留 `include/libacpi.h`、`lib/libacpi.a`、`lib/libacpi.so.0`(+`libacpi.so` 软链)、`share/man/man3/libacpi.3` |
| 4 | 精简包内容 | 上游会把 `AUTHORS/CHANGES/README/LICENSE/doc/**` 装到 `share/doc/libacpi`、把 demo 装到 `bin/`；本配方只保留头/库/man 与 `licenses/LICENSE`（demo 在 `build()` 中已执行留证，不作为命令行工具发布，避免 L0k 的 CLI 门禁） |

## 测试

### 上游测试（build() 内执行，真机）

上游无单元测试框架，只有 `test-libacpi.c`：它调用 `check_acpi_support()`，按设计在
既无 `/proc/acpi` 也无 `/sys/class/power_supply` 时打印
`No acpi support for your system?` 并返回 **-1**（设计行为，不是缺陷）。
配方在 `build()` 中编译并执行它，日志写入 `upstream-test-libacpi.log`，结果按
`executed_with_environment_limitation` 如实申报。

### 消费者测试（test_package，CMake）

`test_package/test_libacpi_consumer.c` 共 24 条断言，全部与机器无关：

- 常量契约：`PROC_ACPI` 路径、`LINE_MAX=256`、`MAX_ITEMS=10`、缓冲区尺寸关系
- 错误码枚举：`SUCCESS=0`、`NOT_SUPPORTED=-1`、`ALLOC_ERR=-2`、`NOT_PRESENT=-3`、`DISABLED=-4`、`ITEM_EXCEED=-5`
- `power_state_t`：`P_AC=0`、`P_BATT=1`、`P_ERR=2`
- 导出数组：`batteries`/`thermals`/`fans` 均为 `MAX_ITEMS` 个元素
- 行为契约：`check_acpi_support()` 只返回 `SUCCESS`/`NOT_SUPPORTED`；四个 `init_acpi_*` 只返回文档定义的返回码集合；发现数量落在 `[0, MAX_ITEMS]`；`ac_state` 始终处于 `power_state_t` 之内；适配器存在时 `read_acpi_acstate()` 保留状态文件路径

## 已知限制

- 具体数值（电池百分比、温度等）取决于运行机器的内核接口，故不断言具体值。
- 热区/风扇在上游 demo 中同样受环境限制；相关返回码已按契约覆盖。
