# apache-arrow 24.0.0 上游测试入口清单

## 上游测试体系概览

Apache Arrow C++ 上游测试主要位于源码包 `cpp/` 目录, 通过 CMake/CTest 生成测试入口, 测试实现使用 Google Test。测试覆盖范围包括:

- Arrow Core: array、buffer、memory、io、filesystem、ipc 等。
- Compute: scalar、vector、cast、temporal 等计算 kernel。
- 数据格式和数据集: CSV、JSON、Parquet、Dataset。
- 执行引擎: Acero。
- 其他扩展: Flight、ORC、Gandiva、CUDA 等, 需要额外依赖、服务或硬件。

由于 GTest 一个可执行文件内可能包含大量 test case, 本报告用 CTest target 作为已迁移执行范围的稳定统计单位, 不把“1000+ GTest case”直接写成完整通过率。

## 本 PR 正式 recipe 启用模块

当前 Conan recipe 重点提供 C++ 核心消费能力:

- `ARROW_IPC=ON`
- `ARROW_COMPUTE=ON`
- `ARROW_CSV=ON`
- `ARROW_FILESYSTEM=ON`
- `ARROW_JSON=ON`

为降低 CI 网络和重依赖风险, 当前基础包未启用:

- Flight
- Dataset
- ORC
- Parquet
- Gandiva
- CUDA

扩展测试阶段为了验证路径 B 覆盖度, 曾额外启用 Parquet、Dataset、Acero 等模块进行上游 CTest 分层验证。该扩展测试不改变当前 recipe 的正式模块承诺。

## 已执行 CTest target 范围

| 范围 | CTest target 数 | 说明 |
| --- | ---: | --- |
| 当前 recipe 启用核心模块对应 target | 52 | 初始核心模块范围 |
| Parquet 新增 target | 11 | 启用 `ARROW_PARQUET=ON` 后新增 |
| Dataset/Acero 新增 target | 26 | 启用 `ARROW_DATASET=ON` 后新增 |
| 最大扩展执行范围 | 89 | 核心 + Parquet + Dataset + Acero |

## Parquet target 清单

- `parquet-internals-test`
- `parquet-encoding-test`
- `parquet-reader-test`
- `parquet-writer-test`
- `parquet-chunker-test`
- `parquet-arrow-reader-writer-test`
- `parquet-arrow-index-test`
- `parquet-arrow-internals-test`
- `parquet-arrow-metadata-test`
- `parquet-file-deserialize-test`
- `parquet-schema-test`

## Dataset/Acero target 清单

Acero:

- `arrow-acero-plan-test`
- `arrow-acero-source-node-test`
- `arrow-acero-fetch-node-test`
- `arrow-acero-order-by-node-test`
- `arrow-acero-hash-join-node-test`
- `arrow-acero-pivot-longer-node-test`
- `arrow-acero-asof-join-node-test`
- `arrow-acero-sorted-merge-node-test`
- `arrow-acero-tpch-node-test`
- `arrow-acero-union-node-test`
- `arrow-acero-aggregate-node-test`
- `arrow-acero-util-test`
- `arrow-acero-hash-aggregate-test`
- `arrow-acero-test-util-internal-test`

Dataset:

- `arrow-dataset-dataset-test`
- `arrow-dataset-dataset-writer-test`
- `arrow-dataset-discovery-test`
- `arrow-dataset-file-ipc-test`
- `arrow-dataset-file-test`
- `arrow-dataset-partition-test`
- `arrow-dataset-scanner-test`
- `arrow-dataset-subtree-test`
- `arrow-dataset-write-node-test`
- `arrow-dataset-file-csv-test`
- `arrow-dataset-file-json-test`
- `arrow-dataset-file-parquet-test`

## 未纳入完整执行统计的上游范围

以下范围存在额外语言运行时、服务、硬件或重依赖, 本 PR 不将其写成通过:

- Python、Java、R 等多语言绑定测试。
- Flight/gRPC 服务式测试。
- CUDA/GPU 相关测试。
- Gandiva/LLVM 相关测试。
- ORC 等额外重依赖格式测试。
- benchmark、示例和非 CTest 标准入口。

该边界与路径 B 申请口径一致: 真实执行可迁移 C++ CTest 子集, 对不可执行子集单独说明原因。

## ORC / Flight 首轮探针 inventory

为避免把重依赖模块直接扩大到基础 recipe, ORC 和 Flight 当前先按 inventory + 首轮探针处理。

### ORC

上游 CMake 入口:

- `cpp/src/arrow/adapters/orc/CMakeLists.txt`
- `add_arrow_test(adapter_test ... "arrow-orc" ...)`

