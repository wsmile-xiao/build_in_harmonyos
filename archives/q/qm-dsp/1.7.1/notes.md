# qm-dsp 1.7.1 — 适配笔记

## 来源核验（官方资料确认）

- 官方仓库：https://github.com/c4dm/qm-dsp
- 正式标签：`v1.7.1`（GitHub Tags API 可查，commit 2117b645d8fac30ae0dd75af02d3e2c57bb905c0）
- 许可证：GPL-2.0（COPYING，发布包根目录）
- 源码归档：`https://github.com/c4dm/qm-dsp/archive/refs/tags/v1.7.1.tar.gz`
- SHA-256：`4d6884ef9e45f571b2621a2d9e87c6bb5074a24ba4b82f78699f43eb0786d0df`
  （本机下载官方归档实测，归档 1504762 字节；conandata.yml 沿用该值）
- 官方文档：README 明确 Linux 构建为 `make -f build/linux/Makefile.linux64`，
  测试为同 Makefile 加 `test` 目标，依赖 Boost。

## 结构

- 纯 Makefile 项目，无 configure、无 CMakeLists、无 meson。顶层构建入口
  `build/linux/Makefile.linux64` 仅设 CFLAGS/CXXFLAGS 后 include
  `build/general/Makefile.inc`，后者枚举全部 SOURCES/HEADERS 并归档为
  `libqm-dsp.a`。自带 kissfft/clapack/cblas 源码，无第三方运行时依赖。
- 头文件分布在 `base/`、`dsp/*/`、`hmm/`、`maths/`、`thread/`、`ext/kissfft/`，
  源码以 `#include "dsp/transforms/FFT.h"` 相对根目录引用，故打包时必须保留
  子目录结构（`include/dsp/...`），消费者以 `-I<package>/include` 使用。
- `build/linux/amd64/cblas.h`、`clapack.h` 为编译期 include（`-Ibuild/linux/amd64`），
  不对外安装。
- 无 `commands.json`：产物仅静态库，无可执行文件，属纯库类型。

## 上游测试审计（R51 三步法之清点）

- 测试目录：`tests/`，框架为 Boost.Test（每个文件 `BOOST_TEST_DYN_LINK` +
  `BOOST_TEST_MAIN` + `BOOST_AUTO_TEST_SUITE`）。
- 构建规则：`tests/Makefile` 定义 `TESTS := test-mathutilities test-window
  test-fft test-pvoc test-resampler test-medianfilter`，链接
  `-lboost_unit_test_framework -lpthread`，默认用 `valgrind -q` 执行。
- 逐文件清点 `BOOST_AUTO_TEST_CASE`（v1.7.1 原文计数）：
  - TestFFT.cpp 21（forward/inverse 边界、dc、sine、cosine、sineCosine、nyquist、dirac、sizes 等复/实数组合）
  - TestMathUtilities.cpp 11（round、mean、sum、median、princarg、isPowerOfTwo、next/previous/nearestPowerOfTwo、factorial、gcd）
  - TestWindow.cpp 9（periodic、bartlett、hamming、hann、blackman、blackmanHarris、kaiser_4_10、kaiser_2p5_11、sinc）
  - TestMedianFilter.cpp 10（odd、even、odd75、even75、oddStandalone、evenStandalone、standaloneEmpty、types、inf、nan）
  - TestResampler.cpp 11（sameRateOneShot、sameRate、interpolatedMisc、interpolatedSine、decimatedSine、downUp2/5/16、upDown2/5/16；末尾 spectrum 已整块注释，不计）
  - TestPhaseVocoder.cpp 2（fullcycle、overlapping）
  - 合计 64（conanfile.py 中 `UPSTREAM_CASE_TOTAL = 64` 硬门禁，单二进制期望值见 `UPSTREAM_CASES_PER_BINARY`）。
- 运行方式：配方 `build()` 先编出 `libqm-dsp.a`，再以 Conan boost 的头文件/库目录
  显式编出 6 个二进制（`VG=""` 跳过 valgrind，OHOS 真机无该工具），逐个以
  `--log_level=test_suite --report_level=detailed` 执行，解析框架输出的
  `Running N test cases...` 与 `No errors detected`，N 与审计期望不符即报漂移。
