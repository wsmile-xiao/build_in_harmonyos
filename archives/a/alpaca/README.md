# alpaca

C++17 header-only serialization library.

## OHOS 适配

- CMake 安装 `alpaca` 头文件、Config.cmake 和 pkg-config 元数据。
- Conan target 为 `alpaca::alpaca`。
- 构建时关闭 samples、benchmarks 和 Python 绑定；设备可运行时执行上游 doctest。
- 本次为路径 A 基础适配，未修改上游源码，也没有新增知识库扩展。

## 验证

- 上游测试：343/343 通过；按 doctest 运行时实际 test cases 计数。
- Conan 消费测试：1/1 通过，实际验证 `serialize`/`deserialize` 往返。

上游：https://github.com/p-ranav/alpaca
