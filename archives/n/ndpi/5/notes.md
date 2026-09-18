# ndpi 5 适配笔记

## 编译环境

- 构建系统：autotools（`configure.ac` + `autogen.sh`，无预生成 `configure`）
- 上游：https://github.com/ntop/nDPI，tag `5.0`（`configure.ac: AC_INIT([libndpi],[5.0.0])`）
- 配方版本：归档目录保持任务卡 `5`（L0n 分支门禁 `feat/ndpi-5`）；制品版本经
  `set_version()` 归一化为上游 tag `5.0`（E563；Conan `validate_ref` 正则要求版本
  总长 >= 2，字面 `version = "5"` 在 `conan create` 导出阶段必报
  `ERROR: Invalid package version '5'`，2026-09-16 真机实证）
- 编译器：clang/clang++（OHOS aarch64，`ci/conan/profiles/ohos-aarch64`）
- 状态：built（工作树未提交，真机预检待 HMBS 后台执行）

## 编译步骤

1. `get()` 下载 `https://github.com/ntop/nDPI/archive/refs/tags/5.0.tar.gz`
   （sha256 `8b0d3d…aa9ea5`，与 Homebrew、Fossies、Void 三方公布值一致），`strip_root=True`。
2. `generate()`：`AutotoolsToolchain`（shared=True 时 `--disable-static --enable-shared`，
   反之 `--enable-static --disable-shared`，恒加 `-fPIC`）+ `AutotoolsDeps` + `PkgConfigDeps`
  （向 `configure` 注入 `libpcap/1.10.6` 的 CFLAGS/LDFLAGS）。
3. `build()`：
   - 置 `PWD=$build_folder`，补 `ACLOCAL_PATH` 的 `pkg.m4`；
   - `autoreconf -fiv` 生成 `configure`（`tool_requires: automake/1.18, libtool/2.5.4`）；
   - config.guess/config.sub 补充 HarmonyOS 识别；`configure` 的 mktemp 改走
     `${TMPDIR:-/tmp}`、pwd 判定回退 `$PWD`（HMDFS 已验证模式，与 aircrack 1.7 相同）；
   - `configure` → `make -j1` → `_run_upstream_checks()` 执行 `make check` 并输出
     `HMBS_UPSTREAM_TEST_RESULT` 标记。
4. `package()`：install-shim 下 `make install`，删除 `*.la`，移除 `bin/`（ndpiReader、
   ndpiSimpleIntegration）与 `share/ndpi`（示例数据），仅发布库 + 头文件 + `libndpi.pc`。
5. `test_package`：CMake 构建 `test.c` 并 `ctest -R test_ndpi`，输出
   `HMBS_TEST_PACKAGE_RESULT`（7 断言）。

## 上游测试审计（适配前清点）

| 套件 | 来源 | 规模 | 真机计划 |
|------|------|------|----------|
| pcap 回放 | `tests/do.sh` + `tests/cfgs/*/pcap|result`，`tests/Makefile.am: TESTS = do.sh do-dga.sh` | cfgs 多配置 × 大量 pcap（全量数以 `make check` 日志为准，不预估） | `make check` 运行 |
| DGA 门禁 | `tests/do-dga.sh` + `tests/dga/test_{,non_}dga.csv`（准确率/精确率/召回率阈值） | 1 脚本（3 指标门禁） | `make check` 运行 |
| C 单测 | `tests/unit/unit.c`（`BUILD_UNITTESTS` 需 json-c，`configure.ac` 无 json-c 时自动禁用） | 1 二进制（多断言） | 缺 json-c（制品仓无 published 版本）而自动跳过，已在 MANIFEST 声明 |

