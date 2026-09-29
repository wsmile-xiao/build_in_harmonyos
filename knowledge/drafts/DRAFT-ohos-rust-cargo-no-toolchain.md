# OHOS 无 Rust 工具链，Rust/cargo 项目不可适配（illuminanced 选型先例）

- **草稿 ID**: DRAFT-ohos-rust-cargo-no-toolchain
- **来源**: illumina（illuminanced 1.0.2，mikhail-m1/illuminanced）适配评估；AdGuardHome（Go）同型先例
- **分类**: toolchain / rust / ohos / selection
- **状态**: 本地草稿（按用户要求不推送代码）

## 问题 / 判定依据

- **上游**：mikhail-m1/illuminanced，tag 1.0.2 存在（NixOS/Arch 均有打包记录），GPL-3.0
- **语言/构建**：纯 Rust（Cargo.toml：edition 2021，依赖 daemonize/syslog/log/simplelog/getopts/toml/glob/libc），cargo build
- **OHOS 工具链**：沙箱 `which rustc cargo` 无结果；`/data/service/hnp/bin` 无 rust/cargo；conan cache 无 rust 工具链包；**无 linux-ohos 官方 Rust 目标 triple**（与 Go 相同）
- **hmmac 沙箱**：封锁"下载来的预构建静态 ELF"执行（execve errno=13，官方 Go 工具链先例）——即使有预构建 Rust 工具链也无法执行

## 结论

**选型阶段即判不可适配**：Rust/cargo 项目在 OHOS 无任何可编译路径，不必创建纯净分支/四件套/消费者用例（无法本地与 CI 构建验证，推送必失败）。

## 处理流程（路径 B：知识库贡献）

1. 查重：knowledge/index.tsv + graph/ + drafts/ 无 illumina/rust-toolchain 条目（无撞车）
2. 编写本 DRAFT（.kv 按 _template.kv 全字段；.md 含差异化定位表）
3. 申报 PR：标题【知识库扩展】+ B 类章节，说明 illumina 评估结论（Rust 无工具链不可适配）

## 与既有条目的差异化定位

| 条目 | 覆盖范围 | 本条目差异 |
|------|----------|-----------|
| adguardhome 先例（全局记忆/历史记录） | Go 项目无 OHOS 工具链 | 本条目将**语言维度判定规则**固化（Rust 同型），供选型脚本/后续评估复用 |
| E057/E074（MAKEFLAGS/工具链注入） | 有工具链时的构建注入 | 本条目覆盖**无工具链**的选型否决场景，前置步骤不同 |

## 验证

- 选型检查命令：`which rustc cargo`、`ls /data/service/hnp/bin | grep -iE 'rust|cargo'`、上游仓库根含 `Cargo.toml`
