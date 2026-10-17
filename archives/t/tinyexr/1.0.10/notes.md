# tinyexr 1.0.10

- 上游：https://github.com/syoyo/tinyexr tag v1.0.10（codeload 与 github archive 同 sha256 `d2e4cef7…e6cc`）
- 单头 `tinyexr.h` + `tinyexr.cc`（`TINYEXR_IMPLEMENTATION`）+ 自带 miniz
- 构建：clang 编 `tinyexr.cc` 与 `deps/miniz/miniz.c` 打成 `libtinyexr.a`；不用上游 CMake（cmake_minimum_required 2.8 且无安装规则）
- 上游测试（真机 `conan create` 退出码 0）：
  - Catch2 V1 `test/unit/tester.cc`：**37/37 test cases 通过，2759 assertions**（含 openexr-images 样本与 `test/unit/regression/` fuzz 用例）
  - `test/unit/tester.cc` 共 `grep -cE '^[[:space:]]*TEST_CASE'` = **38** 个 TEST_CASE 宏，其中 1 个（`Tiles/Spirals.exr`，pxr24 压缩）位于 `#if 0`（tester.cc:1011）不参与注册，故实跑 37；声明取宏数 38 ≥ 实跑 37
  - 根目录 `make test`：`./test_tinyexr asakusa.exr` 载入往返通过（1 项集成）
- 构建期下载 openexr-images（`AcademySoftwareFoundation/openexr-images` main），并把 `test/unit/tester.cc` 的 `kOpenEXRImagePath` 由 `../../../openexr-images/` 改为 `../../openexr-images/`（仅路径、非断言）
- 与 1.0.13 差异：1.0.10 无 `tester-v2/v3/v3-simd.cc`、无 `run_tests.txt`，根 Makefile 无 `test-v3`；仅 Catch2 V1 单测 + 根 `make test`
- `test/unit/Makefile` 默认 ASan/UBSan，OHOS 用命令行 `CFLAGS/CXXFLAGS` 覆盖为 `-O2 -std=c++11`
- 1.0.10 tarball 无顶层 `LICENSE`（仅 `deps/miniz/LICENSE`），`package()` 的 `copy("LICENSE")` 为空操作，不影响出包
- 鸿蒙特有：`test_package/test_tinyexr.cpp` **10/10**（`__OHOS__`、SaveEXR/LoadEXR 往返、IsEXR、ParseEXRVersionFromFile）；口径：真机执行输出 10 行 `ok - `，源码 `check(` 调用点 12（`grep -cE '^[[:space:]]+check\('`）中 2 处为 `#else`/`else` 互斥兜底，与已合入 1.0.13 同文件同声明
