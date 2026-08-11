# martin 1.13.0 HarmonyOS PC 适配笔记

## 基本信息

- **上游**: https://github.com/maplibre/martin（tag martin-v1.13.0）
- **许可**: MIT OR Apache-2.0
- **构建系统**: cargo（Rust workspace：martin / martin-core / martin-tile-utils / mbtiles / martin-config-macros）
- **适配路径**: 路径 A（基础适配）
- **目标平台**: HarmonyOS PC (aarch64, os=OHOS)

## 适配摘要

- 上游为 Rust 编写的矢量瓦片服务器，支持 PostGIS/MBTiles/PMTiles。
- OHOS 策略：Rust 工具链用 Harmonybrew（`~/.harmonybrew/bin/cargo`，rustc 1.97.1；
  OHOS 上 rustup 不可用），`cargo build --release` 原生编译 aarch64-unknown-linux-ohos。
- 链接器：OHOS 无 `cc`，`RUSTFLAGS=-C linker=/data/service/hnp/bin/clang`，
  `.cargo/config.toml` 指定 `[target.aarch64-unknown-linux-ohos] linker = "clang"`。
- openssl-sys 依赖：从制品仓安装 `openssl/3.5.6`（conan）后设置
  `OPENSSL_DIR/OPENSSL_LIB_DIR/OPENSSL_INCLUDE_DIR`。
- aws-lc-sys（经 rustls/aws-config 引入）在 OHOS 上 CMake 无法自动识别处理器，
  必须设置 `OHOS_SDK_NATIVE=<ohos-sdk>/native` 以加载 ohos.toolchain.cmake，
  否则生成 generic 实现导致 chacha/aes 汇编符号缺失、链接失败。
- 上游默认特性 `webui`（npm/vite 前端，rolldown 无 OHOS 原生 binding，node 26 core dump）、
  `rendering`（maplibre-native C++ 大仓库 git 克隆）、`lambda` 在 OHOS 上不可用，
  配方固定编译服务端特性集：fonts,mbtiles,metrics,passthrough,pmtiles,postgres,
  sprites,styles,geojson,mlt。
- 产物：`martin`、`martin-cp`、`mbtiles` 三个二进制（application 包，bin/）。

## 本地验证（OHOS aarch64 实际执行）

- `cargo build --release` 成功；`martin --version` 输出 `martin 1.13.0`。
- 上游测试实际运行（cargo test --release）：
  - martin-core / martin-tile-utils / mbtiles / martin-config-macros 单元+集成测试：564 通过 / 0 失败 / 1 忽略
  - martin 主程序 bin 单测：24 通过 / 0 失败
  - martin 集成测试（binary_diagnostics / cors_test / mb_server_test）：22 通过 / 0 失败
  - 合计：610 通过 / 0 失败 / 1 忽略（通过率 100%，忽略项为上游自带 ignore 用例）
  - doc-tests 因 OHOS rustdoc 平台限制无法执行（rustdoc 执行 proc-macro doctest 报
    "No such file or directory"），属平台环境限制，非用例失败。
- conan create 本地 CI 模拟：通过（详见 .ci-result.json / ci-local-output.log）。

## 已知限制

- `webui`（web 管理界面）与 `rendering`（静态地图渲染）特性未启用：前者需 npm/vite
  前端工具链（OHOS 无 rolldown 原生 binding），后者需 maplibre-native C++ 源码树
  （含大量子模块，OHOS 网络下 git 克隆不稳定）。核心瓦片服务能力不受影响。
- 需要 PostgreSQL 外部服务的集成测试（pg_*_test、pmt_minio_test 等）未纳入本地统计，
  依赖外部数据库/对象存储实例。
