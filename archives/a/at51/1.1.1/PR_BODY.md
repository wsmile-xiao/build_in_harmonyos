- **三方库名称**：at51
- **上游版本**：1.1.1（tag：1.1.1）
- **上游仓库地址**：https://github.com/8051Enthusiast/at51
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（编译SKILL）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 38 | 来源：上游 Rust `#[test]`，分布于 `src/kinit.rs`、`src/libfind/aslink3.rs`、`src/libfind/mod.rs`、`src/libfind/omf51.rs` |
| 集成测试 | 0 | 上游未提供独立 `tests/` 集成测试目录 |
| 其他测试 | 0 | 无 doctest/ignore 用例纳入本次统计 |
| **合计** | **38** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 38 | 不变 | 全部在 OHOS aarch64 真机通过 `cargo test --release --locked --no-fail-fast --bins --tests` 实际运行 |
| 集成测试 | 0 | 不变 | 上游未提供独立集成测试 |
| 鸿蒙特有测试 | 5 | 新增 | test_package 执行 `at51 --help` 以及 `stat/base/kinit/libfind --help` |
| **合计** | **43** | **+5** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游 at51 1.1.1 自带 38 个 Rust 单元测试，本次全部在 OHOS aarch64 真机实际运行通过。
> 适配侧新增 5 条 test_package CLI 冒烟验证，用于确认 Conan 制品中的 `at51` 可执行文件和四个子命令帮助输出可正常运行。

## 验证结果

- 编译状态：通过（`cargo build --release --locked` 成功，产出 `at51` 二进制）
- 上游测试用例通过率：38/38（100.00%）
- 新增测试用例通过率：5/5（100.00%）

## 补充说明

- **真机 CI 结果**：旧端口 56267 上通过 `conan create`，run 目录为 `/storage/Users/currentUser/ohos-test-runs/codex-a-1.1.1-at51-1.1.1-oldport-r1-20260814-conan-20260815-222107-41019`。
- **CI 门禁**：L0/L1/L2/L4/L5 全部通过，L1e 负向破坏测试确认 test_package 真实依赖包内 `at51` 二进制。
- **平台适配**：旧端口环境无 curl/Harmonybrew/Rust，配方通过 Python urllib 下载 Harmonybrew Rust/OpenSSL/zlib bottle，在构建目录内引导 Rust 工具链；Cargo linker 解析到可执行 `clang-15` 并显式传入 OHOS sysroot、code-sign 和 linker 参数。
- **源码变更**：未修改上游源码，无补丁。
