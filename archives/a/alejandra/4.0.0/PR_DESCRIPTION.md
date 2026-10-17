- **三方库名称**：alejandra
- **上游版本**：4.0.0
- **上游仓库地址**：https://github.com/kamadorueda/alejandra
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| Formatter golden case | 43 | `fmt.rs` 遍历 43 个 fixture 目录 |
| CLI 快照 case | 33 | `cli.rs` 遍历 33 组参数/stdin |
| **合计** | **76** | 按 harness 内实际 case 计数 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------:|-----------:|------|
| 上游 formatter case | 43 | 不变 | 43/43 通过 |
| 上游 CLI case | 33 | 不变 | 33/33 通过 |
| 鸿蒙特有消费者断言 | 3 | +3 | 版本、格式化输出和 `--check` |
| **合计** | **79** | **+3** | 上游 case 无删除、无弱化 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在测试运行兼容性修改

修改 `src/alejandra_cli/tests/cli.rs` 的执行适配：

1. 使用 Cargo 提供的 `CARGO_BIN_EXE_alejandra` 直接运行已构建 CLI，避免每个 case 嵌套执行 `cargo run`；
2. 仅过滤 OHOS 运行时在应用 stderr 前注入的 `[OhOS Auto-Sign]` 诊断及伴随空行；
3. 33 组输入、预期 `output.txt` 快照、退出码及业务 stdout/stderr 断言均保持不变。

## 补全测试用例说明

- **补全范围**：为 Conan 包中的 `alejandra` 可执行文件新增 3 个消费者行为断言。
- **新增文件**：`test_package/test.sh`。

## 验证结果

- 编译状态：通过（OHOS arm64 release 构建）
- 上游测试用例通过率：**76/76（100%）**
- 新增测试用例通过率：**3/3（100%）**
- 产物：ELF64 AArch64 PIE `bin/alejandra`

## 补充说明

- 使用 `aarch64-unknown-linux-ohos` 原生 Rust 工具链和上游 `Cargo.lock` 构建。
- 无额外 Conan 运行时依赖。
- 适配补丁仅处理测试执行时的平台诊断，不修改 Alejandra 产品逻辑。
