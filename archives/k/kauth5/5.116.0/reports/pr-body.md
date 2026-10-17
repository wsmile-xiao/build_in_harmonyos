# 鸿蒙 PC 三方库积分大赛 · PR 提交模板

每个适配任务须通过 Pull Request（PR）提交，PR 描述中必须包含以下测试用例对比信息。该信息将作为流水线复核和评审委员会评审的依据之一。

## PR 提交标题

所有参赛作品提交 PR 时，都需要在 PR 标题加前缀“【积分赛】/【依赖项】/【知识库扩展】/【无法适配】/【高难度挑战】”，便于赛事识别。

## PR 提交模板

## PR 信息

- **三方库名称**：kauth5（KDE Frameworks 5 / Qt5 分支的 KAuth）
- **上游版本**：v5.116.0
- **上游仓库地址**：https://invent.kde.org/frameworks/kauth
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（SKILL 主流程）；知识条目命中 E131/E135（Permission denied / ELF 签名）、E274/E316（SONAME 实体）、E542（poqm 依赖 Qt5LinguistTools）

---

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 4 | 来源：`autotests/CMakeLists.txt`（ecm_add_test + add_test）：`KAuthSetupActionTest`、`KAuthHelperTest`、`KAuthPolicyGenTest`、`KAuthPolicyGenTestCompare` |
| 集成测试 | 0 | 上游无独立集成测试目录 |
| 其他测试 | 0 | 无 |
| **合计** | **4** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 2 | -2 | OHOS 使用 `KAUTH_BACKEND_NAME=FAKE`（PolkitQt-1 未发布到 ohpcd，且运行需 polkit daemon），`KAuthPolicyGenTest` / `KAuthPolicyGenTestCompare` 位于 `if(NOT KAUTH_BACKEND_NAME STREQUAL "FAKE")` guard 内，故不注册；其余 2 项正常注册 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 1 | 新增 | 针对鸿蒙平台特性的测试：`test_package/test_kauth5_ohos.cpp` 断言 OHOS FAKE 后端回退路径的可观测行为（`#ifndef __OHOS__ #error` 守卫） |
| **合计** | **3** | **-1** | |

---

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 未改动 `autotests/` 下任何文件；`KAuthSetupActionTest`、`KAuthHelperTest` 两个目标均以原生源码编译通过。唯一源码级改动是对顶层 `CMakeLists.txt` 注释掉 `ecm_install_po_files_as_qm(poqm)`（见「补充说明」），不涉及任何测试用例。

---

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> 上游 `autotests/` 的用例只针对库内部行为，**没有覆盖「OHOS 平台后端回退」这一适配语义**。适配后补全：

> - **补全的测试范围**：为鸿蒙平台特性新增 2 个消费者测试程序（`test_kauth5`、`test_kauth5_ohos`），覆盖 `KAuth::Action` 构造 / `name()` / `detailsV2()` / `arguments()` / `helperId()` 往返、空 Action 无效性、FAKE 后端下 `status()==DeniedStatus`、`execute()->exec()==false` 且 `error()==ActionReply::BackendError`、`data().isEmpty()`、`ActionReply` 工厂函数，以及 OHOS 回退路径的 `hasHelper()` 行为
> - **补全原因**：验证产物在鸿蒙 PC 上「可链接 + 可运行 + 后端回退行为正确」，而非仅编译通过
> - **新增测试文件清单**：
>   1. `test_package/test.cpp` — 消费者视角调用 KF5AuthCore 公共 API（编译并真机执行通过）
>   2. `test_package/test_kauth5_ohos.cpp` — 鸿蒙特有测试：OHOS FAKE 后端回退行为的运行时断言

---

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：
  - 实际运行口径：**1/2（50%）** — `KAuthSetupActionTest` 通过，`KAuthHelperTest` 已实际尝试运行但被排除
  - 注册且可运行口径：**1/1（100%）**
  - 全部上游口径：**1/4（25%）**
- 新增测试用例通过率：**2/2（100%）**

### 上游测试逐项明细（R51 三步法：清点 → 运行 → 回填）

| ctest 名 | 状态 | 证据 |
|---|---|---|
| `KAuthSetupActionTest` | **通过** | 真机实测 `1/1 Test #1: KAuthSetupActionTest ... Passed 0.09 sec`；`100% tests passed, 0 tests failed out of 1` |
| `KAuthHelperTest` | **排除**（已实际尝试运行） | 配方用 dbus 包自带 `bin/dbus-daemon` + `share/dbus-1/session.conf` 启动私有 session bus；报 `Error registering helper DBus service "org.kde.kf5auth.autotest" "Not connected to D-Bus server"`，随后挂起，在 60s 上限超时，如实记为排除、不计为通过 |
| `KAuthPolicyGenTest` | **未注册** | `add_test` 位于 `if(NOT KAUTH_BACKEND_NAME STREQUAL "FAKE")` guard 内 |
| `KAuthPolicyGenTestCompare` | **未注册** | 同上（依赖 `KAuthPolicyGenTest`） |

