# tinyexr 1.0.13

- 上游：https://github.com/syoyo/tinyexr tag v1.0.13
- 单头 `tinyexr.h` + `tinyexr.cc`（`TINYEXR_IMPLEMENTATION`）+ 自带 miniz
- 构建：clang 编 `tinyexr.cc` 与 `deps/miniz/miniz.c` 打成 `libtinyexr.a`；不用上游 CMake 2.8
- 上游测试（真机 `conan create` 退出码 0）：
  - Catch2 V1 `tester.cc` 56/56（19050 assertions），含 openexr-images 样本
  - Catch2 V2 `tester-v2.cc` 48/48（3151085 assertions）
  - 根目录 `make test`：`./test_tinyexr asakusa.exr` 通过
  - 合计 105 个可执行用例；`tester.cc` 另有 1 条已注释 Issue54，审查脚本计为 106
- 构建期下载 openexr-images，并把 `kOpenEXRImagePath` 改为 `../../openexr-images/`
- `test/unit/Makefile` 默认 ASan/UBSan，OHOS 用命令行覆盖为 `-O2 -std=c++11`
- 鸿蒙特有：`test_package/test_tinyexr.cpp` 10/10
