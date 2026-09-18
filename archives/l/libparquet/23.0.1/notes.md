# libparquet 23.0.1 适配笔记

## 软件信息
- **名称**: Apache Parquet (C++) — Arrow 家族列存格式模块
- **版本**: 23.0.1
- **上游**: https://github.com/apache/arrow
- **Tag**: apache-arrow-23.0.1（与 libarrow/libarrow_acero 同源码）
- **许可证**: Apache-2.0
- **构建系统**: CMake (configure from cpp/ subdirectory)
- **语言**: C++20 (Arrow 23.0.1 SetupCxxFlags.cmake 强制 >= 20)

## 适配决策

### 组件配置（复用 libarrow 主件 #9874 配方，仅改组件开关）
| 组件 | 状态 | 原因 |
|------|------|------|
| ARROW_PARQUET | ⭐ ON | 本包主组件——列存格式读写 |
| ARROW_COMPUTE/CSV/JSON/FILESYSTEM/IPC | ON | 核心组件（与主件一致） |
| Thrift | BUNDLED | 制品仓未发布 thrift → 用 Arrow 自带 bundled 构建（thrift 0.22.0，FetchContent 从 archive.apache.org 下载——与源码包同域，CI worker 可达） |
| ARROW_FLIGHT/FLIGHT_SQL | OFF | 需 grpc+protobuf |
| ARROW_ORC/GANDIVA/CUDA/DATASET/ACERO/S3/GCS/HDFS/AZURE/SUBSTRAIT | OFF | 依赖未发布或不适用 |
| ARROW_JEMALLOC/MIMALLOC | OFF | 使用系统分配器 |
| PARQUET_REQUIRE_ENCRYPTION | OFF（默认） | 加密测试默认关闭，openssl 仍开启供主库使用 |

### Thrift BUNDLED 关键点
1. `conan download "thrift/*" -r=ohpcd --only-recipe` → 0 结果（未发布）→ 按 W0 依赖检查走 bundled
2. Arrow 的 ThirdpartyToolchain build_thrift() 用 FetchContent 拉 thrift 0.22.0（SHA256=794a0e455787960d9f27ab92c38e34da27e8deeda7a5db0e59dc64a00df8a1e5）
3. 下载源 archive.apache.org/dist/thrift/0.22.0/——与 apache-arrow 源码包同域（主件已验证 CI worker 可达该域）
4. thrift cmake_minimum_required(3.16)——本机/CI cmake 4.1.2 兼容；CMake>=3.26 才允许 bundled（ThirdpartyToolchain 硬检查）
5. Clang 环境自动应用 Arrow 自带 thrift-3187.patch（THRIFT-3268 警告抑制）
6. thrift BUNDLED 需要 boost locale+uuid headers（BOOST_SOURCE=SYSTEM 下从 conan boost 包取）

### 上游测试执行（clancyxie 口径：CI 跑不了就本地联网补跑）
- ARROW_BUILD_TESTS=ON + ARROW_TESTING=ON
- Arrow 的 add_test() 用 build-support/run-test.sh 包装（依赖 pushd/python/c++filt，OHOS 不可用）→ conanfile build() 直接执行 release/ 下的测试二进制本体（与 acero #9896 同法）
- parquet 测试目标：cpp/src/parquet/CMakeLists.txt 注册 12 个 add_parquet_test，其中 2 个 encryption 类受 PARQUET_REQUIRE_ENCRYPTION（默认 OFF）门控 → 默认注册 10 个
- 核心测试目标 52 个（同主件）+ parquet 10 个 = 62 个 ctest 目标全构建
- PARQUET_TEST_DATA 数据驱动测试：parquet-testing 仓库（github.com/apache/parquet-testing）本地联网下载，运行时注入 PARQUET_TEST_DATA 环境变量；CI 无 GitHub 外网跑不了的数据测试本地补跑
- ARROW_TEST_DATA 依赖仅 1 处（arrow_reader_writer_test.cc:4329，GTEST_SKIP 软门控，无数据自动跳过）