---

## 补充说明

1. **后端选择**：`KAUTH_BACKEND_NAME=FAKE`、`KAUTH_HELPER_BACKEND_NAME=FAKE`。KAuth 原生后端为 PolkitQt-1，未发布到 ohpcd（已用 recipe-only download 探测确认）且运行还需 polkit daemon；上游 `src/ConfigureChecks.cmake` 在探测不到时本就回退 `FAKE`，本配方显式固定同一决策而非依赖系统探测。副作用：`kauth-policy-gen` 与两个插件 MODULE 目标不构建。
2. **依赖版本族统一**：`qt5-qtbase/5.15.2.2` 是仓库内首个提供 `Qt5Widgets` / `Qt5DBus` 组件的版本（上游需要 `find_package(Qt5 ... Widgets)` 与 `find_package(Qt5DBus CONFIG REQUIRED)`）；`kcoreaddons5/5.116.0` 声明的是 `qt5-qtbase/5.15.2`，故用 `override=True` 统一。override 只改写引用，kcoreaddons5 已发布二进制记录的依赖为 `qt5-qtbase/5.15.Z`，仍是缓存/制品仓命中、不触发重建。
3. **唯一源码补丁**：注释 `ecm_install_po_files_as_qm(poqm)` —— qt5-qtbase 未提供 Qt5LinguistTools（lconvert/lrelease）。与 kcoreaddons5 / kwidgetsaddons5 / kconfig5 同源先例（仓库内 54 例）。
4. **本任务发现并沉淀的通用问题（已按 R31 生成知识草稿 `knowledge/drafts/DRAFT-ohos-unsigned-elf-permission-denied.md`）**：OHOS 加载器拒绝**未签名 ELF**（`.codesign` 段为空）时，报错文本为 `Error loading shared library <lib>: Permission denied`，**并伴随误导性的** `Error relocating ...: symbol not found`；用 `ctypes.CDLL()` 对单库 dlopen 可一步区分真因（签名问题）与假因（符号/SONAME 缺失）：报 `Permission denied` 即签名问题，报 `not found` 才是符号或路径问题。
5. **已知限制**：`KAuthHelperTest` 需要可用的 session D-Bus，OHOS 沙箱不提供（属平台/生态侧限制，非配方缺陷）；已在配方 `build()` 中明文 WARN 输出，且不将其计入通过。
6. **待办（可另立项，非本 PR 范围）**：`kcoreaddons5/5.116.0` 的制品仓二进制 `.codesign` 为空，建议由该包归属方补签名；本配方仅在 `build_folder` 内做私有副本签名（`signed-runtime/`）以完成验证，未改动任何依赖包内容（遵守 R49/E524）。
7. **验证环境**：HarmonyOS aarch64 真机（本机原生构建）；命令 `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=missing`；W3 本地 CI 模拟与 G2 干净构建均通过。

---

## 模板使用说明

| 填写项 | 是否必填 | 说明 |
|--------|---------|------|
| 三方库名称及上游版本 | 必填 | 用于追溯上游变更 |
| 测试用例对比表格 | 必填 | 用于追溯上游测试用例完整性 |
| 上游测试修改说明 | 条件必填 | 若存在修改则必填，须逐条说明原因与内容 |
| 测试补全说明 | 条件必填 | 若上游无测试且适配后补全则必填 |
| 验证结果 | 必填 | 由参赛者填写本地验证结果 |

## 常见场景示例

**场景一：上游有完整测试，适配后保持不变**
上游 120 个单元测试 + 30 个集成测试，适配后全部通过，测试用例无修改。
测试用例对比：合计 150 → 150（不变），未修改上游测试，无需补全。

**场景二：上游有测试，部分需修改以适配鸿蒙**
上游 80 个单元测试，其中 3 个与 POSIX 文件路径相关，因鸿蒙文件系统差异需修改断言。修改后全部通过。
测试用例对比：合计 80 → 80（不变），修改上游测试 3 处（路径断言），无需补全。

**场景三：上游无测试，适配后补充**
上游库仅提供示例代码，无正式测试框架。适配后补全 45 个单元测试、8 个集成测试，全部通过。
测试用例对比：合计 0 → 53（+53），未修改上游测试（上游无测试），已补全。

**场景四：上游有测试 + 适配后针对鸿蒙新增测试**
上游 60 个单元测试全部保留并通过。另新增 15 个鸿蒙特有场景测试（如窗口管理、输入法适配）。
测试用例对比：合计 60 → 75（+15 新增），未修改上游测试，无需补全（上游已有测试）。
