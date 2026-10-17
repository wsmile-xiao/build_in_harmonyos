- **三方库名称**：martin
- **上游版本**：1.13.0（tag：martin-v1.13.0）
- **上游仓库地址**：https://github.com/maplibre/martin
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（编译SKILL）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 588 | 来源：各 crate `src/` 内 `#[test]`/`#[tokio::test]`（martin 主包 bin 单测 24 + martin-core/tile-utils/mbtiles/config-macros 564） |
| 集成测试 | 22 | 来源：`martin/tests/` 的 binary_diagnostics、cors_test、mb_server_test（已实际运行） |
| 其他测试 | 1 | 上游自带 `#[ignore]` 用例（忽略项，不计入通过/失败） |
| **合计** | **611** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 588 | 不变 | 全部在 OHOS aarch64 本地实际运行 |
| 集成测试 | 22 | 不变 | cors/mb_server/binary_diagnostics 本地运行通过 |
| 鸿蒙特有测试 | 3 | 新增 | test_package：martin --version、martin --help、mbtiles --help 执行验证 |
| **合计** | **613** | **+3** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游 martin-v1.13.0 自带完整 Rust 测试套件（23 个 `*_test.rs` + 27 个 `tests/` 文件），
> 本地 OHOS aarch64 实际运行 610 项全部通过；doc-tests 因 OHOS rustdoc 无法执行
> proc-macro doctest 属平台限制，非用例失败。test_package 额外新增 3 条二进制可执行性验证。

## 验证结果

- 编译状态：通过（`cargo build --release` 成功，产出 martin / martin-cp / mbtiles 三个二进制；`martin --version` 输出 `martin 1.13.0`）
- 上游测试用例通过率：610/610（100.00%）（另有 1 项上游自带 `#[ignore]` 忽略）
- 新增测试用例通过率：3/3（100.00%）

## 补充说明

- **本地 CI 模拟（conan create）**：`conan create` 在 ohos-aarch64 profile 下成功，
  包内三个二进制经 test_package 实际执行验证通过（详见 `.ci-result.json` 与 `ci-local-output.log`）。
- **特性裁剪**：上游默认特性中的 `webui`（npm/vite 前端，OHOS 无 rolldown 原生 binding）、
  `rendering`（maplibre-native C++ 源码树）、`lambda` 在 OHOS 上不可用，配方固定编译
  服务端特性集 fonts,mbtiles,metrics,passthrough,pmtiles,postgres,sprites,styles,geojson,mlt；
  核心瓦片服务（PostGIS/MBTiles/PMTiles）能力完整保留。
- **平台适配**：OHOS 无 `cc` 链接器，配方通过 `RUSTFLAGS=-C linker=clang` 与
  `.cargo/config.toml` 指定 clang；openssl-sys 依赖制品仓 openssl/3.5.6；
  aws-lc-sys 依赖 OHOS SDK cmake toolchain 识别 aarch64 生成汇编，
  并对 SDK 缺失的 llvm-ranlib 符号链接做了 toolchain 级 workaround。
- **未纳入统计**：需 PostgreSQL/MinIO 外部服务的集成测试（pg_*_test、pmt_minio_test 等）
  依赖外部实例，未纳入本地统计。
