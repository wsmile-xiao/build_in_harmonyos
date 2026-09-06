# pnm 1.0.1 测试报告

## 上游测试

- 来源：上游 `test/test_pixels.cpp`、`test/test_image.cpp`、`test/test_io.cpp`
- 规模：10 个 Catch2 `TEST_CASE`，1263 个断言；3 个测试程序
- 命令：`cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && cmake --build build -j2 && ctest --test-dir build/test --output-on-failure`
- 结果：3/3 测试程序通过，10/10 test cases 通过，1263/1263 assertions 通过
- 备注：上游 CMakeLists 声明 `cmake_minimum_required(VERSION 3.0)`，CMake 4.1 首次配置被移除兼容策略拦截；增加官方支持的 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 后通过。未修改上游测试。

## 消费者测试

- 文件：`test_package/test.cpp`
- 规模：1 个集成测试，4 个显式运行时检查（通过返回非零报告失败，避免 Release `NDEBUG` 消除断言）
- 命令：`conan create archives/p/pnm/1.0.1 --name=pnm --version=1.0.1 -pr:h=default -pr:b=default -s:h compiler.libcxx=libc++ -s:b compiler.libcxx=libc++ --build=missing`
- 结果：1/1 通过
- 覆盖：`pnm::image<rgb_pixel>`、二进制 PPM 写入、读取及 RGB 像素值回读。

## 环境限制

设备默认 profile 使用 `compiler.libcxx=libstdc++`，clang 15 报 `invalid library name in argument '-stdlib=libstdc++'`；设备工具链实际可用 libc++，验证时显式覆盖为 libc++。该问题属于环境 profile 与工具链不一致。