代表性 target:

- `arrow-orc-adapter-test`

依赖展开:

- `ARROW_ORC=ON` 会开启 `ARROW_WITH_PROTOBUF=ON`。
- `ARROW_ORC=ON` 会开启 `ARROW_WITH_ZLIB=ON`。
- `ThirdpartyToolchain.cmake` 中 ORC 默认通过 `ARROW_ORC_URL` 或 Apache ORC 下载地址获取源码。

当前缓存状态:

- 隔离真机已有 Boost / GoogleTest FetchContent 缓存。
- 未发现 ORC / protobuf / zlib 的可复用源码缓存。

预期首轮探针:

- 配置 `ARROW_ORC=ON`、`ARROW_BUILD_TESTS=ON`。
- 尝试构建 `arrow-orc-adapter-test`。
- 若停在 ORC/protobuf/zlib 下载或配置阶段, 记录为重依赖环境缺口, 不写成 target 失败。

已执行首轮探针:

- RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-orc-probe-v1-20260726-224750-37131`
- 结果: 1200 秒上限退出, exit code 124。
- 进展: CMake 配置阶段已进入 `Protobuf: Building Protocol Buffers from source using FetchContent`。
- 判断: ORC target 尚未进入构建/运行阶段, 当前证据说明 ORC 会牵出 protobuf 等重依赖源码构建, 不写作 `arrow-orc-adapter-test` 失败。

### Flight

上游 CMake 入口:

- `cpp/src/arrow/flight/CMakeLists.txt`
- `cpp/src/arrow/flight/integration_tests/CMakeLists.txt`
- `cpp/src/arrow/flight/sql/CMakeLists.txt`
- `cpp/src/arrow/flight/sql/odbc/*/CMakeLists.txt`

代表性 target:

- `arrow-flight-internals-test`
- `arrow-flight-test`
- `arrow-flight-integration-test`
- `arrow-flight-sql-test`
- `odbc-spi-impl-test`
- `arrow-flight-sql-odbc-test`

依赖展开:

- `ARROW_FLIGHT=ON` 会开启 `ARROW_WITH_GRPC=ON`。
- `ARROW_WITH_GRPC=ON` 会开启 `ARROW_WITH_RE2=ON` 和 `ARROW_WITH_ZLIB=ON`。
- `ARROW_FLIGHT=ON` 也会开启 `ARROW_WITH_PROTOBUF=ON`。
- `ARROW_FLIGHT=ON` 会强制 OpenSSL 依赖, 需要 `OpenSSL::SSL` / `OpenSSL::Crypto`。
- Flight integration / SQL / ODBC 还涉及服务进程、端口/Unix socket、ODBC 或额外客户端工具。

当前缓存状态:

- 隔离真机已有 Boost / GoogleTest FetchContent 缓存。
- 已通过预解包方式得到 gRPC 1.46.3 source cache, 其中 tarball 内 link 条目已展开为普通副本。
- 未发现 OpenSSL / BoringSSL 的可复用库缓存。

预期首轮探针:

- 配置 `ARROW_FLIGHT=ON`、`ARROW_BUILD_TESTS=ON`。
- 优先尝试构建 `arrow-flight-internals-test`。
- 若停在 gRPC/protobuf/re2/zlib 下载或配置阶段, 记录为服务式/重依赖测试缺口, 不写成 Flight target 失败。

当前状态:

- RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v2-20260727-040342-62286`
- v2 结果: gRPC 1.46.3 tarball 下载完成, 但 CMake/libarchive 解包在 symlink/hardlink 条目处失败; 当前真机文件系统对 link 创建返回 `Permission denied`。
- 处理: 使用 `scripts/ohos_extract_tar_no_links.py` 将 gRPC tarball 中 12 个 link 条目展开为普通文件/目录副本。
- RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v3-20260727-042031-3517`
- v3 结果: 预解包 gRPC 后越过 FetchContent 解包, 但 Flight tests 要求静态 Arrow 测试树。
- RUN_DIR: `/storage/Users/currentUser/ohos-test-runs/codex-apache-arrow-upstream-flight-probe-v4-20260727-043233-9482`
- v4 结果: 静态 Arrow + 预解包 gRPC 配置阶段完成, CMake generate 停在 `OpenSSL::SSL` / `OpenSSL::Crypto` target 缺失。
- 判断: `arrow-flight-internals-test` 尚未进入构建/运行阶段, 当前证据说明 Flight 会牵出 gRPC/protobuf/re2/zlib/OpenSSL 以及服务式测试链路, 不写作 Flight target 失败。