## 与主件/兄弟件的关系
- libarrow 主件 #9874：ARROW_PARQUET=OFF（thrift 未发布）
- libarrow_acero #9896：ARROW_ACERO=ON 超集包（acero 组件）
- libparquet（本包）：ARROW_PARQUET=ON 超集包（parquet 组件 + bundled thrift）——三者互不依赖，均为独立超集包（Arrow 的构建系统不支持单独构建 parquet 而不带 arrow 核心）

## 构建流程
1. 下载 apache-arrow-23.0.1.tar.gz（archive.apache.org，sha256: bd09adb4feac11fe49d1604f296618866702be610c86e2d513b561d877de6b18）
2. strip_root=True 解压到 src/
3. 应用 3 个补丁（与主件相同：skip_gtest_cxx_standard_check / fix_thirdparty_toolchain / skip_filesystem_example）
4. CMake configure from cpp/：ARROW_PARQUET=ON + THRIFT_SOURCE=BUNDLED
5. bundled thrift 0.22.0 FetchContent（configure 阶段从 archive.apache.org 下载）
6. 静态构建 (ARROW_BUILD_STATIC=ON, ARROW_BUILD_SHARED=OFF)
7. build() 内直接执行测试二进制（62 目标）

## 上游测试统计
- add_parquet_test 注册: 12 个（10 默认启用 + 2 encryption 门控关闭）
- add_arrow_test 核心: 52 个（同主件配置）
- 合计 ctest 目标: 62 个（全部构建并执行）
- gtest 用例级实测: 11227 执行 = 11116 PASS（99.0%）+ 38 FAIL（全在 arrow 核心，OHOS 平台语义差异与 #9874/#9896 定性一致）+ 73 gtest SKIPPED
- parquet 专用 10 目标带 parquet-testing 数据补跑: 2153 用例 = 2150 PASS + 0 FAIL + 3 SKIPPED（100%）
- arrow-buffer-test ResizeOOM 崩溃排除后 45/45 过；parquet-reader-test 带数据 159/159 过
- test_package: 3 项全过（SNAPPY round-trip / ZSTD 低层写+读回 / footer 元数据）

## SIMD 适配
- ARROW_SIMD_LEVEL=DEFAULT: aarch64 自动选择 NEON
- ARROW_RUNTIME_SIMD_LEVEL=MAX
- xsimd/13.2.0 跨平台 SIMD 抽象层

## 路径 B/C 评估
- 见 PR 正文补充说明（B/C 判定四道关卡逐项过）

## 平台限制记录
- 与主件相同的 OHOS 差异（时区数据库缺失 29 个/MemoryPool OOM 语义 5 个/HMDFS 文件语义 3 个/glibc 差异 1 个 = 38 失败）在 52 个核心测试上的失败模式一致（见 #9874/#9896 记录）
- parquet 专用 10 目标：带 parquet-testing 数据 2150/2153 = 100%（3 个 gtest SKIPPED：Lz4Codec LegacyLZ4NonHadoop 上游主动跳过 2 个 + reader-test 1 个）
- 已知限制：独立消费者静态链接直调 TypedColumnReader<T>::ReadBatch 低层虚接口 SIGSEGV（上游构建树内同路径 2153 用例全过，库功能完好；test_package 以 thrift footer 核验 + arrow 层读回覆盖低层写路径）
- bundled thrift 适配要点（知识沉淀候选）：
  1. build_thrift() 的 POP_FRONT CMAKE_MODULE_PATH 在 Conan 下错弹 conan generators 目录 → thrift include(DefineOptions) 命中 Arrow 版本缺 PRINT_CONFIG_SUMMARY → 配置崩溃（本包补丁修复）
  2. thrift 头 include boost/numeric/conversion/cast.hpp 等，SYSTEM boost 下需给 thrift::thrift INTERFACE 挂 Boost::headers（本包补丁修复）
  3. bundled thrift 对象聚合进 libarrow_bundled_dependencies.a 随包分发（勿手动拷贝 libthrift.a 避免双重符号）
  4. ARROW_THRIFT_URL 环境变量固定 archive.apache.org 下载源（CI 可达域）
