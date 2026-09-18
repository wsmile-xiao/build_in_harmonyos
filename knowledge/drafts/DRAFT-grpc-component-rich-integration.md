# registry 组件富 cmake 包（cmake_find_mode=none）作为下游库依赖时的五件套接线法

## 背景

libarrow_flight 23.0.1（Arrow Flight RPC）适配中，制品仓的 grpc/1.70.0 与 protobuf/33.6 都是 `cmake_find_mode=none` 的组件富 CMake 包（保留上游原生 gRPCConfig.cmake / protobuf-config.cmake，CMakeDeps 不为其生成 config 文件）。Arrow 上游构建系统（ThirdpartyToolchain + FindgRPCAlt）与 conan 消费链路在四个点上不兼容，连环报错。

## 错误签名（可机器匹配）

```
ERROR: error generating context for 'X': Component 'grpc::grpc++' not found in 'grpc' p
CMake Error: The link interface of target ... contains: openssl::openssl ... but the target was not found
CMake Error: By not providing "Findgrpc.cmake" ... find a package configuration file provided by "grpc"
CMake Error: The link interface of target ... contains: grpc::grpc ... but the target was not found
```

## 根因（四坑连环）

1. **target 名不匹配**：原生 config 导出 `gRPC::grpc++`；conan 组件引用必须是 `pkgname::x` 字面量，无 components 的包只能写 `grpc::grpc`（写 `grpc::grpc++` 会报 `Component 'grpc::grpc++' not found in 'grpc' package`）。
2. **大小写双轨**：上游 FindgRPCAlt 用 `find_package(gRPC CONFIG)`（大写），消费者 config 里 CMakeDeps 生成 `find_dependency(grpc)`（小写）；CMake 变量区分大小写，`gRPC_FOUND` ≠ `grpc_FOUND`，小写查找去找 grpcConfig.cmake（文件名也是大小写敏感的，实际文件是 gRPCConfig.cmake）→ 找不到。
3. **openssl target 双轨**：原生 gRPCTargets.cmake 引用 `openssl::openssl` target——只有 conan 的 openssl-config.cmake 定义它；若上游库已用内置 FindOpenSSL（OPENSSL_ROOT_DIR，MODULE 模式）成功解析 openssl，conan config 永不加载 → gRPCTargets.cmake 报 target not found。
4. **交叉编译插件缺失**：`CMAKE_CROSSCOMPILING=1` 时 gRPCConfig.cmake 不 include gRPCPluginTargets.cmake → `gRPC::grpc_cpp_plugin` target 不存在 → proto 代码生成挂掉。

## 解决方案：五件套接线法

```python
# 1. requires 显式声明（conan 校验直接依赖必须被组件引用）
self.requires("grpc/1.70.0")
self.requires("protobuf/33.6")

# 2. toolchain 注入原生 config 路径
tc.variables["gRPC_DIR"] = os.path.join(grpc.package_folder, "lib", "cmake", "grpc")
tc.variables["Protobuf_DIR"] = os.path.join(protobuf.package_folder, "lib", "cmake", "protobuf")
tc.variables["utf8_range_DIR"] = os.path.join(protobuf.package_folder, "lib", "cmake", "utf8_range")
tc.variables["absl_DIR"] = os.path.join(abseil.package_folder, "lib", "cmake", "absl")

# 3. 补丁：上游 resolve gRPC 前预加载 conan openssl config
#    （补丁打在 ThirdpartyToolchain.cmake 的 gRPC resolve 块前）
if(NOT TARGET openssl::openssl)
  find_package(openssl CONFIG REQUIRED)
endif()

# 4. 交叉编译插件路径（Arrow 专属变量，其他库需查各自 *_PLUGIN 变量）
tc.variables["ARROW_GRPC_CPP_PLUGIN"] = os.path.join(grpc.package_folder, "bin", "grpc_cpp_plugin")
# registry 的 grpc_cpp_plugin 是 OHOS 原生 arm64 二进制——构建主机（aarch64 OHOS）
# 可直接运行，运行时需 LD_LIBRARY_PATH 指向 SDK llvm/lib（libc++_shared.so）

# 5. bridge 文件（关键）：包内 ship 一个 cmake_build_modules 别名文件
#    cmake/bridge-grpc-targets.cmake:
#      if(NOT TARGET grpc::grpc)
#        if(TARGET gRPC::grpc++)
#          add_library(grpc::grpc INTERFACE IMPORTED)
#          set_target_properties(grpc::grpc PROPERTIES INTERFACE_LINK_LIBRARIES gRPC::grpc++)
#        endif()
#      endif()
#      # 同样桥接 protobuf::protobuf -> protobuf::libprotobuf
#    conanfile: exports_sources = "cmake/*"
#    package(): copy 到 lib/cmake/（注意在 rmdir lib/cmake 之后 copy）
#    package_info(): set_property("cmake_build_modules", ["lib/cmake/bridge-grpc-targets.cmake"])
#    组件引用: requires.append("grpc::grpc") + requires.append("protobuf::protobuf")
```

test_package 侧配套：

```cmake
# 先加载原生 config（大写名），再短路小写 find_dependency
find_package(gRPC CONFIG REQUIRED)
set(grpc_FOUND TRUE)
set(protobuf_FOUND TRUE)
set(Protobuf_FOUND TRUE)
find_package(ArrowFlight REQUIRED)  # 组件全在单一 config 里
```

## 验证

- libarrow_flight/23.0.1 本地 conan create 全绿：55 个上游测试二进制 54 PASS（唯一失败 arrow-buffer-test 的 ResizeOOM 为 OHOS 平台差异）
- Flight 模块 152 GTest 用例：148 PASS + 4 个 TestTls（gRPC TLS 握手工厂 OHOS 限制）
- test_package 真实 localhost gRPC Flight RPC 往返（server Init → client Connect → ListFlights → Shutdown）PASS

## 适用范围

任何把制品仓 `cmake_find_mode=none` 组件富包（grpc/protobuf 及同类）作为依赖的下游库适配。
