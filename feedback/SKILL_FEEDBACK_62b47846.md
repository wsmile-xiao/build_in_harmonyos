# SKILL 执行流程反馈报告

> 本报告由 SKILL 自动生成并补全，记录本次编译适配全流程中的失败、效率和改进发现。
> 文件位置: `feedback/SKILL_FEEDBACK_62b47846.md`

---

## 背景

- **软件名称**: stalwart
- **版本**: 1.0.5
- **构建日期**: 2026-08-17
- **构建系统**: Cargo + aws-lc-sys 嵌套 CMake
- **上游仓库**: https://github.com/stalwartlabs/cli/archive/refs/tags/v1.0.5.tar.gz
- **适配路径**: 路径 A + 路径 B 候选（Issue #2237，草稿 E328-draft-912A）
- **补丁数量**: 0
- **编译依赖**: Cargo.lock 固定的 213 个 Rust package；无独立 Conan 运行依赖
- **最终状态**: 本地适配、测试、W3/W4 和 PR 创建完成；PR #5534 的远程 AI 检视已通过，CI 工具链修复后待最终重建

---

## 情况

### 执行概要

本次 SKILL 执行流程涵盖任务查重、W0 工具链探测、Conan 配方实现、真实上游/消费者测试、知识查重、独立审计和 PR 创建。

| 阶段 | 步骤 | 结果 | 说明 |
|------|------|------|------|
| W0/G0 | Rust/OHOS 与 Cargo 闭包探测 | 完成 | Rust target 可用；锁定 213 个 package；定位 aws-lc-sys 原生子构建问题 |
| build | 编译构建 | 成功 | 官方 v1.0.5 源码；OHOS AArch64 ELF；未修改上游源码 |
| conan-verify | 配方验证 | 通过 | G1-G4 与 L1-L5 通过，完整 `conan create` 成功 |
| upstream tests | 上游测试 | 通过并如实降级 | 75/75 单元测试执行通过；13 个集成函数提前返回，按 skipped 统计 |
| test_package | 真实消费者验证 | 通过 | 打包后二进制对 localhost-only mock JMAP API 执行 9/9 断言 |
| finish/W3 | 本地 CI 模拟 | 通过 | `setup.sh` 与 `build_and_test.sh` 均通过，由 finish 门禁生成结果 |
| W4 | 独立审计 | 通过 | 三轮配方审计后 P0=0、P1=0；知识草稿复审完成 |
| submit | PR 提交+AI检视+CI | 进行中 | PR #5534 已关联 Issue #2237；远程 AI 检视通过，CI 工具链修复后待最终重建 |

### 失败与问题

1. 默认 Cargo linker `cc` 不存在，需把 Conan profile 的 OHOS clang 映射到 `aarch64-unknown-linux-ohos`。
2. 未进入完整 OHOS CMake toolchain 时，AWS-LC archive 缺失正确架构汇编对象，最终出现 AES/BN 未定义符号；该签名也可能由 `CMAKE_SYSTEM_PROCESSOR=unknown` 引发，不能作为 ranlib 问题的特异签名。
3. 使用官方 OHOS toolchain 后，SDK 提供 `llvm-ar` 但缺少其固定路径下的 `llvm-ranlib`，导致静态归档索引失败。配方使用 build-local `llvm-ar s` 包装器和 target-specific CMake overlay 修复，未修改 SDK。
4. `AWS_LC_SYS_NO_ASM=1` 被上游限制为 debug 构建，不能用于 release 交付。
5. `finish`/W3 会把正式 `conandata.yml` 临时改写成指向本地预下载缓存的 `file://` URL，门禁通过后必须恢复官方 HTTPS URL，否则 W4 与 CI 不可复现。
6. 首轮 W4 发现 build() 未复现上游测试、消费者测试硬编码 shell、源码 URL 被 W3 改写；第二轮发现 shell 拼接转义和 SDK 路径推断问题；均修复后第三轮通过。
7. `finish` 全流程首次超过外层 300 秒超时且未保留完整阶段输出，后续按标准嵌入方法单独执行 W3。
8. CI Worker 的非交互 PATH 不包含 Rust；后续 #26301 又证明 Worker 的官方安装目录和 `$HOME/.cargo/bin` 也没有完整 cargo/rustc 对。配方不能依赖操作员预装，最终方案先严格检查现有成对工具链，缺失时从 OpenHarmonyPCDeveloper/rust v1.95.0 官方 release 自举到 build folder，并固定 SHA256。

### 知识图谱使用情况

- **引用知识条目**: E012、E267、E296，以及 E327 草稿（用于语义查重）
- **新增知识草稿**: E328-draft-912A（`draft: true`）
- **引擎命中情况**: E012 覆盖“使用 LLVM ar/ranlib”，但不覆盖 SDK 缺少独立 ranlib 且 CMake cache 固化不存在路径的嵌套 Cargo/CMake 场景
- **测试统计**: 上游发现 88，真实执行并通过 75，失败 0，跳过 13；消费者 9/9
- **未覆盖的错误模式**: Cargo `build.rs` 启动的目标 CMake 子构建读取 OHOS toolchain 后，`CMAKE_RANLIB` 指向 SDK 中不存在的 `llvm-ranlib`；需 build-local `llvm-ar s` 包装器和 target-scoped overlay

