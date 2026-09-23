# lang-preflight 全树 manifest 扫描将辅助差分门禁误判为主语言——按 R47 D.4 边界规则以主库主体判定

- **草稿 ID**: DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest
- **来源**: exr_image 0.1.0-rc3 HarmonyOS PC 适配（C89 单头文件 OpenEXR 库，tests/exrs_reference 为可选 Rust 差分门禁，lang-preflight 误判 mixed(cargo)）
- **分类**: preflight / build-system / manifest / language-detection / R47
- **状态**: 本地草稿（挂路径 B 知识库扩展 PR，与 exr_image 归档同 PR 交付）

## 问题 / 错误签名

- **错误输出**：`ohc-run.py lang-preflight exr_image 0.1.0-rc3 --src <src>` 判定 `detected_language: mixed`，build_system=cargo，manifest=`Cargo.toml name = "exri_exrs_reference"`，自动写终态 `env_unsupported`（draft:false）。
- **复现**：任何源码树 `tests/` 等子目录含辅助工具 manifest（Cargo.toml/pyproject.toml/go.mod）的 C/C++ 库，lang-preflight 的 `_manifest_scan` 对 `Cargo.toml` 使用全树文件名集合（`names = {p.name for p in files}`，rglob 全部文件，未限定顶层），与源码统计（c 占 79%）冲突 → `mixed`。
- **对照验证**：主库为 C89 单头文件库（exr_image.h 14894 行，README："standalone C header ... C89-compatible"）；`tests/exrs_reference` 是 docs/checks.md 明确标注的 *optional differential gate*（可选 Rust exrs crate 差分校验），属辅助参考工具，不参与主体语言判定。

## 根因

1. **lang_detect.py `_manifest_scan` 的 manifest 判定未顶层锚定**：`if "Cargo.toml" in names` 中 `names` 是全树文件名的集合（`_iter_files` 递归），与 CMakeLists.txt/meson.build 分支使用的 `tops = {p.name: p for p in files if p.parent == src}` 顶层限定语义不一致。辅助工具的 Cargo.toml（tests/exrs_reference/Cargo.toml）因此被当作主库 manifest。

2. **冲突规则叠加**：manifest=rust 与源码统计主语言 c（79% ≥ 70%）矛盾 → 协议 §4.7 冲突规则判 mixed → 工具写终态 env_unsupported。

3. **R47 边界规则（附录 D.4）未被此路径应用**："辅助脚本（构建脚本是 python 等）不算主体语言"；`tests/exrs_reference` 是测试辅助差分门禁，不是库主体。c↔cpp 属兼容族不迁移。

## 最小修复方案（执行端边界规则判定，工具侧修正见回退方案）

1. 收到 lang-preflight `mixed`（或 detected ≠ c/cpp）且任务语言为 c/cpp 时，不直接接受工具终态：
   - 核对主库主体：README/主头文件/主源码统计（排除 tests/ 辅助目录）；
   - 主库主体为 c/cpp → 按 D.4 判 `detected=c/cpp`（c↔cpp 兼容族）→ 记录证据（reports/lang_preflight.log）后继续适配主流程；
   - 仅当主库主体确为非 c/cpp 时才走 env_unsupported/lang_hold。
2. 证据落盘：记录工具原始输出、主库主体判定依据（README 引文、文件统计、辅助工具定位文档如 docs/checks.md）、最终判定与继续执行结论。

回退方案（框架侧）：将 `_manifest_scan` 的 Cargo.toml/pyproject.toml/go.mod 分支改为与 cmake/meson 一致的顶层限定（`tops.get("Cargo.toml")`），属 SKILL 框架改动需单独框架 PR。

## 验证结果

| 环境 | 结果 |
|------|------|
| lang-preflight（修正判定前） | 工具输出 mixed(cargo) + env_unsupported 终态（记录存档） |
| D.4 边界规则判定 | 主库 = C89 单头文件库（C），辅助 Rust 差分门禁排除 → detected=c，与任务 cpp 兼容 → 继续适配 |
| 后续门禁实证 | conan-verify G0-G4/L2/L4/L5 全 PASS；conan create 消费者 2/2 通过；上游测试台账 10/18（/tmp 只读 erofs 阻塞 4 项如实计分母）——证明主库确为可正常适配的 C 库，工具误判若被直接接受将错误终止任务 |

## 禁止策略

- 禁止无主库主体证据直接硬适配（绕过 R47 且无法复核）；
- 禁止把"辅助差分门禁的 manifest"当作"库主语言"上报 mixed 后直接停止——必须先按 D.4 核验主库主体。

## 相关

- 相似条目：DRAFT-cl-unicode-lisp-lang-hold-verification（lang_hold 流程主题，非 manifest 误判内容）
- 引用原则：P005（框架侧补丁需可向上游提交）
- 适用边界/反例：主库主体确为 Rust/Python/Go 等的库不适用本条目（应走 env_unsupported/lang_hold）；仅适用于"辅助工具 manifest 被误判、主库主体为 c/cpp"的场景。
