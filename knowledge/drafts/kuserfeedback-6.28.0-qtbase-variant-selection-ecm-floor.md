# kuserfeedback-6.28.0：qtbase 双变体选型三步实证法 + ECM 版本门槛降版族 + po/qm 双保险

## 命中场景

(1) KDE Frameworks / Qt6 系包在两个 qtbase 变体（vanilla `qtbase/6.11.1` vs `qtbase-sql-dbus/6.11.1`）间选型；
(2) KF 6.28.0 系包遇到 `find_package(ECM 6.28.0)` 高于 registry 现有 `ecm/6.26.0`；
(3) 上游 po/qm 翻译处理需 Qt6LinguistTools（ohpcd 未发布）；
(4) flex/bison 条件注册的测试怎么计 N。

## 症状（实测，kuserfeedback 6.28.0）

1. 选 sql-dbus 变体 + qtdeclarative 同图 → 变体冲突炸图
2. `find_package(ECM 6.28.0)` 找不到（registry 最高 6.26.0）
3. `ecm_install_po_files_as_qm` 触发 Qt6LinguistTools 探测失败
4. surveytargetexpressiontest 注册与否影响 N 申报

## 根因

| 层 | 问题 |
|----|------|
| 变体 | qtdeclarative 原生 requires vanilla qtbase；主包若选 sql-dbus 变体则同图双变体 |
| ECM | 6.28.0 系 KF 包版本门槛 > registry KF6 代 ecm 上限 |
| po/qm | 上游无条件调 qm 处理；但 ecm_create_qm_loader 在 6.26.0 是自包含桩（实测）——qm 处理与 loader 桩可分离 |
| N 口径 | flex/bison 条件（HAVE_SURVEY_TARGET_EXPRESSIONS）在 OHOS SDK 自带工具下实测达成 |

## 方案（实证通过）

- **变体选型三步**：全树 grep `Qt6::Sql|Qt6::DBus`（本件 server 全关后为零）→ 选 vanilla → 单变体图
- **ECM 降版**：`find_package(ECM 6.28.0)` → `6.26.0`（attica/kdnssd 同款补丁族）
- **po/qm 双保险**：注释 qm 处理行 + `KF_SKIP_PO_PROCESSING=ON`；loader 桩照常生成
- **N 口径**：条件注册且条件实测达成 → 计入 N（本件 N=7）；offscreen 三件套跑 ctest

**验证**：conan create 全绿；ctest 6/6 + 1 QSKIP（KUSERFEEBACK_SKIP_TESTOPENGLINFOSOURCE=1，上游 WIN32 同款守卫）；消费者 6 断言过。

## 查重对照（knowledge/graph/index.tsv，766 条）

- `qtbase.*variant` / `qtbase-sql-dbus` / `qtdeclarative`：**零命中**
- ECM 降版：attica/kdnssd 补丁先例存在于各件归档，**知识图谱无独立条目**——本条含变体选型+qm 双保险为组合增量
- offscreen ctest 三件套：kstatusnotifieritem 先例（图谱内似有条目），本条仅引用不重复申报核心

## 关联

- PR：!14771（kuserfeedback 6.28.0，feat/kuserfeedback-6.28.0 @9bac8ca937）
- 复现：`conan create archives/k/kuserfeedback/6.28.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64`
