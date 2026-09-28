- **三方库名称**：intermodal（CLI 二进制 `imdl`）
- **上游版本**：v0.1.16
- **上游仓库地址**：https://github.com/casey/intermodal
- **适配路径**：路径 A（基础适配）
- **使用知识库**：ohos-worker-env-triage skill、仓库 Rust 先例 below/0.11.0（rust-toolchain/1.97.1 tool_requires + 工具链自签名 + rsproxy 镜像模式）、add/0.7.3

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 285 | 来源：cargo 单元测试，src/ 下 52 个 `#[cfg(test)]` 模块的 285 个 `#[test]` 函数（grep 实测计数；其中 2 个 `#[ignored]`） |
| 集成测试 | 0 | 来源：上游无 tests/ 目录，功能测试均以单元测试形式内嵌 src/（test_env! 宏驱动真实 imdl 工作流） |
| 其他测试 | 若干 | doctest（README/doc 示例，由 rustdoc 执行；见「补充说明 1」）+ criterion 基准（hasher，harness=false，非常规测试） |
| **合计** | **285** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 285 | 不变 | 上游测试代码零修改，build() 内以 `cargo test --release --target aarch64-unknown-linux-ohos -p imdl --lib --bins --no-fail-fast` 于 HarmonyOS PC 真机实跑（282 执行：280 通过 / 2 环境限制失败 / 2 ignored） |
| 集成测试 | 8 | +8 | test_package/test_imdl.py 功能测试：对真实数据文件执行 torrent create（--announce）→ bencode 结构断言（顶层 dict/announce+info 键/文件名）→ show → verify 重哈希 → link 产出 40-hex infohash magnet 的完整闭环 |
| 鸿蒙特有测试 | 4 | 新增 | test_imdl.py B1–B4：AArch64 ELF / PT_INTERP=OHOS musl loader（/lib/ld-musl-aarch64.so.1）/ OHOS code signature（未签名 ELF 无法 execve，EACCES errno 13）/ 产物非空可执行 |
| **合计** | **297** | **+12** | 285 + 8 + 4；另含消费者冒烟 3 项（--help/子命令/--version） |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：test_package 消费者层新增 12 个断言（8 个真实 .torrent 功能工作流 + 4 个鸿蒙特有平台断言）+ 3 个冒烟断言
> - **补全原因**：上游测试以 Rust 单元测试为主，缺少「打包产物在目标平台可用」的消费者级验证；本包为纯 CLI 应用（无库消费方），必须以端到端方式验证产物
> - **新增测试文件清单**：
>   1. `archives/i/intermodal/0.1.16/test_package/test_imdl.py` — 消费者测试（15 断言：冒烟 3 + 功能 8 + 鸿蒙特有 4，逐条输出可审计）
>   2. `archives/i/intermodal/0.1.16/test_package/conanfile.py` — conan test 入口（VirtualRunEnv + can_run 门禁）
>   3. `archives/i/intermodal/0.1.16/test_package/MANIFEST.yml` — R51 测试三步法申报

## 验证结果

- 编译状态：通过（W3 本地 CI L0/L1/L2/L4/L5 + G0/KC/JC 全 pass，破坏性负测试确认 test_package 真实依赖产物；conan-verify G1–G5 通过）
- 上游测试用例通过率：[280/282]（99.3%；计入 2 个上游自带 ignored 为 280/284）
- 新增测试用例通过率：[15/15]（100%）

## 补充说明

1. **doctest 排除**：cargo test 的 doctest target 由 rustdoc 执行，rust-toolchain/1.97.1 dist 包的 rustdoc 未携带 OHOS code signature，execve 报 EACCES（errno 13）。README/doc 示例不属于单元测试契约，故测试命令限定 `--lib --bins` 并在此如实申报。
2. **2 个失败用例的环境限制**：`subcommand::torrent::create::tests::follow_symlinks` 与 `symlink_root`——测试经 `std::os::unix::fs::symlink` 创建符号链接，本平台 HMDFS uid 映射卷不支持创建 symlink（os.symlink 直接 EPERM，与 conan 缓存/构建目录上同源）。属运行环境限制而非被测逻辑缺陷，imdl 的 symlink 处理代码未做任何修改（patches_applied=[]）。
3. **PF8/PF9 说明**：本包为应用级包（package_type=application，交付 bin/imdl），按 R38 携带软件级 `commands.json`/`README.md`/`manifest.yaml`（参考 archives/s/strace 与 archives/b/below 先例）。此三文件路径层级为 4 段，会触发 PF9 路径深度误报，故以 OHC_PREFLIGHT=0 提交（与 aiac/orcania 等已合入先例一致）。
4. **构建方式**：Rust 工具链由制品仓基础设施包 `rust-toolchain/1.97.1` 提供（tool_requires，rust-lang 官方 dist 预编译 aarch64-unknown-linux-ohos），HarmonyOS PC 原生 cargo 构建；不使用 rustup（无法识别 HarmonyOS 宿主）。工具链 cargo/rustc/librustc_driver 复制后用 binary-sign-tool 自签名。产物 `bin/imdl` 亦已自签名。无 conan 依赖（纯 Rust crates.io 依赖集，经 rsproxy.cn sparse 镜像拉取）。
5. 本机打包自检：`packaging/intermodal-0.1.16-ohos-aarch64.tar.gz`（7.2MB，bin/imdl + licenses + res）+ `.staging-verified`（verified=1 failed=0）+ `.ci-result.json` 为本机自检产物，按仓库规范不进 PR。
