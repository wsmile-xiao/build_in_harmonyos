# lang-preflight 将含辅助 pyproject.toml 的纯 C 库误判为 python——按 R47 D.4 边界规则以 C/C++ 主体判定

- **草稿 ID**: DRAFT-cmsis-dsp-1.18.0-lang-preflight-pyproject-python-misdetect
- **来源**: cmsis-dsp 1.18.0 HarmonyOS PC 适配（纯 C DSP 库，PythonWrapper/cmsisdsp/Testing/Examples
  子目录共 4 个辅助 pyproject.toml，lang-preflight 误判 python）
- **分类**: preflight / build-system / manifest / language-detection / R47
- **状态**: 本地草稿（挂路径 B 知识库扩展 PR，与 cmsis-dsp 归档同 PR 交付）

## 问题 / 错误签名

- **错误输出**: `ohc-run.py lang-preflight cmsis-dsp 1.18.0 --src <src>` 判定
  `detected_language: python`，build_system=setuptools，manifest=`pyproject.toml 存在（python 打包 manifest）`，
  自动写终态 `env_unsupported`（draft:false），exit 2。
- **复现**: 源码树子目录含 pyproject.toml/setup.py 辅助工具（Python 绑定、测试工具、样例）的 C/C++
  库；`_manifest_scan` 对 pyproject.toml 使用全树文件名集合（rglob 全部文件，未限定顶层），
  与源码统计冲突（c 69% < 70% 阈值、未合并 c+cpp 的 92.6%）→ 判 python。
- **对照验证**: 主库主体为 C/C++——Source/ 660 个 .c、Include/ 49 个 .h；
  `find Source -name '*.c' | wc -l` = 660，c+cpp 合计 92.6% ≥ 70%；
  PythonWrapper/、cmsisdsp/ 为可选 Python 绑定，Testing/、Examples/ 为测试与样例辅助工具。

## 根因

1. **lang_detect.py `_manifest_scan` 的 pyproject.toml/setup.py 判定未顶层锚定**：
   `if names & {"pyproject.toml", "setup.py", "setup.cfg"}` 中 `names` 是全树文件名集合
   （`_iter_files` 递归），与 CMakeLists.txt/meson.build 分支的 `tops` 顶层限定语义不一致。
   辅助工具的 pyproject.toml 因此被当作主库 manifest。

2. **`_source_stats` 未合并 c/cpp 计数**：单语言 ≥70% 判定只看 c（69%）忽略 cpp（23%），
   实际 c+cpp=92.6% 满足主体条件却不被识别，叠加 manifest=python → 判 python。

3. **R47 边界规则（附录 D.4）未被此路径应用**："辅助脚本（构建脚本是 python 等）不算主体语言"；
   PythonWrapper/cmsisdsp 是绑定、Testing/Examples 是辅助，均不是库主体。c↔cpp 属兼容族不迁移。

## 最小修复方案（执行端边界规则判定，工具侧修正见回退方案）

1. 收到 lang-preflight `python`（或 detected ≠ c/cpp）且任务语言为 c/cpp 时，不直接接受工具终态：
   - 核对主库主体：README/主头文件/主源码统计（排除 PythonWrapper/Testing/Examples 等辅助目录）；
   - 主库主体为 C/C++（c+cpp 合并 ≥70%）→ 按 D.4 判 `detected=c/cpp`（c↔cpp 兼容族）→
     记录证据（reports/lang_preflight.log + 台账）后继续适配主流程；
   - 仅当主库主体确为非 c/cpp 时才走 env_unsupported/lang_hold。
2. 证据落盘：记录工具原始输出、主库主体判定依据（文件统计、辅助工具定位）、最终判定与继续执行结论。

回退方案（框架侧）：`_manifest_scan` 的 Cargo.toml/pyproject.toml/go.mod/setup.py 分支改为
与 cmake/meson 一致的顶层限定（`tops.get("pyproject.toml")`）；`_source_stats` 对 c/cpp 合并计数。
属 SKILL 框架改动需单独框架 PR。

## 验证结果

| 环境 | 结果 |
|------|------|
| lang-preflight（修正判定前） | 工具输出 python + env_unsupported 终态（存档） |
| D.4 边界规则判定 | 主库 = C/C++（Source 660 .c + Include 49 .h，c+cpp 92.6%），辅助 pyproject.toml 排除 → detected=c/cpp，与任务 cpp 兼容 → 继续适配 |
| 后续门禁实证 | conan-verify G0-G4/L2/L4/L5 全 PASS；test_package/消费者/鸿蒙专项测试全通过；上游测试默认配置 1527/1527、F16 304/304——证明主库确为可正常适配的 C 库，工具误判若被直接接受将错误终止任务 |

## 与既有家族条目的关系

- similar_to: DRAFT-exr_image-0.1.0-rc3-lang-preflight-aux-manifest（Cargo.toml→mixed(cargo) 变体）、
  DRAFT-E586-libyal-ohos-false-signals-langdetect-and-api（根目录绑定 manifest→mixed，
  status=pending-editor-review）、DRAFT-dshlibs-0.109-lang-preflight-pure-script-package-misdetect
  （纯脚本包→c 变体）
- 差异点（本候选新增）: pyproject.toml/setuptools→python 判定边界 + "c/cpp 应合并计数"（92.6% 主体）
  的修复要点；既有条目均为单一语言统计口径。

## 禁止策略

- ❌ 硬着头皮适配：无视 python 判定直接 conan 流程且无主库主体证据（R47 违规）。
- ❌ 把辅助 pyproject.toml 当主库 manifest 修改源码树去"迎合"工具判定。
