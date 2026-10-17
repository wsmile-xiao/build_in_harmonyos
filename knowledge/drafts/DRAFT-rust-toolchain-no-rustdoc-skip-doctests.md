# DRAFT-rust-toolchain-no-rustdoc-skip-doctests

## 症状

rust-toolchain conan 包构建的 Cargo 项目，在 conan create 的 build() 内执行裸
`cargo test` 时：单元/集成目标全部正常结束（哪怕 `running 0 tests`），随后在
Doc-tests 阶段失败：

```
Doc-tests comet
error: doctest failed, to rerun pass `--doc`

Caused by:
  could not execute process `rustdoc --edition=2021 ...` (never executed)

Caused by:
  No such file or directory (os error 2)
```

conan 层面表现为 `ConanException: Error 101 while executing`，conan create 失败
（实例：comet/0.3.2 适配权威 CI 首轮，2026-09-11；修复后同 run 复测全 gate PASS）。

## 根因

- rust-toolchain/1.97.1 发行包 bin/ 实测仅 cargo/rustc/rustfmt/clippy-driver 等
  10 个二进制，**不含 rustdoc**（rust-lang 官方 dist tarball 不携带 rustdoc 组件；
  cbindgen/0.28.0 notes 行 48 亦有在先记录"工具链未包含 rustdoc"）。
- cargo test 在**未限定测试目标**时，默认目标集包含 Doc-tests；doctest 由 rustdoc
  进程执行。工具链没有 rustdoc → spawn ENOENT → cargo test 整体失败。
- 与包是否真的有 doctest 无关：只要进入 Doc-tests 目标就会调用 rustdoc。

## 修复

测试命令显式限定目标集，绕开 doctest：

```python
self.run(cargo + " test --locked --release --lib --bins", ...)
```

- 存在集成测试时按需追加 `--tests`；
- **如实标注**：跳过 doctest 是工具链能力缺失下的既知取舍，须在
  test_package/MANIFEST.yml 与 notes.md 中注明"doctest 未执行（工具链无
  rustdoc）"，不得伪称全量测试。

## 适用范围

- 一切以 rust-toolchain conan 包为 tool_requires 的 Rust 配方（应用与库）；
- 与包规模、测试数量无关（0 doctests 同样失败）。

## 反例/边界

- 非本机理的 cargo test 失败：编译错误、断言失败有各自的报错面（不在
  Doc-tests 阶段、无 rustdoc ENOENT）；
- 设备/CI worker 若安装了带 rustdoc 的工具链（如未来发行包补齐组件），本条
  规避不再必要，但显式目标限定仍是无害的良好实践。

## 触发实例

- comet/0.3.2（2026-09-11）：裸 cargo test 实败 → `--lib --bins` 后 CI 全绿；
- cbindgen/0.28.0：案例级在先记录（notes 行 48），配方自始使用目标限定。

## 相关

- E105 / E154 / E180 / E358：Rust on OHOS 工具链族（平台支持、工具链可用性、
  OHOS target、锁图迁移）；本条是"工具链组成能力"面的补充。
