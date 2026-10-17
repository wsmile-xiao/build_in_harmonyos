# DRAFT-emio-0.9.0-lang-preflight-aux-cargo-misdetect

> Contributor: pc1-51 | Status: Draft | Updated: 2026-09-03
> Source: emio 0.9.0 HarmonyOS PC 适配（task emio-0.9.0-r01-pc1-51，lang-preflight 阶段）
> 领域：语言预检（R47 / lang_detect）/ 构建系统识别

## 背景

emio 0.9.0 是 C++20 header-only I/O 库（顶层 manifest 为 CMakeLists.txt，`project(... LANGUAGES CXX)`，
源码统计 cpp 占 98%）。但 `ohc-run.py lang-preflight emio 0.9.0` 判定
`detected_language=mixed（build_system=cargo）`，并自动写入 env_unsupported 终态。

上游仓库 `test/fuzzy/dragon4/rust_ref/` 目录下存在一个 **Rust 参考实现**（Cargo.toml +
src/lib.rs，crate-type cdylib），仅用于 dragon4 浮点格式化的交叉验证，
属于辅助测试工具而非库主体。

## 错误签名

```text
lang-preflight.*detected_language.*mixed|build_system.*cargo|Cargo.toml.*name = "rust_ref"
```

## 根因

`scripts/ohc/lang_detect.py::_manifest_scan` 用**全文件集合**（`names = {p.name for p in files}`，
rglob 递归）检索 Cargo.toml，不限顶层目录；而 CMakeLists.txt 的检查只取 `tops`（顶层）。
因此测试目录内的辅助 Cargo.toml 优先级高于顶层 CMakeLists.txt → manifest=cargo 与
源码统计 cpp 98% 矛盾 → 按 §4.7 冲突规则判 mixed。

R47 边界规则明确"**辅助脚本/工具不算主体**"、C/C++ 按主体判；此处 rust_ref 是
交叉验证辅助实现，不应作为项目 manifest。

## 方案（判定口径）

按 R47 边界规则复核：
1. 顶层 manifest 为 CMakeLists.txt（c/cpp，cmake）；
2. 源码统计 cpp 98%（108/110，唯一 .rs 位于 test/fuzzy/dragon4/rust_ref/）；
3. rust_ref 为辅助验证工具（cdylib，dragon4 交叉验证），不算主体。

结论：任务语言 **cpp 成立**，lang-preflight 的 mixed 判定为框架工具对辅助目录
manifest 的边界误判；继续按 cpp 适配（不构成 env_unsupported）。
本库其余流程（26 个测试 TU 编译运行、Conan 验证）证实 cpp 结论成立。

## 验证

- `-fsyntax-only` + 26 个测试 TU 正常编译运行（141 用例 138 通过）
- 库为 C++20 header-only（include/emio/*.hpp 纯 C++），无任何 Rust 产物入包
- lang-preflight 误判证据已记录于 `.oh-executor/emio-0.9.0-r01-lang-preflight-finding.log`

## 适用边界

- 适用: 测试/示例目录内嵌辅助语言实现（Rust/Python 参考等）的 C/C++ 库；
  lang_detect 全文件 manifest 扫描的边界用例
- 不适用: 真正的混合语言项目（应如实判 mixed / 迁移）
- 相关既有知识: E154（Rust 工具链安装，属另一问题面）

## 查重差异

| 范围 | 结果 |
|---|---|
| 正式知识 doc/ | 未命中（E154 是 Rust 工具链安装，非语言预检误判） |
| 图谱 index.tsv | 未命中 lang_detect/辅助 Cargo.toml 模式 |
| 草稿 drafts/ | 未命中 |
| 配方库 recipes/ | 未命中 |