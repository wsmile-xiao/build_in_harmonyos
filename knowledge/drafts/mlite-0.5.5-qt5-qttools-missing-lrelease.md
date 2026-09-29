# qmake 上游测试目标硬编码 $$[QT_INSTALL_BINS]/lrelease：制品仓无 Qt5 qttools 时上游测试无法构建（打包可绕开，但 R51 要求实跑上游测试）

> Draft: `DRAFT-MLITE-055-QT5-QTTOOLS-MISSING-LRELEASE-UPSTREAM-TESTS`
> Stem: `mlite-0.5.5-qt5-qttools-missing-lrelease` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MLITE-055-QT5-QTTOOLS-MISSING-LRELEASE-UPSTREAM-TESTS
- **严重度**: 2（3=🔴blocking / 2=🟡medium / 1=🟢minor）
- **类别**: qmake|qt5|test-build|toolchain-gap
- **触发工具**: make
- **阶段**: compilation

## 错误特征

```
lrelease: not found|Error 127|\.qm\] Error 127|Cannot find .*lrelease
```

匹配关键词：`lrelease, lupdate, Qt Linguist, qttools, qt5-qttools, .qm, TRANSLATIONS, ut_mdesktopentry, qmake`

## 根因

上游测试 .pro 用 QMAKE_EXTRA_COMPILERS 在 target_predeps 阶段调用 $$[QT_INSTALL_BINS]/lrelease 生成 .qm；qt5-qtbase 只含 Qt5 基础模块（无 Linguist），而制品仓没有 Qt5 的 qttools（qt5-qttools/5.15.2、qttools/5.15.2 均 404），因此 make 在该目标上以 Error 127 终止。

## 影响范围

任何"上游把翻译/资源生成挂在构建图里"的 Qt5 项目——打包阶段可以通过只构建库目标绕开，但上游测试（R51）就跑不起来。

## 验证命令

```bash
conan download qt5-qttools/5.15.2 -r=ohpcd --only-recipe; echo $?   # 1=不存在；对照 qttools/6.11.1 → 0
```

## 处置建议

- **优先级**: 3
- **方案**: `use-qt6-lrelease-as-build-tool-and-verify-qm-loads`
- **说明**: (1) 打包：只构建库/工具子目标（qmake 顶层 Makefile 的 sub-src-all / sub-tools-all），不构建 tests——避免为一个测试专用工具引入额外依赖；(2) 实跑上游测试：用 Qt6 qttools/6.11.1 的 lrelease 生成 .qm（实测 Qt5.15 的 QTranslator 能正确加载 Qt6 lrelease 产出的 .qm，翻译用例全绿），或在 qtbase 包 bin/ 放 lrelease 转发脚本；(3) 如上两者都不可行，则须在 PR 中申报"上游测试缺 lrelease 工具链"并按 R51 记录具体技术原因，禁止用 test_package 替代上游统计。
- **参考命令**: `lrelease -idbased tests/ut_mdesktopentry.ts -qm tests/ut_mdesktopentry.qm`
- **可自动修复**: false

## 可复用知识总结（同类问题通用）

- **问题类**：qmake 项目的**构建图内嵌 Qt Linguist 步骤**（`lrelease`/`lupdate`），而制品仓缺 Qt5 qttools → 构建/测试阶段 `Error 127`。
- **识别信号**：`Makefile.<target>: … .qm] Error 127`、`lrelease: not found`；`.pro` 内 `$$[QT_INSTALL_BINS]/lrelease`。
- **通用处置**：①打包阶段只构建库/工具子目标（`sub-src-all`/`sub-tools-all`），不为测试专用工具引入额外依赖；②实跑上游测试时用可用的 `lrelease`（实测 **Qt6 qttools 产出的 `.qm` 可被 Qt5.15 `QTranslator` 正常加载**，翻译用例全绿），或在 qtbase 包 `bin/` 放转发脚本；③若都不可行，按 R51 如实申报"缺工具链"并给出具体技术原因，禁止用 test_package 冒充上游统计。
- **适用范围**：任何"上游把翻译/资源生成挂在 make 目标图里"的 Qt5 项目。
