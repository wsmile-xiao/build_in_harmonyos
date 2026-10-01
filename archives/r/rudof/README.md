# rudof

## 简介

rudof 是一个用于 **RDF 数据形状与知识图谱**处理的 Rust 工具箱，提供命令行工具 `rudof`。它围绕多种数据形状/图模式语言实现校验、转换、查询与生成，支持：

- **ShEx**（Shape Expressions）：ShEx 模式解析、ShExMap、ShEx 校验（`shex` / `shex-validate` / `shapemap`）
- **SHACL**（Shapes Constraint Language）：SHACL 形状查看与数据校验（`shacl` / `shacl-validate`）
- **SPARQL**：SPARQL 查询与服务信息（`query` / `service`）
- **DCTAP**：Dublin Core Tabular Application Profiles（`dctap`）
- **PGSchema**：属性图模式（`pgschema` / `pgschema-validate`）
- **RDF 数据操作**：数据信息（`data`）、节点信息（`node`）、格式转换（`convert`）、形状比较（`compare`）
- **合成数据生成**：从 ShEx/SHACL 形状生成 RDF 数据（`generate`）、物化（`materialize`）
- **MCP server**：以 MCP 方式导出（`mcp`）

CLI 由 workspace 成员 crate **`rudof_cli`** 提供（二进制名 `rudof`）。

## 功能概述

- RDF（Turtle / N-Triples / RDF/XML / JSON-LD / TriG / N-Quads 等）与 Property Graph 的加载与序列化
- 多后端：内存图（默认）、远端 SPARQL endpoint（`endpoint=`）、QLever（可选 `qlever` feature）
- 形状校验：ShEx 与 SHACL 两类数据形状语言的校验能力
- 命令行完备的补全脚本生成（`completion`）

## OHOS 适配

### 适配要点

- **构建系统**: Cargo（Rust，workspace `edition 2024`）；仅发布 CLI crate `rudof_cli`
- **编译命令**: `cargo build --release --locked --target aarch64-unknown-linux-ohos --bin rudof`
- **工具链**: 设备无 cargo/rustc，经 `tool_requires rust-toolchain/1.97.1` 提供
  （宿主与目标均为 aarch64-unknown-linux-ohos）
- **工具链自签名**: rust-lang dist 二进制无 code signature，OHOS 拒绝 execve（EACCES/E318）；
  配方内用 `binary-sign-tool -selfSign 1` 自签名 cargo/rustc/librustc_driver
- **运行库**: cargo 动态链接 OpenSSL/zlib，OHOS loader 忽略 DT_RUNPATH 且系统 OpenSSL 3.0
  版本过低，使用 harmonybrew openssl@3 / zlib-ng-compat bottle 并显式设置 LD_LIBRARY_PATH
- **镜像与 CA**: crates 索引走 rsproxy.cn sparse 镜像；设备无默认 CA store，显式指定
  `SSL_CERT_FILE` / `CURL_CA_BUNDLE`
- **TMPDIR**: OHOS /tmp 只读，构建使用可写 TMPDIR
- **源码口径**: 采用 crates.io `rudof_cli` 归档（内含发布时一致的 Cargo.lock，`--locked` 可复现）

### 上游测试

- `cargo test --release --locked --target aarch64-unknown-linux-ohos --tests`
- `rudof_cli` crate 11 个单元测试（全部位于 `src/cli/wrappers/backend.rs`），
  真机运行 **11 passed / 0 failed / 0 ignored**

### 已知问题

- 本机 agent 环境禁止 python 进程创建符号链接，配方 `_link_or_copy()` 会回退为复制；
  CI（Linux）不受影响。
- 上游 workspace 级测试需 git 子模块（`shexTest` / `data-shapes`）与 Docker（`qlever`），
  不在本包测试范围。
