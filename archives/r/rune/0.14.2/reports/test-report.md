# rune 0.14.2 测试报告

**测试日期**：2026-08-19
**测试环境**：OpenHarmony PC aarch64、Rust 1.95.0、clang 15.0.4
**上游版本**：Rune 0.14.2

## Conan 验证

| 项 | 内容 |
|----|------|
| 命令 | `python3 scripts/ohc-run.py conan-verify rune 0.14.2` |
| 结果 | G0-G4、L2、L4、L5 全部通过 |
| W3 本地 CI | `setup.sh` 与 `build_and_test.sh rune/0.14.2` 均通过 |
| 构建产物 | `bin/rune` |

## 上游测试

| 项 | 内容 |
|----|------|
| 命令 | `cargo test --release -p rune --lib` |
| 测试范围 | parser、compiler、runtime、macros、VM 等核心库单元测试 |
| 结果 | 293 通过、0 失败、1 忽略 |
| 通过率 | 293/293（100%，不计上游明确忽略项） |

## 消费者测试

| # | 用例 | 结果 |
|---|------|------|
| 1 | 执行 `rune --version` 并检查解释器标识 | 通过 |
| 2 | 执行 `rune --help` 并检查 Usage 输出 | 通过 |
| 3 | 对合法 Rune 脚本执行 `rune check` | 通过 |
| 4 | 执行合法 Rune 脚本 | 通过 |
| 5 | 确认 `rune check` 拒绝语法错误脚本 | 通过 |

## 汇总

| 指标 | 结果 |
|------|------|
| 上游测试 | 293/293 通过，1 项上游忽略 |
| 新增消费者测试 | 5/5 通过 |
| 编译状态 | 通过 |
| 源码测试修改 | 无 |
| 上游源码补丁 | 无 |

## 已知限制

- 上游 CLI 的 `--version` 输出仅包含解释器名称和 Git 占位信息，不包含 `0.14.2`，因此消费者测试不对语义版本字符串作错误假设。
- 通用 G0 configure 探测不识别 Cargo 项目；Conan G2 干净构建和 W3 本地 CI 已完整验证 Cargo 构建链路。
