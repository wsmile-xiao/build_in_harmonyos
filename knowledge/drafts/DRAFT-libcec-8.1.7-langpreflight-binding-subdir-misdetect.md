# lang-preflight 绑定子目录误判：含 Rust 绑定的 C++ 库应判 cpp

> **适用范围**：主语言为 C/C++、但源码树含 Rust/.NET/Node/Python **绑定子目录**的三方库
> （如 `src/rust/`、`src/nodejs/`、pybind11 包装 C++）。典型对象：libcec 8.x、pybind11 系、
> 含多语言绑定的 C/C++ 库。
>
> **反例**：根目录就是 `Cargo.toml` 的纯 Rust 项目 → 仍判 rust，不适用本条目。

## 问题

`ohc-run.py lang-preflight`（R47 语言预检）对 libcec 8.1.7 输出：

```json
{ "detected_language": "rust", "error_type": "env_unsupported",
  "language_evidence": { "build_system": "cargo", "manifest": "Cargo.toml name = \"libcec\"",
    "source_stats": "源文件 88 个（cpp:53, python:16, rust:14, bash:6），主体占比 60%" } }
```

但 libcec 8.1.7 **主体是 C++**：根目录是 `CMakeLists.txt`（CMake 构建），52 个 `.cpp` + 1 个 `.c`，
`src/rust/` 只是一个可选的 Rust FFI **绑定**子目录（README 明示 "Rust binding for libCEC"，
经公开 C API `include/cecc.h` 绑定 C++ 引擎；`ENABLE_RUST_LIB` 默认 OFF，不进入原生构建图）。

## 根因

`lang_detect._manifest_scan` 用全树文件集合判断 manifest：

```python
names = {p.name for p in files}        # rglob 递归收集所有文件名
if "Cargo.toml" in names:              # 树内任意子目录命中即判 rust
    return ("rust", "cargo", ...)
```

没有把 manifest 判断**限定在源码根目录**。任何子目录（绑定 crate）里的 `Cargo.toml`
都会命中 rust → 自动写 `env_unsupported` 终态。按协议 §4.7 与 R47 边界规则
（"绑定类包（pybind11 包装 C++）→ 判 cpp"、"辅助脚本不算主体"），这是误判。

## 判定方法（按 R47 边界规则人工复核）

1. **根构建系统为权威**：根目录存在 `CMakeLists.txt`/`configure`/`Makefile` → 按根构建系统
   的语言族判定（CMake+大量 .cpp → cpp），绑定子目录的 manifest 不参与主体判定；
2. **源码统计以主体为准**：cpp（含 c 家族）占比为主时判 cpp，与 pybind11 规则一致；
3. **c↔cpp 兼容族不迁移**：判定 cpp 后正常走 conan/CMake 流程；
4. 若工具已写 `env_unsupported` 终态 result.json，以真实结果 `--force` 覆盖。

## 验证（libcec 8.1.7，OHOS aarch64）

按 cpp 判定后全流程通过：init-build → CMake 构建（libcec.so + cec-client/cecc-client）→
conan-init → conan-verify（G0-G4/L2/L4/L5 全 pass）→ finish W3 本地 CI
（L0-L5 pass，`.ci-result.json` exit_code=0）。消费者测试与鸿蒙专项测试均 PASS，
证明主体语言判定正确。

## 边界与反例

- 仅适用"**绑定子目录**"场景；纯 Rust 项目（根 Cargo.toml）仍判 rust；
- 多语言绑定（rust+dotnet+nodejs）共存时同样以主体 C/C++ 为准；
- 工具侧修复方向：`_manifest_scan` 应只扫 `tops`（根目录）而非 `names`（全树）——
  本条目记录人工判定规则，供工具修复前的所有 executor 复用。

## 关联

- similar_to：E105 / E154（Rust 工具链缺失域，触发器不同）
- 相关规则：R47、协议 v0.8 附录 D §4.7
