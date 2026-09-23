# alevin-fry

单细胞/单核 RNA-seq 与 ATAC-seq 数据的快速、准确、内存友好处理工具集，
属于 kallisto|bustools 生态（`kallisto bus` 产出 RAD 文件后，由本工具完成
barcode 校正、collate、quant、infer 等下游步骤）。纯 Rust 实现。

- 上游: https://github.com/COMBINE-lab/alevin-fry
- 许可证: BSD-3-Clause
- 构建系统: cargo (Rust workspace，edition 2024)

## 功能概述

- `convert` — BAM → RAD 格式转换
- `view` — 查看 RAD 文件
- `generate-permit-list` — 由 RAD 文件生成 barcode 许可列表
- `collate` — 按校正后 cell barcode 聚合 RAD 记录
- `quant` — cos 定量表达（支持 `cr-like` / `parsimony-em` 等策略）
- `infer` — 在 equivalence-class 计数矩阵上做推断
- `atac` — scATAC-seq RAD 处理（sort / collate / deduplicate）

## OHOS 适配

- 纯 Rust / Cargo 项目，无 C/C++ 库依赖，依赖图由 `Cargo.lock` 锁定。
- **crates.io 索引限速**：OHOS CI worker 访问 static.crates.io 被限速，
  配方在 build-folder `.cargo/config.toml` 中配置 `rsproxy-sparse` 镜像。
- **libdeflate AVX-VNNI**：libdeflate-sys 需 `-DLIBDEFLATE_ASSEMBLER_DOES_NOT_SUPPORT_AVX_VNNI`
  CFLAGS，否则旧版 assembler 无法解析生成的汇编。
- **OHOS `/tmp` 只读**：构建需设置可写 `TMPDIR` 与任务独立 `CARGO_HOME`
  （并行预检锁冲突）。
- **环境限制**：Rust 工具链 (cargo/rustc) 在 hmbs 预检沙箱不可用，上游测试无法执行。按 signal-tlsd/acme-redirect 先例标记为 env_unsupported。

## 依赖关系

- 编译依赖：cargo/rustc（Rust 工具链）+ clang（链接器）
- 运行依赖：无（二进制自带全部 Rust 静态依赖）

## 参考资料

- 源码: https://github.com/COMBINE-lab/alevin-fry
- 文档: https://alevin-fry.readthedocs.io/en/latest/

## Adapted versions

| Version | Status |
|---------|--------|
| 0.16.2  | built  |