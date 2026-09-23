# libfreexl 2.0.0 适配笔记

## 编译环境

- 目标平台：HarmonyOS PC arm64
- 编译器：Clang 15
- 构建系统：Autotools
- Conan：OHOS 适配版（基线 2.29.1）
- 外部 Conan 依赖：expat/2.8.2、minizip/1.3.1
- iconv：平台 C 库提供（musl libc 内建），不引入额外 Conan 包
- 使用知识库：openharmony-compile-agent

## 构建配置

```text
--enable-static
--disable-shared
--disable-dependency-tracking
--build=aarch64-unknown-linux-gnu
--host=aarch64-linux-ohos
```

包交付静态库 `libfreexl.a`、公共头文件 `freexl.h`、pkg-config 文件 `freexl.pc`。

## HarmonyOS 适配

1. 上游 `config.guess` 不能识别 `HarmonyOS`，且 2.0.0 自带的 `config.sub` 不接受 OHOS 三元组（4 段 `aarch64-unknown-linux-ohos` 报 `machine 'aarch64-unknown-linux' not recognized`，因该旧脚本无 android-linux/linux-uclibc 锚点，严格正则全部落空）。配方按 E007（httperf/bwm-ng 先例，aalib 1.4p5 三段式补充）在 build() 内对源码树下全部 `config.guess/config.sub` 拷贝做通用补丁（`__OHOS__`/`HarmonyOS`/`ohos*` 回退/`linux-ohos*` 回退/`aarch64` CPU），并用 `sh config.sub aarch64-linux-ohos` 自测；再显式传入 build/host triplet；实际 C 编译器仍由存在性校验后的驱动提供。
2. `config.status` 使用 `umask 077` 创建临时目录时，在 HMDFS 权限模型下可能不可写。配方在构建前将 `configure` 中的 `umask 077` 精确替换为 `umask 022`。
3. 默认只交付静态库，避免 OHOS 共享库运行时路径问题。
4. `expat.h` 与 `minizip/unzip.h` 通过 `AutotoolsDeps` 注入已发布 Conan 包的头文件与库路径；`iconv.h` 与 `iconv()` 由平台 libc 满足，configure 的 `AC_SEARCH_LIBS(iconv)` 在 Linux/OHOS 上应落到 `none required`。
5. 未引入 `__OHOS__` 平台宏与补丁；适配全部通过配方级 configure 参数与依赖注入完成。
6. configure 调用前用 `VAR=val configure args` 内联前缀强制 `TMPDIR/TMP/TEMP`（build-local tmp）与 `CONFIG_SHELL/SHELL=/bin/sh`，优先级高于任何 conanbuild.sh 排序；并递归修补 build 树下所有 `conanbuild*.sh`，避免只读 `/tmp` 的 dash/clang 临时文件失败。
7. host 取 `aarch64-linux-ohos` 三段式（aalib 1.4p5 先例；旧 config.sub 无四段解析能力，三段式仅需 linux-ohos/ohos*/aarch64 通用补丁即可识别），build 取 `aarch64-unknown-linux-gnu` 以强制 Autoconf cross 路径，只编译链接 conftest 不执行。
8. 真机 profile 锁定的 `/data/service/hnp/bin/clang` 在预检沙箱内 ENOENT（`configure: .../clang: inaccessible or not found`，Error 77）。配方按 crunch-dxtc/clunk 先例做存在性校验：`--version` 探活通过的驱动才采用，优先级为 profile conf → `CC` 环境 → OHOS SDK LLVM 目录 → `PATH`，并经 `CC/CXX` 环境、内联 `VAR=val` 前缀与生成脚本同值替换三层强制生效；test_package 的 `conan_toolchain.cmake` 同法修补。仅替换驱动绝对路径，不改测试口径。

## 上游测试审计

上游源码树 `tests/` 目录通过 Automake `TESTS` 注册测试程序，`make check` 统一执行。
2.0.0 相对 1.0.6 新增 `check_excel_xlsx` 与 `check_calc_ods`（对应 xlsx/ods 新格式支持）。