### AI 检视结果

- **检视阶段到达**: 本地独立配方审计与知识草稿复审完成；远程 AtomGit AI 检视已通过（评论 `185033787`：`✅ 未发现问题`）
- **变更摘要评估**: 本地终审确认配方、测试统计、官方源码、commands.json 和 E328 草稿描述与实际实现一致
- **检视意见数量**: 配方独立审计三轮共发现 1 个 P0、5 个 P1、1 个 P2；知识草稿审阅发现 1 个 P1、2 个 P2、1 个 P3，修复后仅剩验证顺序 P2，再次修复完成
- **检视意见处理**: 全部阻塞意见均修复并重新构建/复审；包括在 build() 执行上游测试、恢复官方 URL、移除硬编码 shell、使用 shlex.quote、优先使用 OHOS_NDK_HOME、修正文档 CMake 变量语义和增强干净构建验证

### CI 结果

- **本地 CI 模拟 (W3)**: 通过
- **远程 CI (PR 校验)**: AI 检视通过；[CI #26289](https://ohpcd.atomgit.com/ci?id=26289)、[CI #26290](https://ohpcd.atomgit.com/ci?id=26290)、[CI #26291](https://ohpcd.atomgit.com/ci?id=26291)、[CI #26301](https://ohpcd.atomgit.com/ci?id=26301)、[CI #26319](https://ohpcd.atomgit.com/ci?id=26319)、[CI #26321](https://ohpcd.atomgit.com/ci?id=26321) 已逐项定位，等待 CA 修复 head 的最终构建
- **CI 失败原因**: #26289/#26319 为 Worker 缺少 `curl`、`libsqlite3.so.0` 或 Python SSL，未进入配方；#26290 为 Worker Python 缺 SSL 模块，源码下载前失败；#26291/#26301 证明 Worker 没有 Cargo/Rustc 1.95.0 OHOS 工具链，已通过官方 release + SHA256 + build-folder 原子自举修复；#26321 已成功完成工具链自举，但 Cargo 访问 crates.io 时因 Worker 系统 CA 路径不可用报 `InvalidCertificate(UnknownIssuer)`。配方现将 Conan Python 运行时已验证的 certifi CA bundle 显式传给 `CARGO_HTTP_CAINFO`，不关闭 TLS 校验

### 效率分析

- **HANDOFF 次数**: 2 次明确可恢复 HANDOFF（feedback 占位符；finish 超时后的门禁状态恢复），另有 W4 多轮阻塞复审
- **重试次数**: 3 次完整 Conan 重建、3 次 W3、3 轮配方 W4、2 轮知识草稿复审
- **关键瓶颈**: Cargo → build.rs → cmake crate → OHOS SDK toolchain 的嵌套配置边界，以及 SDK `llvm-ranlib` 路径缺口；另一个瓶颈是 W3 临时源码 URL 改写污染最终 staged 快照
- **耗时较长的步骤**: 213 个 Rust package 的首次编译与多次干净 `conan create`、AWS-LC C/汇编构建、W3 本地 CI、隔离审计与知识查重

---

## 建议

### SKILL 设计改进

`finish` 应在超时时持久化当前子步骤、子命令和日志路径，并提供只恢复未完成步骤的命令。W3 临时替换源码 URL 时应使用临时 recipe 副本或 finally 自动恢复，禁止把 `file://` 缓存地址留在工作树中。

### 模板改进

Rust/Cargo 应用模板应包含：`Cargo.lock` 强制 `--locked`、显式 `CARGO_TARGET_DIR`、目标 linker/AR 映射、build.rs 原生子构建检查，以及“Cargo 显示 ok 但测试提前返回时按 skipped 统计”的字段。PR 模板应将“发现/执行/通过/跳过”分列，避免把 75/75 误读成 88 项全部执行。

### 自动化补全

W3/W4 前后可自动断言 `conandata.yml` 仍是官方 HTTPS URL；对 Cargo crate 可自动扫描 Cargo.lock 中的 `*-sys`、`cmake` 和 `cc` package，提示检查嵌套 toolchain cache。可增加 SDK 完整性探针，验证 toolchain 中记录的 clang/ar/ranlib 路径是否都真实存在。

### 知识图谱覆盖

新增 E328 草稿：当 Cargo 原生 CMake 子构建使用 OHOS toolchain，而 SDK 缺少其固定路径下的 `llvm-ranlib` 时，用 build-local `llvm-ar s` 包装器和 target-scoped overlay 补全 archive-index 闭包。该条目与 E012/E267/E296/E327 已完成语义查重，保持 `draft: true` 等待人工审核。

---

## 作者

- **姓名**: wingsluo
- **邮箱**: wingsluo@noreply.gitcode.com
- **Agent ID**: 0B41
- **生成时间**: 2026-08-17 04:15:16
- **PR 编号**: 5534
- **Git Commit**: 44f33aff77
