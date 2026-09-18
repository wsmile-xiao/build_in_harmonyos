# libarrow_acero 23.0.1 适配笔记

## 软件信息
- **名称**: Apache Arrow Acero (Arrow Compute Engine)
- **版本**: 23.0.1
- **上游**: https://github.com/apache/arrow
- **Tag**: apache-arrow-23.0.1（与 libarrow 主件同源码同 tag）
- **许可证**: Apache-2.0
- **构建系统**: CMake (configure from cpp/ subdirectory)
- **语言**: C++20 (required by Arrow 23.0.1)

## 适配决策

### 与主件 libarrow 的关系
- **同源码**: 都从 apache-arrow-23.0.1.tar.gz 构建
- **同构建系统**: CMake，configure from cpp/ subdirectory
- **不同组件**: libarrow 主件 ARROW_ACERO=OFF；libarrow_acero ARROW_ACERO=ON
- **高度复用**: conanfile.py 基于主件配方，仅改 name、ARROW_ACERO 选项、package_info 组件

### acero 组件说明
Arrow Acero 是 Arrow 的流计算引擎模块（Arrow Compute Engine）。
- 对应 CMake 选项: ARROW_ACERO=ON（默认 ON）
- 构建产物: libarrow_acero.a / libarrow_acero.so
- 依赖: libarrow（核心库）
- 上游 CMake target: arrow_acero

### 禁用组件（依赖缺失或平台不适用）
| 组件 | 原因 |
|------|------|
| ARROW_PARQUET | 强制依赖 thrift（制品仓未发布 thrift） |
| ARROW_FLIGHT | 需 grpc + protobuf |
| ARROW_FLIGHT_SQL | 依赖 ARROW_FLIGHT |
| ARROW_ORC | 需 orc 库（未发布） |
| ARROW_GANDIVA | 需 LLVM |
| ARROW_CUDA | 无 CUDA 支持 |
| ARROW_DATASET | 独立组件（依赖 acero，但本包不构建 dataset） |
| ARROW_S3/GCS/HDFS/AZURE | 云存储后端，OHOS 不适用 |
| ARROW_SUBSTRAIT | 依赖 dataset+parquet |
| ARROW_JEMALLOC | 使用系统分配器 |
| ARROW_MIMALLOC | 禁用第三方分配器 |

### 启用组件
| 组件 | 依赖 |
|------|------|
| ARROW_ACERO | (本包主组件，依赖 arrow) |
| ARROW_IPC | (核心，默认 ON) |
| ARROW_COMPUTE | xsimd/13.2.0, re2, utf8proc |
| ARROW_CSV | (核心) |
| ARROW_JSON | rapidjson/1.1.0 |
| ARROW_FILESYSTEM | (核心) |
| ARROW_WITH_ZLIB | zlib/1.3.1 |
| ARROW_WITH_LZ4 | lz4/1.10.0 |
| ARROW_WITH_ZSTD | zstd/1.5.7 |
| ARROW_WITH_BZ2 | bzip2/1.0.8 |
| ARROW_WITH_SNAPPY | snappy/1.1.7 |
| ARROW_WITH_RE2 | re2/2024-04-01 |
| ARROW_WITH_UTF8PROC | utf8proc/2.11.3 |
| ARROW_USE_OPENSSL | openssl/3.0.16 |
| ARROW_USE_BOOST | boost/1.84.0 |

## SIMD 适配
- `ARROW_SIMD_LEVEL=DEFAULT`: 在 aarch64 上自动选择 NEON 指令集
- `ARROW_RUNTIME_SIMD_LEVEL=MAX`: 运行时自动检测最大可用 SIMD 级别
- xsimd/13.2.0 提供跨平台 SIMD 抽象层

## 构建流程
1. 下载 apache-arrow-23.0.1.tar.gz (sha256: 9a9a057bba3aa7080abc2ba8e7a079effa74626a4f308ac56bfce035d31ef1ac)
2. strip_root=True 解压到 src/
3. CMake configure from cpp/ subdirectory
4. ARROW_DEPENDENCY_SOURCE=SYSTEM 使用 CMakeDeps 管理依赖
5. ARROW_ACERO=ON 构建流计算引擎
6. 静态构建 (ARROW_BUILD_STATIC=ON, ARROW_BUILD_SHARED=OFF)

## 上游测试统计
- add_arrow_test 调用: 52 个（acero 相关测试包含在 arrow 测试中）
- acero 专用测试源文件: 约 30 个 (*_test.cc in cpp/src/acero/)
- 适配后: 构建不含测试 (ARROW_BUILD_TESTS=OFF)，test_package 验证 acero API

## package_info 组件
- `arrow`: 核心库（libarrow.a），acero 依赖
- `arrow_compute`: 计算库（libarrow_compute.a），可选
- `arrow_acero`: 流计算引擎（libarrow_acero.a），本包主组件

## 最终状态
- 编译结果: 成功 (conan create PASS)
- 测试结果: test_package PASS (ExecPlan API 验证通过)
- conan-verify: PASS (G1-G4, L2/L4/L5)
- W3 本地 CI: PASS
- status: built
- COMPLETED
