- **三方库名称**：libxpm
- **上游版本**：libXpm 3.5.17（对应 `libXpm.so.4`）
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxpm
- **适配路径**：路径 A（基础适配） + 知识库扩展（复用 X11 家族 autotools 模式）
- **使用知识库**：OHOS 下 X.Org autotools 库的通用工具链修复模式（libxkbfile/libxcb/libxcursor 同法）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 5 | 来源：libXpm 3.5.17 release tarball `test/Makefile.am`；`check_PROGRAMS = XpmCreate XpmMisc XpmRead XpmWrite rgb`（受 `if ENABLE_UNIT_TESTS if HAVE_GLIB` 条件控制），`TESTS=$(check_PROGRAMS)`，TAP 框架（`tap-test` + `tap-driver.sh`） |
| 集成测试 | 0 | 无独立集成测试套件 |
| 其他测试 | 0 | 上游仅生成库与 cxpm/sxpm 命令行工具 |
| **合计** | **5** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 4 | 从上游集成 | 上游 4 个 display-independent 单元测试（`XpmCreate`/`XpmMisc`/`XpmRead`/`XpmWrite`）源码未修改 vendored 至 `test_package/upstream/test/`，链接已发布 glib/2.88.0 在 OHOS CI 实跑通过（见「验证结果」段）；`rgb` 判 N/A |
| 集成测试 | 0 | 不变 | 上游无独立集成测试套件 |
| 鸿蒙特有测试 | 2 | 新增 | `api_surface.c`（34 个导出符号强类型重定位）+ `version_contract.c`（版本宏 + 结构体布局 + 18 个函数签名契约 + XPM 解析/写出/读回/重生成 round-trip），均不依赖 X server |
| **合计** | **6** | **+6** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（5 个：`XpmCreate` / `XpmMisc` / `XpmRead` / `XpmWrite` / `rgb`）
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> **上游测试集成情况说明**：上游 `test/Makefile.am` 的 5 个 `check_PROGRAMS` 受 `if ENABLE_UNIT_TESTS if HAVE_GLIB` 条件控制，依赖 **GLib** 测试框架（`g_test_init`/`g_assert`/`g_test_run`）+ `pixmaps/` 测试数据（经 `G_TEST_SRCDIR`/`G_TEST_DIST` 定位）。GLib 已由 PR #6619 鸿蒙化发布（glib/2.88.0，default shared=False 静态构建，package_info 提供 `GLib::GLib` 目标）。本包 `test_package` 将上游 4 个 display-independent 测试源码未修改 vendored 至 `upstream/test/`（`XpmCreate.c`/`XpmMisc.c`/`XpmRead.c`/`XpmWrite.c` + `TestAllFiles.h`/`CompareXpmImage.h` + `pixmaps/` 数据 + 最小 `config.h` 等价宏），链接 `GLib::GLib` + `libxpm::libxpm`，运行期注入 `G_TEST_SRCDIR`/`G_TEST_BUILDDIR` 实跑；`rgb` 测试因需 configure 生成的内部头（`xpm.h`/`unixio.h`/`file.h`，release tarball 不含）判 N/A。另保留两个 display-independent 的 consumer 测试覆盖核心 ABI 面与解析/写出管线：

