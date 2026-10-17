# nbytes

nbytes 0.1.4 是从 Node.js 核心拆出的字节处理函数库（C++20，CMake 构建）。
本适配以官方 `v0.1.4` 源码归档构建静态/共享库，安装 `libnbytes` 与 `nbytes.h`，
并提供 `nbytes::nbytes` CMake consumer target。

## HarmonyOS 适配

- 上游仓库：https://github.com/nodejs/nbytes
- 版本：0.1.4
- 许可证：MIT
- Conan 引用：`nbytes/0.1.4`
- 适配路径：路径 A（基础适配）

上游测试为 `tests/basic.cpp` 中的 3 个 gtest 用例（`swap_bytes16/32/64`），
配方在构建阶段以 `NBYTES_ENABLE_TESTING=ON` 启用并通过 ctest 实际执行；
消费者测试见 [0.1.4/test_package/test.cpp](0.1.4/test_package/test.cpp)（8 项真实 API 检查）。

详细测试统计见 [0.1.4/notes.md](0.1.4/notes.md) 和
[0.1.4/test_package/MANIFEST.yml](0.1.4/test_package/MANIFEST.yml)。
