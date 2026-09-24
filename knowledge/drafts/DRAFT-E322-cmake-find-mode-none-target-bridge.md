# DRAFT-E322-cmake-find-mode-none-target-bridge：DRAFT-E322-cmake-find-mode-none-target-bridge

> Status: **Draft**（待审核 promote）| severity: `2` | category: `build-system|conan` | Updated: ?
> 对应: `knowledge/drafts/DRAFT-E322-cmake-find-mode-none-target-bridge.kv`

---

## 触发面

- trigger_tool: `cmake|conan`
- phase: `test_package`

**匹配关键词**：cmake_find_mode,find_dependency,grpc_dir,target not found,interface imported

## 错误签名（error_signature）

```text
Could not find a package configuration file provided by "grpc"|Target.*links to.*grpc::grpc.*but the target was not found|find_dependency\(grpc\)
```

## 根因（root_cause）

grpc/protobuf 配方设 cmake_find_mode=none，CMakeDeps 不为其生成 config；消费方包的 CMakeDeps 生成物（-config.cmake/-Target-release.cmake）引用默认目标名 grpc::grpc / protobuf::protobuf，而注册表包自带 config 实际定义 gRPC::*（gRPCTargets.cmake）与 protobuf::libprotobuf；且 find_dependency(grpc) 用小写名搜索 grpc_DIR/grpcConfig.cmake， 实际文件是大写 gRPCConfig.cmake，OHOS 文件系统大小写敏感导致双重失配

## 影响范围（affected_scope）

所有依赖 grpc/protobuf（cmake_find_mode=none 包）的消费方 test_package， 尤其是静态链接需要完整传递依赖闭包的场景

## 推荐方案（rec_approach: `test_package 的 conanfile 用 tc.variables 显式指路（gRPC_DIR/Protobuf_DIR/utf8_range_DIR/absl_DIR/OPENSSL_ROOT_DIR 指向制品仓包的 lib/cmake/<name>），CMakeLists 先 find 真实 config，再用 INTERFACE IMPORTED 桥接 CMakeDeps 期望的目标名，并预置 <dep>_FOUND=TRUE 跳过生成 config 里的 find_dependency`）

test_package 的 conanfile 用 tc.variables 显式指路（gRPC_DIR/Protobuf_DIR/utf8_range_DIR/absl_DIR/OPENSSL_ROOT_DIR 指向制品仓包的 lib/cmake/<name>），CMakeLists 先 find 真实 config，再用 INTERFACE IMPORTED 桥接 CMakeDeps 期望的目标名，并预置 <dep>_FOUND=TRUE 跳过生成 config 里的 find_dependency

## 补充关键词

cmake_find_mode, find_dependency, gRPCConfig.cmake, grpc_DIR, target not found, INTERFACE IMPORTED, 大小写

---

*本文件由 `knowledge/drafts/DRAFT-E322-cmake-find-mode-none-target-bridge.kv` 字段派生生成（补齐 kv↔md 配套）；内容与 kv 一致，待主编审核 promote 后转入 `knowledge/doc/`。*
