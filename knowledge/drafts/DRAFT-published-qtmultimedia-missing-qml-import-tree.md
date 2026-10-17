# DRAFT-published-qtmultimedia-missing-qml-import-tree: 已发布 Qt 模块包缺 QML 导入树的消费端声明治理

> **Contributor**: GoliWie | **Status**: Draft | **Updated**: 2026-09-18
> **申报域**: 依赖闭包（八分类）｜**机理分层**: L2 跨库工程模式（两实例：kirigami-addons/1.13.0 真实失败 + mauikit/4.0.2 预防性同型修复）
> **拟提升编号：由知识库主编确认（不自行编号）**

## 规则（一句话）

已发布的 Qt 模块 conan 包可能只含 C++ 库而缺 QML 导入树——消费端必须先验证导入树存在再声明 `ecm_add_qml_module DEPENDENCIES` 或 import 该 QML 模块；缺失时应移除声明并把 QML 用法降级为无该模块的等价实现（行为降级如实记录）。

## 问题（两个失败面）

已发布 qtmultimedia/6.11.1 包只含 C++ 侧产物：`qml/` 与 `lib/qml/` 均不存在（真机 `ls -d` 实证），C++ 链接/头文件/metatypes 完好。上游 QML 消费面据此分两路失败：

1. **构建/扫描面**：qmlimportscanner 与 QML 编译期报 `module "QtMultimedia" is not installed`。第二实例 kirigami-addons/1.13.0 真实命中：4/6 上游风格 autotest 挂（tst_sounds.qml:11 直触 SoundEffect + album×3 链式），失败记录见 `archives/k/kirigami-addons/1.13.0/notes.md`。
2. **运行期毒化面**（mauikit 案例）：上游 `ecm_add_qml_module(DEPENDENCIES "QtMultimedia")` 落进安装后 qmldir 的 `depends` 行；QQmlEngine 加载 `org.mauikit.controls` 时按 depends 递归定位导入树，失败即**整个模块不可加载**——即使消费者从不实例化任何多媒体类型。

缺口本质是制品仓对 Qt 部署 QML 部分的**逐包裁剪**（qtdeclarative/qtsvg 的 QML 树在包内、qtmultimedia 不在），不是上游源码缺陷；不能按家族推断，必须逐包验证。

## 修复模式（rec）

消费端补丁两步（mauikit `patches/0002` 原文）：

1. 从 `src/CMakeLists.txt` 的 `DEPENDENCIES` 移除 `"QtMultimedia"`，阻断 qmldir depends 毒化；模块其余功能全部可加载。
2. 把 QML 用法降级为无该模块的等价实现：`ToastArea.qml` 的两个 `SoundEffect` → 同 `play()` API 的 no-op `QtObject`；**C++ 侧依赖保留**（Qt6::Multimedia 的 C++ 链接与头文件不受导入树缺失影响）。

诚实边界：这是**行为降级而非功能等价**（通知音效在该平台不可用）；降级已在补丁注释、notes.md 与 manifest 中如实记录，未静默。

## 退路（fallback，含诚实权衡）

**手工最小导入树**：构造模块目录 + qmldir + 空插件占位部署进 `QML2_IMPORT_PATH`，使扫描/校验与 qmldir depends 解析通过。权衡：只满足解析/校验面，运行期仍无真实 QtMultimedia QML 功能；与后续官方包补齐导入树时可能同 URI 双源冲突——**掩盖而非修复**，仅当必须保留上游 DEPENDENCIES 原文时作退路。

## 反模式（forbid）

**未验证 `qml/`/`lib/qml/` 导入树存在即声明（或原样保留上游的）DEPENDENCIES / import**：制品仓逐包裁剪、家族内不一致，按家族推断必踩缺口；qmldir depends 是强约束。后果：轻则构建期 module not installed 大面积挂测（kirigami-addons 4/6 autotest），重则 qmldir 毒化使整个 QML 模块对所有消费者运行期不可加载——其余可用的控件被一个未用到的 depends 拖垮。

## 验证（自包含探针）

见同名 .kv `verification_cmd`：① `ls -d "$QT/qml" "$QT/lib/qml"` 两次 No such file（导入树缺失实证）；② `grep -n 'QtMultimedia' archives/m/mauikit/4.0.2/patches/0002-ohos-qtmultimedia-qml.patch`（毒化面触点与移除原文）；③ `grep -n 'QtMultimedia' archives/k/kirigami-addons/1.13.0/notes.md`（第二实例真实失败行）。

本 run 闭环：patch 0002 应用后，权威 CI 二轮 ctest 3/3（含 `qml_module` 用例——org.mauikit.controls 模块在 offscreen QPA 真实加载并实例化控件），L0–L5 全过。

## 去重记录（与相近条目划界）

- **E343**（qtmultimedia 需 qtshadertools 的 Qt6ShaderTools_DIR）：构建依赖缺口，非 QML 导入树缺口——不同坑。
- **E344**（OHOS 无媒体后端时 integration 测试排除）：测试排除策略，非模块声明治理——不同坑。
- **DRAFT-ecm-qmlmodule-noquiet-required-trap**：同属 ecm_add_qml_module 消费族，但坑在 find_package 噪声/QUIET 语义，与导入树缺失正交。
- 检索复核：`grep -rln -i 'QtMultimedia' knowledge/` → E343/E344 + kirigami-addons 相关草稿，读题均非"QML 导入树缺失"；graph 内无本条覆盖（Curator/Auditor 双重复核一致）。

## 关系

similar_to: E343, E344, DRAFT-ecm-qmlmodule-noquiet-required-trap
principles: P-RUNTIME-002, P-PATCH-003
