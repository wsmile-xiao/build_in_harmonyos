# kylin-ai-proto

Kylin AI 协议定义包（openKylin AI 子系统进程间通信协议），纯数据分发：
gdbus（D-Bus introspection XML，`share/kylin-ai/protocols/gdbus/`）与 grpc
（`.proto` 文件，`share/kylin-ai/protocols/grpc/`）。上游为 CMake INTERFACE
库（`add_library(KylinAiProto INTERFACE)`），无编译代码。

## 已适配版本

| 版本 | 上游 | 状态 |
|------|------|------|
| 1.0.0.1 | gitee.com/openkylin/kylin-ai-proto (tag build/1.0.0.1-ok0.3, commit 9074982) | built |

## 要点

- 纯协议/数据包，无外部依赖（CMakeLists.txt 无 find_package）
- CMake target：`KylinAiProto::KylinAiProto`（cmake_file_name=KylinAiProto）
- 产物：`share/kylin-ai/protocols/`（10 gdbus XML + 9 grpc proto）
  + `lib/cmake/KylinAiProto/`（CMake package config）
- 补丁 1 个：`install(DIRECTORY protocols/usr/ DESTINATION /usr)` 直写系统根 →
  改为 `${CMAKE_INSTALL_DATAROOTDIR}`；CMake 配置目录由 share/ 迁到 lib/cmake/
- 上游无测试（R51 清点证据见 1.0.0.1/notes.md），test_package 消费者测试
  验证 find_package 目标 + 协议文件存在且非空
