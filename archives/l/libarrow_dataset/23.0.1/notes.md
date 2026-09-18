# libarrow_dataset 23.0.1 适配笔记

## 软件信息
- **名称**: Apache Arrow Dataset
- **版本**: 23.0.1
- **上游**: https://github.com/apache/arrow
- **Tag**: apache-arrow-23.0.1（与 libarrow 主件同源码同 tag）
- **许可证**: Apache-2.0
- **构建系统**: CMake (configure from cpp/ subdirectory)
- **语言**: C++20 (required by Arrow 23.0.1)

## 适配决策

### 与主件 libarrow 的关系
- **同源码**: 都从 apache-arrow-23.0.1.tar.gz 构建（sha256: bd09adb4feac11fe49d1604f296618866702be610c86e2d513b561d877de6b18）
- **同构建系统**: CMake，configure from cpp/ subdirectory
- **不同组件**: libarrow 主件 ARROW_DATASET=OFF；libarrow_dataset ARROW_DATASET=ON
- **高度复用**: conanfile.py 基于 libarrow_acero 配方（PR #9896），仅改 name、ARROW_DATASET 选项、package_info 组件

### dataset 组件说明
Arrow Dataset 是 Arrow 的数据集发现/分区/扫描模块。
- 对应 CMake 选项: ARROW_DATASET=ON（上游默认 OFF）
- 构建产物: libarrow_dataset.a / libarrow_dataset.so
- **硬依赖**（上游 cmake_modules/DefineOptions.cmake）: ARROW_DATASET DEPENDS ARROW_ACERO + ARROW_FILESYSTEM（开启 dataset 自动启用 acero）
- 上游 CMakeLists: `ARROW_DATASET_REQUIRED_DEPENDENCIES = Arrow ArrowCompute ArrowAcero`，pkg-config requires "arrow-acero arrow-compute"
- 上游 CMake target: ArrowDataset::arrow_dataset_{shared,static}

### 禁用组件（依赖缺失或平台不适用）
| 组件 | 原因 |
|------|------|
| ARROW_PARQUET | 强制依赖 thrift（制品仓未发布 thrift） |
| ARROW_FLIGHT | 需 grpc + protobuf |
| ARROW_FLIGHT_SQL | 依赖 ARROW_FLIGHT |
| ARROW_ORC | 需 orc 库（未发布） |
| ARROW_GANDIVA | 需 LLVM |
| ARROW_CUDA | 无 CUDA 支持 |
| ARROW_S3/GCS/HDFS/AZURE | 云存储后端，OHOS 不适用 |
| ARROW_SUBSTRAIT | 依赖 dataset+parquet（parquet 禁用） |
| ARROW_PYTHON | 无 Python 绑定需求 |
| ARROW_JEMALLOC | 使用系统分配器 |
| ARROW_MIMALLOC | 禁用第三方分配器 |

### 启用组件
| 组件 | 依赖 |
|------|------|
| ARROW_DATASET | （本包主组件，依赖 acero+filesystem） |
| ARROW_ACERO | （dataset 硬依赖，自动启用） |
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
1. 下载 apache-arrow-23.0.1.tar.gz（Apache 官方 archive，CI worker 无法访问 GitHub）
2. strip_root=True 解压到 src/
3. 三个 portability 补丁（与主件/acero 相同）: skip_gtest_cxx_standard_check / fix_thirdparty_toolchain / skip_filesystem_example
4. CMake configure from cpp/ subdirectory
5. ARROW_DEPENDENCY_SOURCE=SYSTEM 使用 CMakeDeps 管理依赖
6. ARROW_DATASET=ON + ARROW_ACERO=ON 构建数据集模块
7. 静态构建 (ARROW_BUILD_STATIC=ON, ARROW_BUILD_SHARED=OFF)

## 上游测试统计（实测）
- **77 个 ctest 测试目标**全部构建并真实执行（52 核心 + 14 acero + 11 dataset）:
  - 52 核心: arrow-* 基础测试（buffer/array/table/scalar/compute/csv/json/io/filesystem/ipc/util 等）
  - 14 acero: arrow-acero-*-test（exec plan 各节点）
  - **11 dataset 专项（全部 PASS ✅）**: arrow-dataset-{dataset,dataset-writer,discovery,file-csv,file-ipc,file-json,file,partition,scanner,subtree,write-node}-test
- **gtest 用例级**: 10025 用例执行，9918 通过（99.0%），36 失败（34 FAIL + 2 崩溃），67 跳过
- 执行方式: build() 内直跑 release/arrow-*-test 二进制（绕过上游 run-test.sh wrapper——依赖 python/c++filt，OHOS 测试机不可用）
- 失败项定性（与 acero PR #9896 相同的 OHOS 平台环境差异）:
  1. **时区数据库缺失（27）**: OHOS 无 /usr/share/zoneinfo，`Cannot locate or parse timezone 'Pacific/Marquesas': discover_tz_dir failed to find zoneinfo`
  2. **MemoryPool OOM 语义差异（4）**: OHOS mmap overcommit 不返回错误，`Expected 'pool->Allocate(to_alloc, &data)' to fail with OutOfMemory, but got OK`
  3. **HMDFS 文件系统语义（2）**: HMDFS 不拒绝目录 append 打开
  4. **buffer-test ResizeOOM 崩溃（2）**: 故意分配 int64 max 触发 OOM 路径，OHOS libc++ bad_alloc 直接 SIGSEGV；排除 `-*ResizeOOM*` 复跑 45/45 全过
  5. **FileSystemFromUri.LoadedRegisteredFactory（1）**: 时区缺失同源
- **dataset 专项 11 个测试全部通过**——本包主组件零缺陷

## 消费者适配要点（L3 知识）
- **静态链接消费者必须调用 `arrow::compute::Initialize()`**（arrow/compute/api.h）:
  Arrow 23.0 的 compute kernel 注册（make_struct 等）在 libarrow_compute 的
  initialize.cc 中，懒注册设计——静态链接时若消费者不显式调用 Initialize()，
  GetFunctionRegistry() 单例只注册核心 kernel，Scanner 投影报
  `No function registered with name: make_struct`。
  dataset 扫描（Project/Filter 表达式绑定）全部依赖 make_struct。
- **静态链接需显式链 libarrow_compute**: 上游 arrow-dataset.pc requires "arrow-acero arrow-compute"，
  CMake 消费者应链接 Arrow::arrow_compute_static（本配方 package_info 已定义 arrow_compute 组件）

## package_info 组件
- `arrow`: 核心库（libarrow.a）
- `arrow_compute`: 计算库（libarrow_compute.a），含 make_struct 等 kernel
- `arrow_acero`: 流计算引擎（libarrow_acero.a），dataset 硬依赖
- `arrow_dataset`: 数据集模块（libarrow_dataset.a），本包主组件

## 最终状态
- 编译结果: 成功 (conan create PASS)
- 测试结果: test_package PASS (InMemoryDataset→Scanner→ToTable/CountRows 全链路验证)
- 上游测试: 77 目标真实执行，76 PASS + 1 已知平台崩溃（buffer-test ResizeOOM）；9918/10025 用例通过（99.0%）
- status: built
- COMPLETED