- 证伪设计：逐项检查退出码 + 成功文本 + 用例数三元组；桩二进制（空输出/错误输出/
  非零退出）必 FAIL；`UPSTREAM_CASE_TOTAL` 防 harness 被改小后全过。（待真机用实际日志复核。）

## 依赖

- `boost/1.90.0.4.1`（仅用于 build 期编跑上游 Boost.Test；库本身不依赖 Boost）。
  选用该版本因其明确编译 `test` 组件（含 `unit_test_framework`），而 1.84.0
  配方仅编 filesystem/regex/program_options/iostreams、无 test 组件。
  `package_info()` 不向消费者透传 Boost，消费者仅链接 `qm-dsp` + 系统 `m`/`pthread`。
- 无其他依赖。kissfft/clapack/cblas 均已 vendor 在源码树内。

## 构建适配（第二轮修订：静态补丁改为构建时直写）

- 真机失败：`apply_conandata_patches` 报 `Failed to apply patch`
  `patches/0001-build-linux-aarch64-flags.patch`，`source file is different -
  build/linux/Makefile.linux64`。上游该文件仅 5 行，hunk 上下文漂移/CRLF
  脆弱导致打补丁失败；与 `/tmp` 只读诊断无关（配方与测试均未写 `/tmp`）。
- 修复：删除静态补丁文件及 `conandata.yml` 的 `patches` 声明，`conanfile.py`
  新增 `_fix_linux_makefile_aarch64()` 在 `build()` 首行幂等执行，
  上下文无关字符串删除 `-msse2`/`-msse`/`-mfpmath=sse` 并压缩多余空格，
  无旧标记时跳过。其余 `-O3 -fPIC -ffast-math -ftree-vectorize
  -DUSE_PTHREADS` 保留，无平台宏。
- R33：CC/CXX/AR/RANLIB 经 `_resolve_tool` 解析：配置绝对路径仅在文件存在且
  可执行时信任，否则告警并回退到 PATH 中的可用编译器；CXX 追加 `-stdlib=libc++`
  以匹配 OHOS profile。test_package 的 CMake 侧同样仅在配置路径不可用时覆盖
  `CMAKE_C/CXX_COMPILER`。
- 测试编译追加 `-std=c++17`（Boost 头文件要求），库本身沿用上游默认标准。
- 上游测试 6 二进制 rc=127 `Error relocating ... symbol not found`（Boost.Test
  符号）：链接期 `-L` 命中 Conan boost 1.90 共享库，但运行时无 rpath 且
  `subprocess.run` 绕过 conanrun 环境，loader 解析到错误副本。修复：
  链接加 `-Wl,-rpath,<boost libdir>`（不套内层双引号，避免破坏
  `make LDFLAGS="..."` 的 shell 解析）、编译加 `-DBOOST_TEST_DYN_LINK`、
  运行二进制时 `LD_LIBRARY_PATH` 前置 boost libdir（`_test_run_env`）。
- 判定修正：`--report_level=detailed` 下 Boost.Test 只打印逐用例
  `N assertions out of M passed`、从不打印短报告尾标
  `No errors detected`，旧 `ok_text` 检查恒为假导致 0/64。
  改为单一方判定：exit==0 且 `Running N`==审计期望且至少一行断言行、
  且全部断言行满通过（空输出/桩必然失败，无算术回补）。
- 并行约束：全程 `-j1`。

## 本轮状态

- 首轮工作树：配方 + portability 补丁 + test_package（含 4 断言消费者测试
  `test_qmdsp.cpp`）+ 双 manifest + PR 正文草稿已就绪，均未提交。
- 待 HMBS 真机预检：`conan create` 全量日志（含 64 上游检查明细、
  `HMBS_UPSTREAM_TEST_RESULT` 与 `HMBS_TEST_PACKAGE_RESULT` 两行标记）
  回来后，如实回填 PR 正文通过率；若 boost 二进制缺失或测试在真机水土不服
  （编译器键名、库路径形态、 Boost 输出格式等），按预检日志修复。
