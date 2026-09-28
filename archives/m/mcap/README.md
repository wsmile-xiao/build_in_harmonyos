# mcap

Header-only C++ implementation of the [MCAP](https://github.com/foxglove/mcap) file format
(modular, serialization-agnostic log container for pub/sub and robotics).

- 最新版本：`0.3.0`（C++ 包 tag `releases/cpp/v0.3.0`）
- 构建系统：header-only（C++17，需 lz4 + zstd 压缩依赖）
- 上游测试：`cpp/test/unit_tests.cpp`（Catch2，8 TEST_CASEs，随 `make test-host` 运行）