| # | 测试程序 | 覆盖内容 |
|---|----------|----------|
| 1 | open_oocalc95 | 打开 OO Calc 95 样例 |
| 2 | open_oocalc97 | 打开 OO Calc 97 样例 |
| 3 | check_oocalc95 | 校验 OO Calc 95 内容 |
| 4 | check_oocalc97 | 校验 OO Calc 97 内容 |
| 5 | open_excel2003 | 打开 Excel 2003 样例 |
| 6 | check_excel2003_biff2 | 校验 BIFF2 工作簿 |
| 7 | check_excel2003_biff3 | 校验 BIFF3 工作簿 |
| 8 | check_excel2003_biff3_info | 校验 BIFF3 元信息 |
| 9 | check_excel2003_biff3_error_checks | 校验 BIFF3 错误处理 |
| 10 | check_excel2003_biff4 | 校验 BIFF4 工作簿 |
| 11 | check_excel2003_biff4_workbook | 校验 BIFF4 工作簿结构 |
| 12 | check_excel2003_biff5_workbook | 校验 BIFF5 工作簿结构 |
| 13 | check_excel2003_biff8 | 校验 BIFF8 工作簿 |
| 14 | check_excel2003_biff4_1904 | 校验 BIFF4 1904 日期体系 |
| 15 | walk_fat_oocalc97 | 遍历 OO Calc 97 FAT 链 |
| 16 | walk_sst_oocalc97 | 遍历 OO Calc 97 共享字符串表 |
| 17 | check_datetime_biff8 | 校验 BIFF8 日期时间单元格 |
| 18 | check_boolean_biff8 | 校验 BIFF8 布尔单元格 |
| 19 | check_oocalc97_intvalue | 校验 OO Calc 97 整数单元格 |
| 20 | check_excel_xlsx | 校验 xlsx 新格式读取 |
| 21 | check_calc_ods | 校验 ods 新格式读取 |

上游测试合计 21 个，来源：`tests/Makefile.am` 的 `TESTS` 注册与 `make check` 输出。配方在 `build()` 末尾执行 `make check`，未修改上游测试源码或断言。

## 消费端测试

`test_package/test_libfreexl.c` 通过 Conan 生成的 `libfreexl::libfreexl` CMake target 编译和链接，验证：

- `freexl_version()` 返回 `2.0.0`
- `freexl_open()` 对不存在的文件返回非 `FREEXL_OK` 错误码
- `freexl_close()` 能释放打开失败的句柄

消费端测试 1 个。真机实测计数以后端预检 evidence 为准，本轮不预填通过率。

---

**编写日期**：2026-09-14
**最终状态**：工作树已完成，真机预检待执行

## 2026-09-14 真机 upstream_test 21/21 FAIL 修复轮
- 现象：`make check` 21 个程序全 FAIL；摘要另带 `preflight.sh[306]: can't create temporary file /tmp/sh*.tmp: Read-only file system` 与 HMBS `[readonly_tmp]` 诊断。
- 排查：上游库 `src/*.c` 无 `/tmp/mktemp/tmpfile` 调用，`configure` 临时目录已用 `./confXXXXXX` 且配方已做 umask 022 + TMPDIR build-local 化；测试源码 `tests/*.c` 均以相对路径 `testdata/...` 打开样例文件（如 `freexl_open("testdata/simple2003.xls")`），而 Conan 为异地构建（build/tests 与 source/tests 分离），`build/tests/testdata` 不存在时全部报 OPEN ERROR 全败，与 21/21 现象吻合；只读 `/tmp` 为 shell 层告警，非本库直接原因。
- 修改（配方内，未改上游断言/数量）：`build()` 中 `make` 后、`make check` 前把 `source/tests/testdata` 整目录镜像到构建树下每个 `tests` 目录（含 `build-release/tests` 变体）；`make check` 失败时把 `test-suite.log` 及 tests 下 `.log` 按单行 `HMBS_TEST_DIAG` 输出（含 OPEN ERROR/shared library/testdata/FAIL 关键字），便于下轮直接定位。
- 证伪要求：下轮以真机 `test-suite.log` 实测为准；若仍全败，以新输出的 `HMBS_TEST_DIAG` 为据，不沿用本轮推断。

## 2026-09-14 package() install 失败修复轮
- 现象：build() 与 make check 21/21 已过，package() 的 autotools.install() 在 src 目录报 install 后 chmod 644 .../p//lib/libfreexl.a: No such file，install 本身无报错。
- 排查：configure/make/test 均用同一 build-local TMPDIR 且已过，顶部的 /tmp 只读告警为 preflight 包装器噪音；缺失的是交付物而非测试产物，指向 install 包装（runtime/bin/install + 无 -D 的 install -c 不建目录 / MKDIR_P 未生效），与编译器/测试无关。
- 修改（仅 package()，未改源码与测试口径）：预建 package/lib、lib/pkgconfig、include；autotools.install() 包 try/except，失败时从 build 树 src/.libs/libfreexl.a、源码 headers/freexl.h、build 树 freexl.pc 手工交付到对应 package 目录；双通道任一成功即交付，失败才抛错。
