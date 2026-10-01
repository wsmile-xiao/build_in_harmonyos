# rhai 1.25.0 测试报告

**测试日期**：2026-10-01
**测试环境**：OpenHarmony PC aarch64、Rust 1.97.1（rust-toolchain/1.97.1）、OHOS SDK clang 15
**上游版本**：rhai 1.25.0（tag v1.25.0 = 8498f86907d238000b67a5fb3348250fd252b314）

## 上游测试

| 项 | 内容 |
|----|------|
| 命令 | `cargo test --release --tests --features testing-environ,decimal,serde,metadata,internals,debugging --target aarch64-unknown-linux-ohos` |
| 范围 | tests/ 58 个集成测试文件（语言语义/解析/优化器/serde/modules/…）+ src/lib.rs 单元测试 |
| 结果 | **281 通过、0 失败、0 忽略**（61 个 test binary） |
| 通过率 | 281/281 = 100% |
| 日志 | `.plan/rhai_build/upstream_tests.log` |

按套件明细（全部 0 failed）：

| 套件 | passed | 套件 | passed | 套件 | passed |
|---|---|---|---|---|---|
| src/lib | 1 | arrays | 9 | assignments | 2 |
| binary_ops | 2 | bit_fields | 3 | blobs | 3 |
| bool_op | 6 | build_type | 4 | call_fn | 7 |
| chars | 1 | closures | 7 | comments | 2 |
| compound_equality | 8 | constants | 3 | custom_syntax | 8 |
| data_size | 3 | debugging | 2 | decrement | 1 |
| eval | 5 | expressions | 2 | float | 6 |
| fn_ptr | 6 | for | 6 | functions | 22 |
| get_set | 7 | if_block | 2 | increment | 1 |
| looping | 2 | maps | 9 | math | 2 |
| method_call | 8 | mismatched_op | 3 | modules | 13 |
| native | 3 | not | 1 | number_literals | 4 |
| operations | 5 | ops | 5 | optimizer | 8 |
| options | 2 | packages | 2 | parse_json | 2 |
| plugins | 3 | power_of | 2 | print | 3 |
| serde | 26 | side_effects | 2 | stack | 3 |
| string | 10 | switch | 8 | throw | 2 |
| time | 2 | tokens | 4 | types | 1 |
| unary_after_binary | 1 | unary_minus | 1 | unit | 3 |
| var_scope | 9 | while_loop | 3 | | |

补充组合：`testing-environ,unicode-xid-ident,decimal,serde,metadata,internals,debugging` → 281 通过 / 0 失败。

## 消费者测试（test_package/test_rhai.py）

| # | 用例 | 结果 |
|---|------|------|
| A0 | rhai-run 存在 | 通过 |
| A1 | rhai-dbg 存在 | 通过 |
| A2 | 脚本执行退出码 0 | 通过 |
| A3 | 输出含 `sum=45`（循环累加） | 通过 |
| A4 | 输出含 `42`（算术） | 通过 |
| A5 | 语法错误脚本报 `Syntax error` 诊断 | 通过 |
| A6 | 缺失脚本文件返回非零退出码 | 通过 |
| B1 | 鸿蒙特有：ELF machine = AArch64(183) | 通过 |
| B2 | 鸿蒙特有：PT_INTERP = `/lib/ld-musl-aarch64.so.1` | 通过 |
| B3 | 鸿蒙特有：含 OHOS code signature | 通过 |
| B4 | 鸿蒙特有：产物非空且可执行 | 通过 |

**11/11 通过**（消费者功能 7 + 鸿蒙特有 4）

## 汇总

| 指标 | 结果 |
|------|------|
| 上游测试 | 281/281 通过（0 失败 / 0 忽略） |
| 消费者测试 | 7/7 通过 |
| 鸿蒙特有测试 | 4/4 通过（≥1 满足） |
| 构建产物 | `bin/rhai-run`、`bin/rhai-dbg` |
