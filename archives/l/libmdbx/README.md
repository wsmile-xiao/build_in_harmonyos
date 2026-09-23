# libmdbx

libmdbx 是一个嵌入式事务型键值数据库引擎，提供 C API 和现代 C++ API。

## HarmonyOS PC 适配

- 使用上游 CMake 构建共享库，并保留头文件和 CMake 消费者目标。
- 库包关闭命令行工具、man page 和上游测试构建，只交付库本身。
- Conan 包名为 `libmdbx`，消费者目标为 `libmdbx::mdbx`。

## 验证

`0.14.3` 的发布归档不包含完整上游测试目录；test_package 提供 C API、C++ API 和仅 OHOS 构建的 HMDFS 专项消费者验证。最终设备验证中 C consumer 为 `21 passed, 0 failed`，C++ consumer 为 `8 passed, 0 failed`，OHOS consumer 为 `5 passed, 0 failed`；W3 本地 CI 模拟通过。当前状态为 `built`，不代表已发布。

## 上游

- <https://github.com/erthink/libmdbx>