审计结论：上游存在测试，配方在 `build()` 末尾完整运行 `make check`（do.sh + do-dga.sh 实跑；
unit 因缺 published 的 json-c 由上游 `configure` 自行禁用，不属配方跳过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | archive tarball 无 `configure`，直接 `Autotools.configure()` 无入口 | 上游要求 `./autogen.sh && ./configure`（5.0 发布说明 behavior） | `build()` 先 `autoreconf -fiv`，`tool_requires` 锁定 `automake/1.18` + `libtool/2.5.4`（与 aircrack 1.7 同口径） |
| 2 | `example/ndpiReader` 链接需 libpcap；`tests/do.sh` 无 reader 则 `exit 1` | 完整构建默认含 example，`AC_CHECK_LIB([pcap])` 缺失即报错 | `requires("libpcap/1.10.6")`（已 published）+ `AutotoolsDeps/PkgConfigDeps` 注入 |
| 3 | unit 测试需 json-c，但制品仓 json-c（0.17/0.18）无 published 版本 | R36 禁止依赖未发布包 | 不声明 json-c；`configure` 自动走 `Disabled unit test` 分支，仅 do.sh/do-dga.sh 实跑，并在 MANIFEST 与 PR 补充说明中如实声明 |
| 5 | 真机 `make check` 2 进 1 出错 + `[readonly_tmp]`（`tests/do.sh.in` 硬编码 `/tmp/reader.$$.out`，真机 `/tmp` 只读，`ndpiReader -w` 写不出，`do.sh` 直接 ERROR/FAIL） | 上游 `run_single_pcap()` 写 `/tmp/reader.$$.out` 共 5 处（`CMD/test -f/diff/cp/rm`），与 `configure` 的 mktemp 问题同源 | 新增 `_patch_one_tmpdir/_patch_tests_tmpdir`：`tests/do.sh.in/do.sh/do-dga.sh/do-unit.sh` 的 `/tmp/reader.` 全部替换为 `${TMPDIR:-/tmp}/reader.`（仅换临时根目录，不删测试）；`autoreconf` 后打模板、`configure` 后再打生成树（兼顾 out-of-source `build-release`），`make` 前 `makedirs(TMPDIR)`；失败时递归转储全部 `test-suite.log` + `make-check.log` 的 ERROR/FAIL/OK 行 |
| 6 | test_package 报 `fatal error: .ndpi_define.h. file not found`（`include/ndpi/ndpi_main.h:32` 经 `"ndpi_define.h"` 同目录引用，但包内缺失；上游 `src/lib/Makefile.in` 的 install 只 `find \$(top_srcdir)/src/include/*.h`，而 `ndpi_define.h` 由 `AC_CONFIG_FILES` 在 top_builddir 生成，源树仅有 `.in` 模板） | 上游 out-of-tree 安装遗漏生成头（非工具链/环境问题） | `package()` 末新增 `_install_generated_headers()`：在 build 树（`src/include/ndpi_define.h` 优先，兼 walk 兜底）定位生成头并拷贝到 `package/include/ndpi/ndpi_define.h`，缺失则直接报错；`ndpi_config.h` 保持构建私有（仅 `NDPI_LIB_COMPILATION` 下被引用，不随包发布） |
| 4 | `make install` 附带 `bin/ndpiReader` + `share/ndpi`，包变为库/工具混合体 | `example/Makefile` 的 install 规则 | `package()` 移除 `bin/` 与 `share/`，保持纯 `library`（无需 commands.json）；ndpiReader 仍在构建树中供 `make check` 使用 |

## 依赖版本

- `libpcap/1.10.6`（requires，已 published）
- `automake/1.18`、`libtool/2.5.4`（tool_requires，autoreconf 用）
- 无其他 requires；pcre2/maxminddb/rrd/nBPF 保持上游默认关闭

## 验证结果

- 本轮为工作树准备轮（按任务要求不 commit、不 push、不建 PR）：`conan create` 未在本机执行，
  待 HMBS 后台在 HarmonyOS 真机完成 `conan create`（含 `make check` + `test_package`）。
- `HMBS_UPSTREAM_TEST_RESULT`（automake 框架，`make check`）与 `HMBS_TEST_PACKAGE_RESULT`
  （`discovered=7/passedCount=7`，`ctest -R test_ndpi`）均由配方在真机实测后输出；
  PR 正文通过率以预检日志实测为准，本轮不填写猜测数字。
- 证伪预案（真机轮执行）：① 确认 `make-check.log` 含 automake `PASS: do.sh/do-dga.sh` 且
  `result/*.out` 非空（非空文件比空文件）；② 必要时以 `exit 1` 桩替换 ndpiReader 确认 harness 可抓失败；
  ③ 区分"通过"与"静默跳过"（SKIPPED 计跳过，不计通过）。

## 注意事项

- 源码 URL 仅保留官方 GitHub（R39）；GitHub/GNU 镜像回退由 CI 自动追加，不手写镜像。
- `v12` 系列配方要求 `settings.os in ("Linux", "OHOS")`；本配方无 OS 分支，无需该判断。
- 本机 Windows 大小写不敏感导致 `archives/l/libXext` 与 `archives/l/libxext` 共存目录
  在 `git status` 中显示为已修改（历史遗留，与本任务无关，未触碰）。