`libxpm_api_surface` 对 libXpm.so.4 全部 34 个导出函数（Xpm*）强制活重定位，确保 ABI 完整；`libxpm_version_contract` 校验 XpmIncludeVersion=30411、XpmImage（4 个 unsigned int + 末尾 colorTable/data 指针，offsetof 断言）、XpmColor（6 个 char*）、XpmInfo/XpmExtension/XpmColorSymbol 布局，18 个导出函数的强类型签名契约，以及一个完整 XPM round-trip：内联 XPM 数组解析为 XpmImage → 写入文件 → 读回 → 重新生成 XPM 数据，验证解析/写出管线（display-independent，功能上覆盖上游 `XpmCreate` / `XpmWrite` / `XpmRead` 测试的核心解析/写出场景）。

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：**4/5（4/4 可执行子集实跑全部通过；`rgb` 判 N/A）**。本 PR `test_package` 将上游 4 个 display-independent 测试（`XpmCreate`/`XpmMisc`/`XpmRead`/`XpmWrite`）源码未修改 vendored，链接已发布 **glib/2.88.0**（PR #6619 鸿蒙化）在 OHOS CI 上构建并实跑通过（运行期注入 `G_TEST_SRCDIR`/`G_TEST_BUILDDIR` 定位 `pixmaps/` 数据，`config.h` 提供 configure 生成等价宏：`HAVE_G_PATTERN_SPEC_MATCH_STRING`/`NO_ZPIPE`）。`NO_ZPIPE` 按上游 harness 自身的 `#ifdef` 干净跳过压缩 xpm 变体（.xpm.gz/.xpm.Z，需 gzip/compress 工具链 + 构建期生成步骤，非库构建产物）。**`rgb` N/A**：上游 `rgb.c` 测内部函数 `xpmReadRgbNames`（`#include "../src/rgb.c"`，非导出 API），且依赖 configure 生成的内部头 `xpm.h`/`unixio.h`/`file.h`——libXpm-3.5.17 release tarball 不含这三个头（已解包核验），无法无修改编译。测试源码未作任何修改（「上游测试用例修改说明」仍为否），与 `#ifdef` 相关的跳过行为是上游自身的测试逻辑
- 新增测试用例通过率：2/2（100%），`test_package` 由 GitCode CI 在 PR 上构建并执行通过（`libxpm_api_surface` + `libxpm_version_contract` 两个 consumer 均通过；round-trip 在 OHOS CI 上实测触发 `XpmCreateDataFromXpmImage` 单块内存契约，见「知识库扩展」第 6 点）

## 补充说明

- 本 PR 只新增 `archives/l/libxpm/3.5.17/` 下的 Conan 配方、元数据、test_package，不修改依赖包或基础设施目录。
- 包名沿用小写 `libxpm/3.5.17`；目录使用小写 `archives/l/libxpm/3.5.17/`，符合 conan slug 规则。
- 上游测试用例统计已通过解包 libXpm-3.5.17 release tarball 手工核验（`test/Makefile.am` `check_PROGRAMS = XpmCreate XpmMisc XpmRead XpmWrite rgb`，`TESTS=$(check_PROGRAMS)`，条件 `ENABLE_UNIT_TESTS`+`HAVE_GLIB`），N=5 不存在少报。
- 本 PR 上游测试实跑依赖 glib/2.88.0（PR #6619 鸿蒙化已发布）。首次提交时 GLib 尚未发布，曾按"依赖测试框架未鸿蒙化"申请路径 B、以 `version_contract` round-trip 等价覆盖——GLib 发布后（#6619 合并）已按评审意见改为直接链接 glib/2.88.0 实跑上游 4 个可执行测试（`XpmCreate`/`XpmMisc`/`XpmRead`/`XpmWrite` 全部通过），`rgb` 因 configure 生成内部头缺失判 N/A（详见「验证结果」段）。功能等价覆盖的 consumer 测试（`api_surface`/`version_contract`）继续保留。

## 知识库扩展

复用 E342 已验证的 X11 家族 autotools 适配模式。本 PR 补充七个新知识点：

