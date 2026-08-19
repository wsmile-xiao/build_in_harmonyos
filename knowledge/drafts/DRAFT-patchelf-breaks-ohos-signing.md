# DRAFT-patchelf-breaks-ohos-signing：patchelf 改 ELF 破坏 OHOS 代码签名 → 禁止用于测试二进制

> Contributor: librsvg-2.62.3 适配 | Status: Draft | Updated: 2026-08-14
> Source: archives/l/librsvg/2.62.3（round-8 CI，patchelf 破坏签名，交付 commit 0ca0b722ea）

## 现象

OHOS 对 ELF 有代码签名要求（构建期自动签名、`.codesign` 段）。当尝试用 patchelf
修改已签名测试二进制的 RUNPATH/rpath（如 `patchelf --add-rpath <libdir> <binary>`）
以解决运行时 .so 可达问题时，会破坏既有签名，重签失败（`binary-sign-tool` 报
`WriteCodeSignBlock error`），二进制不可用。

## 与现有知识的关系

- knowledge/graph 共 323 条，grep `patchelf` / `代码签名` / `WriteCodeSignBlock` /
  `RUNPATH` 于 knowledge/docs/references 均无结果——本主题无覆盖。
- **既有 E186 的边界细化/修正**：E186 `rec_approach: patchelf-fix-runpath`
  （cargo 本体 + 重签成功）；本轮 round-8 实证 patchelf 对**已签名测试二进制**改
  RUNPATH 破坏 OHOS 代码签名、重签失败（`WriteCodeSignBlock error`）→ 测试二进制
  运行时可达**禁用 patchelf**、改用运行期注入。这是"禁止模式"级知识。
- 既有 DRAFT-upstream-test-runtime-libs 提供运行期注入的替代方案，本草稿为其
  "禁止 patchelf"边界的补充，建议互链。
- 本草稿为"一类问题"（跨库可复用）：任意在 OHOS 上尝试用 patchelf 修改已签名
  二进制 RUNPATH/rpath 的 Conan 适配都可能命中。

## 方案

测试二进制改用运行期注入（`LD_LIBRARY_PATH` 或 `RUSTFLAGS` rpath，见
DRAFT-upstream-test-runtime-libs），不使用 patchelf。确需改 ELF（如 E186 的 cargo
工具链本体场景）必须 `--remove-section .codesign` 后重签，且仅限可重签的工程内
二进制。

## 验证证据

librsvg 2.62.3 在 HarmonyOS aarch64 真机单包 CI：

- round-8 FAIL：尝试用 patchelf 改测试二进制 RUNPATH 以解决 pixman 缺口，破坏 OHOS
  代码签名（`WriteCodeSignBlock error`），重签失败，二进制不可用。
- round-9 PASS：改用运行期注入策略（C API 测试用 `LD_LIBRARY_PATH`、Rust 测试用
  `RUSTFLAGS rpath`，见 DRAFT-upstream-test-runtime-libs），不再用 patchelf；CI exit 0，
  上游 3 套件真实运行（C API tests OK 8.03s、Rust tests (librsvg) OK 502.37s、
  Rust tests (rsvg) OK 1086.16s）。

## 禁止做法

- 不要对已签名测试/制品二进制直接 `patchelf --add-rpath/--set-rpath` 后不重签——
  会破坏 OHOS 代码签名（`.codesign` 段），重签失败（`WriteCodeSignBlock error`），
  二进制不可用。
- 不要把 patchelf 作为测试二进制运行时 .so 可达的首选方案——OHOS 代码签名要求
  使得 patchelf 路径不可行，须用运行期注入。
