# libarrow_flight 适配笔记

## 软件信息
- **名称**: Apache Arrow Flight RPC (gRPC data transport)
- **版本**: 23.0.1
- **上游**: https://github.com/apache/arrow
- **Tag**: apache-arrow-23.0.1（与 libarrow/libarrow_acero/libparquet 同源码同 tag）
- **许可证**: Apache-2.0
- **构建系统**: CMake (configure from cpp/ subdirectory)
- **语言**: C++20 (required by Arrow 23.0.1)

## 适配决策

### 与 libarrow 系列的关系
- **同源码**: apache-arrow-23.0.1.tar.gz（sha256 bd09adb4feac11fe49d1604f296618866702be610c86e2d513b561d877de6b18）
- **不同组件**: 本包 ARROW_FLIGHT=ON + ARROW_FLIGHT_SQL=ON
- **依赖核心**: grpc/1.70.0（制品仓已发布，含 OHOS armv8 binary 与 grpc_cpp_plugin 原生工具）

### Flight 组件说明
Arrow Flight 是基于 gRPC 的高性能数据传输协议。
- 对应 CMake 选项: ARROW_FLIGHT=ON（DEPENDS ARROW_IPC）
- Flight SQL 扩展: ARROW_FLIGHT_SQL=ON（DEPENDS ARROW_FLIGHT，同一 gRPC 栈）
- 构建产物: libarrow_flight.a / libarrow_flight_sql.a
- 上游 CMake targets: arrow_flight / arrow_flight_sql

### gRPC 集成（本包核心难点）
1. **registry grpc/1.70.0** 包是组件富 CMake 包（cmake_find_mode=none，自带 gRPCConfig.cmake + gRPCTargets.cmake + gRPCPluginTargets.cmake），提供 gRPC::grpc++ / gRPC::grpc 等 imported targets
2. **显式路径注入**（gRPC_DIR / Protobuf_DIR / utf8_range_DIR / absl_DIR）——镜像 grpc 配方自己的做法；因为 cmake_find_mode=none 的包不会被 CMakeDeps 生成 config，必须指向包内原生 config
3. **openssl::openssl 预加载补丁**: Arrow 自己用内置 FindOpenSSL（OPENSSL_ROOT_DIR + MODULE 模式）解析 openssl 成功后不会加载 conan 的 openssl-config.cmake，但 gRPCTargets.cmake 引用 `openssl::openssl` imported target——补丁在 resolve_dependency(gRPC) 前显式 find_package(openssl CONFIG REQUIRED)
4. **交叉编译插件路径**: gRPCConfig.cmake 只在 NOT CMAKE_CROSSCOMPILING 时 include gRPCPluginTargets（gRPC::grpc_cpp_plugin），OHOS 交叉构建时该 target 不存在——通过 Arrow 的 ARROW_GRPC_CPP_PLUGIN 变量直接指向 registry 包内 bin/grpc_cpp_plugin（OHOS 原生 arm64 二进制，构建主机可原生运行）
5. **protoc 运行时**: protobuf/33.6 的 protoc 是 OHOS arm64 二进制（动态链接 libc++_shared.so），构建时需 LD_LIBRARY_PATH 指向 SDK llvm/lib（profile buildenv 已含 + 配方内 Environment 兜底）
6. **ABI 对齐**: grpc/1.70.0 固定依赖 protobuf/33.6 + abseil-cpp/20260107.1 + openssl/3.5.6 + c-ares/1.34.6 + re2 + zlib——本包所有依赖与 grpc 的注册表构建保持一致，openssl 用 3.5.6（不是 libarrow_acero 的 3.0.16，避免与 grpc 的 ABI 冲突）

### 禁用组件
| 组件 | 原因 |
|------|------|
| ARROW_PARQUET | 强制依赖 thrift（制品仓未发布） |
| ARROW_ORC | 需 orc 库（未发布） |
| ARROW_GANDIVA | 需 LLVM |
| ARROW_CUDA | 无 CUDA 支持 |
| ARROW_DATASET/ACERO | 独立组件（libarrow_dataset/libarrow_acero 单独成包） |
| ARROW_S3/GCS/HDFS/AZURE | 云存储后端，OHOS 不适用 |
| ARROW_SUBSTRAIT | 依赖 dataset+parquet |
| ARROW_JEMALLOC/MIMALLOC | 使用系统分配器 |

### 启用组件
| 组件 | 依赖 |
|------|------|
| ARROW_FLIGHT ⭐ | grpc/1.70.0, protobuf/33.6 |
| ARROW_FLIGHT_SQL ⭐ | ARROW_FLIGHT, sqlite3/3.49.1（测试 server） |
| ARROW_IPC | （核心，Flight 前置） |
| ARROW_COMPUTE | xsimd/13.2.0, re2, utf8proc |
| ARROW_CSV/JSON/FILESYSTEM | （核心） |
| ARROW_WITH_ZLIB/LZ4/ZSTD/BZ2/SNAPPY | 压缩编解码 |
| ARROW_USE_BOOST | boost/1.84.0 |
| ARROW_USE_OPENSSL | openssl/3.5.6（grpc ABI 对齐） |

## 构建流程
1. 下载 apache-arrow-23.0.1.tar.gz（Apache 官方归档）
2. 四个补丁: skip_gtest_cxx_standard_check + fix_thirdparty_toolchain + skip_filesystem_example + preload_openssl_config_for_grpc
3. CMake configure from cpp/，ARROW_DEPENDENCY_SOURCE=SYSTEM + gRPC_DIR/Protobuf_DIR/utf8_range_DIR/absl_DIR + ARROW_GRPC_CPP_PLUGIN
4. protoc 生成 Flight.pb.cc/Flight.grpc.pb.cc/FlightSql.pb.cc（构建时原生运行）
5. 静态构建 (ARROW_BUILD_STATIC=ON, ARROW_BUILD_SHARED=OFF)

## 上游测试统计（rule4 口径：上游构建系统注册数）
- flight 模块 add_arrow_test 注册: 3 个测试目标
  - flight_internals_test (30 GTest 用例)
  - flight_test (48 TEST 宏 → 95 GTest 用例，含参数化展开)
  - flight_sql_test (27 GTest 用例, sql/server_test.cc 26 + sql/server_session_middleware_internals_test.cc 1)
- 构建过程连带 arrow 核心 52 个测试目标（共 ~9300 GTest 用例）
- Flight 模块实测: 152 用例执行，148 通过，4 个 TestTls 失败（gRPC TLS 握手工厂 OHOS 平台限制: Handshaker factory creation failed with TSI_INVALID_ARGUMENT）
- arrow 核心 52 目标中 51 PASS，arrow-buffer-test 的 ResizeOOM 用例段错误（OHOS 上 INT64_MAX 分配触发 SIGSEGV 而非返回 OutOfMemory——平台差异）
- 适配后: ARROW_BUILD_TESTS=ON 构建上游测试并直接运行测试二进制（绕过 run-test.sh wrapper，长驻 server 类二进制跳过）

## 已知坑
- Arrow 的 add_test() 用 build-support/run-test.sh 包装（pushd + python/c++filt），OHOS 设备不可用——直接运行测试二进制收集 gtest 结果
- Protobuf_SOURCE/gRPC_SOURCE 不能设 BUNDLED（会强制 FetchContent 从 GitHub 下载，CI 无网）——保持 SYSTEM 默认并显式注入路径
- protobuf 33.6 生成代码要求 C++20，与 Arrow 23.0.1 的 C++20 要求一致