1. **cxpm 工具无 LDADD 也能链接**：cxpm.c 直接 `#include` 内部 src/*.c
   翻译单元（data.c/parse.c/RdFToI.c/hashtab.c/misc.c/Attrib.c/Image.c），
   这些文件不调用 Xlib 函数，故 cxpm 只需链接 libc，不会因缺 `-lX11`
   而失败；sxpm 由 `PKG_CHECK_MODULES(SXPM, ... xt ...)` 无 libXt 自动禁用。
2. **libXpm 的依赖轨道陷阱**：与 libxcursor 同源——必须强制 libx11/**6.4.0**
   （cmd-pkgs 轨道），强制 1.8.13 会让 libX11.la 引用不存在的 libxcb.la
   导致 libtool `is not a valid libtool archive` 失败。
3. **Xpm 头文件声明机制**：`xpm.h` 用 `FUNC(name,type,args)` 宏展开为
   `extern _X_EXPORT t f args`，与普通 `extern` 声明等价；导出面为 34 个
   Xpm* 符号，`-version-number 4:11:0` → libXpm.so.4。
4. **OHOS autoconf works-check 陷阱（关键，来自 libxrender/0.9.12 实证）**：
   OHOS worker 上 `--build == --host` 的本机模式会失败——autoconf 的 C 编译器
   works-check 尝试 *执行* conftest 二进制，被 OHOS 沙箱拦截报
   `C compiler cannot create executables`。必须 `--host=aarch64-linux-ohos`
   进入交叉编译模式（config.guess 报 build=aarch64-unknown-linux-ohos ≠ host），
   works-check 仅链接不运行即通过。配合 build 本地重定位 linker-view 消除
   libx11/6.4.0 的 libX11.la → libxcb.la（libxcb/1.16 无 .la）的 libtool 崩溃。
5. **config.guess/config.sub 补丁（必须，来自 libxrender/0.9.12 移植）**：上游
   config.guess 不认识 HarmonyOS，fall through 到通用 Linux 分支去编译 dummy.c
   探测（需在 TMPDIR 写文件），在 OHOS worker 沙箱下报
   `config.guess[1700]: can't create .../dummy.c: Permission denied` →
   `cannot guess build type`。libxrender 通过两个 conandata 补丁解决：
   `0002-config.guess.patch` 在 NetBSD 分支前插入 HarmonyOS 分支（uname -s 为
   HarmonyOS 时直接 echo aarch64-unknown-linux-ohos 退出，不再编译 dummy.c）；
   `0001-config.sub.patch` 把 `ohos*` 加进合法 OS 列表、`linux-ohos*` 加进
   kernel-os 校验。本配方按 libxpm 的 config.guess/sub 版本做了 hunk 适配。
6. **XpmCreateDataFromXpmImage 的单块内存契约**：该函数返回**一个** XpmMalloc
   分配的连续块，行指针全部指向块内部（man XpmCreateData："a single block
   malloc'ed data"），调用方只需 `XpmFree(data_return)` 一次。若逐行
   `XpmFree` 会二次释放内部指针，在 Bionic/scudo 分配器下直接 SIGTRAP
   （Signal 5）崩溃——本 PR 的 round-trip 测试在 OHOS CI 上实测触发，属文档化
   API 契约而非 libXpm 缺陷。
7. **上游测试框架鸿蒙化后直接实跑（rule4 修正闭环）**：libxpm 上游 `test/` 的
   5 个 `check_PROGRAMS` 受 `if ENABLE_UNIT_TESTS if HAVE_GLIB` 双条件控制，深度依赖
   GLib 测试框架（`g_test_init`/`g_assert`/`g_test_run`）+ GLib 目录遍历 API
   （`GDir`/`g_pattern_spec`/`g_test_get_filename`，封装于 `TestAllFiles.h`）+
   `pixmaps/` 数据集。首次提交时 GLib 未鸿蒙化，曾走路径 B 等价覆盖；glib/2.88.0
   发布（PR #6619）后，本 PR 改为直接链接 `GLib::GLib` 实跑上游测试：4 个可执行
   测试源码未修改 vendored，最小 `config.h` 等价 configure 宏（
   `HAVE_G_PATTERN_SPEC_MATCH_STRING`/`NO_ZPIPE`），运行期注入 `G_TEST_SRCDIR`
   /`G_TEST_BUILDDIR` 定位 `pixmaps/` 数据，全部通过。`rgb` 因依赖 configure 生成
   的内部头（`xpm.h`/`unixio.h`/`file.h`，release tarball 不含）判 N/A。两个
   consumer 测试（`api_surface`/`version_contract`）继续保留作 ABI 面与 round-trip
   契约覆盖。

本 PR 是 GUI 工具链消费 libXpm（XPM 图标/图像解析）的构建前置。
