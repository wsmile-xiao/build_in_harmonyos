# kylin-ai-document-service

Kylin AI 文档分块服务（openKylin AI 子系统）的 **gRPC 客户端库**。上游用 CMake
构建共享库 `libkylin-ai-document-service.so`（C++17），对外提供
`document::DocumentChunkClient`：同步/异步/流式文档分块请求，并在首次调用前经
sd-bus（systemd 用户总线）拉起 `kylin-ai-document-service.service`。除 C++ 库外
还分发 Python 服务负载与 systemd user unit。

上游协议定义在源码树 `document.proto`（`package document`，
`service DocumentService`）。

## 已适配版本

| 版本 | 上游 | 状态 |
|------|------|------|
| 1.2.0.0 | gitee.com/openkylin/kylin-ai-document-service（tag build/1.2.0.0-ok0.6，commit ef12f7fa） | built |

## 要点

- 产物：`lib/libkylin-ai-document-service.so.2.0.0`（SONAME `.so.2`）
  + `include/kylin-ai-document-service/*.h`
  + `share/pkgconfig/kylin-ai-document-service.pc`（`${pcfiledir}` 可重定位）
  + `share/kylin-ai-document-service/python/`（服务负载）
  + `lib/systemd/user/kylin-ai-document-service.service`
- 纯库类型，**无 `bin/` 可执行产物 → 不提供 `commands.json`**（R38）
- 依赖：`grpc/1.84.0`、`protobuf/33.6`、`libkylin-ai-system-private/1.2.0.0`、
  `systemd/261`、`nlohmann_json/3.12.0`（zlib/openssl/abseil 等为传递依赖）
- `find_package(KylinAiProto)` 由 `libkylin-ai-system-private/1.2.0.0` 的组件提供
  （该包 `share/KylinAiProto/cmake/` 含 `KylinAiProtoFunctions.cmake` /
  `KylinAiProtoGenerate.cmake`，即本库代码生成所调用的两个函数）
- 补丁 3 个：CMake 安装路径与依赖发现（`find_package` 替代 pkg-config）、
  pkg-config 可重定位、protobuf 33.x JSON API 改名
- 上游测试：仅 `test/test.cpp`（N=1，无 CTest 注册），已在 `build()` 中编译并
  执行（N′=1）；其局限见 `1.2.0.0/notes.md` 的 R51 申报表
- 平台限制：OHOS 无 systemd 守护进程与用户 D-Bus，运行期 `startUserService()`
  必然失败（编译/链接不受影响，已计入兼容性说明）
