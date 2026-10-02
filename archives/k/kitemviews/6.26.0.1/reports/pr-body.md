# 【依赖项】kitemviews 6.26.0.1 鸿蒙PC适配

## PR 信息

- **三方库名称**：kitemviews（KDE Frameworks 6 视图基类库）
- **上游版本**：6.26.0（适配修订版号 `6.26.0.1`，R37 适配修复后缀）
- **上游仓库地址**：https://invent.kde.org/frameworks/kitemviews
- **适配路径**：路径 A（基础适配） —— `archives/k/kitemviews/6.26.0.1/`
- **使用知识库**：技能 `openharmony-compile-agent`（本轮适用规则 R32/R34/R37/R38/R39/R51；知识条目 E002 `$TMPDIR` 只读规避）

补充字段（便于复核）：

| 项 | 内容 |
|---|---|
| 源码归档 | https://download.kde.org/stable/frameworks/6.26/kitemviews-6.26.0.tar.xz |
| SHA256 | `e76cc9d7561d0aae22b07a77552fbcddf61c8066bac5cfac9958ac065b617e74` |
| 构建系统 | CMake（ECM） |
| 目标平台 | HarmonyOS PC / OHOS aarch64（`ci/conan/profiles/ohos-aarch64`，clang 17 + libc++） |
| 依赖（required / build） | `qtbase/6.11.1` / `ecm/6.26.0` |
| 补丁 | `patches/0001-CMakeLists.txt.patch`（1 个） |
| 交付性质 | 【依赖项】`kio/6.26.0.1` 依赖闭包成员（自底向上逐个交付） |

### 本 `.1` 修订的适配内容

1. **`DT_SONAME` 链接标志注入**（本次 `.1` 的唯一改动，与 karchive/kcodecs/kguiaddons/kwindowsystem/kconfig/kwidgetsaddons 同范式）：OHOS 工具链下 CMake 无 `Platform/HarmonyOS` 模块，`CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG` 为空、lld 不产出 `DT_SONAME`，下游会记录绝对路径形式的依赖。配方 `generate()` 注入 `-Wl,-soname,` 后 `libKF6ItemViews.so.6` 的 SONAME 正确落盘。
2. 配方本体（6.26.0 适配集）保持不变：`BUILD_TESTING=ON`、po/qm 安装补丁沿用基线。

## 测试用例对比

### 上游库测试用例统计

> **计数口径**：上游**测试目标（测试源文件）**数 —— 上游 `kitemviews-6.26.0.tar.xz` 内 `autotests/` 1 项 + `tests/` 3 项 = **4**。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 4 | ① `autotests/klistwidgetsearchlinetest`（CTest 注册名 `kitemviews-klistwidgetsearchlinetest`）② `tests/kcategorizedviewtest` ③ `tests/ktreewidgetsearchlinetest` ④ `tests/kwidgetitemdelegatetest`；②③④ 均在 `tests/CMakeLists.txt` 中 `ecm_mark_as_test` 标记 |
| 集成测试 | 0 | 上游未注册集成测试 |
| 其他测试 | 0 | 上游无其他注册项 |
| **合计** | **4** | 上游 `autotests/` 1 + `tests/` 3 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试（自动判定） | 1 | 不变 | 上游唯一 CTest 注册项，OHOS offscreen QPA 下 1/1 通过，**无运行期排除**（未使用 `-E`） |
| 单元测试（交互式 GUI，上游未注册） | 3 | 不变 | ②③④ 为交互式 GUI 演示程序（`main()` → `mainWindow->show()` / `dialog.exec()`，需人工目视操作），**上游自身未将其注册为 CTest 用例**：ECM `ecm_mark_as_test` 仅在 `NOT BUILD_TESTING` 时影响构建，从不调用 `add_test`；实测 `build/Release/tests/CTestTestfile.cmake` 为空、`ctest -N` 输出 `Total Tests: 1`。适配后 **3/3 编译成功**且 **3/3 在 offscreen QPA 下成功启动**（证据见下），不构成适配遗漏 |
| 集成测试 | 0 | 不变 | 上游无集成测试注册项 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/`（R34 真实 API：`KTreeWidgetSearchLine` 构造 + `treeWidget()` 回环校验） |
| **合计** | **5** | **+1** | 上游 4 → 适配后 5；**自动断言通过率 2/2 (100%)**；3 项交互式目标为上游未注册的 GUI 演示，已附具体技术原因与启动证据 |

原始证据（本地构建目录 `build/Release` 实测）：

```
$ ctest -N
  Test #1: kitemviews-klistwidgetsearchlinetest
Total Tests: 1                        # 上游仅注册 1 项自动用例

$ ls build/Release/bin/
kcategorizedviewtest                kitemviews-klistwidgetsearchlinetest
ktreewidgetsearchlinetest           kwidgetitemdelegatetest     # 4/4 测试目标编译成功

$ QT_QPA_PLATFORM=offscreen timeout 6 ./bin/<target>        # 3 项交互式目标启动验证
kcategorizedviewtest        rc=124    # 超时触发=事件循环存活，无缺失库/链接错误
ktreewidgetsearchlinetest   rc=124
kwidgetitemdelegatetest     rc=124
# 三者 stderr 仅 Qt 字体目录提示（QFontDatabase: Cannot find font directory …）

$ conan create ... --build="kitemviews/*"
1/1 Test #1: kitemviews-klistwidgetsearchlinetest ...   Passed    0.31 sec
100% tests passed, 0 tests failed out of 1
kitemviews/6.26.0.1: Package '57ffd8c720a5bfee7e8827990cd6550a49181c1b' created

$ test_package
1/1 Test #1: test_kitemviews ..................   Passed    0.06 sec
PASS: KTreeWidgetSearchLine constructed and wired OK
=== RC=0 END 2026-09-30T12:43:53Z ===
```

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

上游测试**源码零改动**：`patches/` 仅含 `0001-CMakeLists.txt.patch`（顶层构建编排），未触及 `autotests/` 与 `tests/` 下任何文件；无运行期排除（`ctest --test-dir <build> --output-on-failure --no-tests=error` 全量执行上游注册的全部用例；上游 4 个测试目标 4/4 编译通过）。适配仅通过 CMake 编排调整：

1. `ecm_install_po_files_as_qm(poqm)` 注释停用 —— Qt6LinguistTools 组件未随本仓 `qtbase` 发布；仅影响 `.qm` 译文安装，不影响库功能与 ABI。
2. 无排除用例：上游注册的 1 项 CTest 在 OHOS 上全量执行；上游 `tests/` 下 3 项交互式 GUI 目标亦全部编译成功并完成启动验证（见「测试用例对比」）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

上游已有测试目标 4 项（1 项 CTest 自动用例 + 3 项交互式 GUI 演示）。本仓库按赛事要求**另行补充鸿蒙特有消费者用例 1 项**（计入上表「鸿蒙特有测试」，属适配新增覆盖，非补全上游缺失）：

- **新增测试文件清单**：
  1. `archives/k/kitemviews/6.26.0.1/test_package/test.cpp` — 构造 `KTreeWidgetSearchLine`，`setTreeWidget(&tree)` 后校验 `treeWidget() == &tree`，成功输出 `PASS: KTreeWidgetSearchLine constructed and wired OK`
  2. `archives/k/kitemviews/6.26.0.1/test_package/CMakeLists.txt` — CTest 注册（`cmake.test()`）
  3. `archives/k/kitemviews/6.26.0.1/test_package/conanfile.py`、`MANIFEST.yml` — 测试编排与断言声明
- **补充原因**：上游 `autotests/` 只覆盖 `KListWidgetSearchLine` 系列单元断言，不覆盖「外部消费者仅用头文件 + SONAME 链接 `libKF6ItemViews.so.6`」的集成路径；而本次 `.1` 修订的核心正是 SONAME 注入，需消费者用例反向检出「头文件缺失」与「SONAME 缺失导致链接失败」两类回归。

## 验证结果

- 编译状态：通过（上游 4 个测试目标 4/4 编译成功）
- 上游测试用例通过率：自动用例 1/1（100%）；交互式 GUI 3 项为上游未注册为 CTest 自动用例（3/3 编译成功、3/3 offscreen 启动验证通过，具体技术原因见「适配后测试用例统计」）
- 新增测试用例通过率：1/1（100%）

| 门禁 | 结果 | 证据 |
|---|---|---|
| conan create（真实重编译） | ✅ rc=0 | `--build="kitemviews/*"` 强制重编译至 `[100%]`；package id `57ffd8c720a5bfee7e8827990cd6550a49181c1b` |
| 上游 CTest（自动用例） | ✅ 1/1 (100%) | `100% tests passed, 0 tests failed out of 1`；`ctest -N` → `Total Tests: 1`（上游仅注册 1 项） |
| 上游交互式 GUI 目标（3 项） | ✅ 4/4 编译 · 3/3 启动 | `build/Release/bin/` 4 个测试可执行文件齐全；`QT_QPA_PLATFORM=offscreen timeout 6` 下 3 项 rc=124（事件循环存活），stderr 仅 Qt 字体目录提示 |
| test_package | ✅ 1/1 | `PASS: KTreeWidgetSearchLine constructed and wired OK` |
| SONAME | ✅ | `readelf -d`：`libKF6ItemViews.so.6` |
| W3 本地 CI（`ci/conan/build_and_test.sh`） | ✅ exit_code=0 | `.ci-result.json`：`step=W3_local_ci`、`integrity_hash=1c93ae6cb6191962`、`log_sha256=07c17ea041d7641a…9dd` |
| conan-verify（G0–G4） | ✅ | G1/G2/G3/G4 全 PASS（G0 因本地无原始 tarball 跳过，非阻塞） |
| W4 Pre-PR 独立审计 | ✅ pass（P0=0, P1=0, P2=1, P3=1） | `reports/audit-result.json` |
| W5 知识图谱完整性 | ✅ | doc↔kv 配套完整 |

产物清单：`lib/libKF6ItemViews.so{,.6,.6.26.0}`、`include/KF6/**`、`lib/cmake/KF6ItemViews/**`。

## 补充说明

1. **交付顺序**：本包属 `kio/6.26.0.1` 依赖闭包，按自底向上顺序（qtbase/ecm → karchive/kcoreaddons/kcodecs/kguiaddons/kwindowsystem/kconfig/kwidgetsaddons → kitemviews/solid → … → kio）逐个开分支、逐个提 PR。
2. **R37 版本后缀**：制品仓不支持同版本多 recipe revision 并存，故适配修订以 `6.26.0.1` 独立发布，`conandata.yml` 的 patches 键同步为 `"6.26.0.1"`；下游以 `kitemviews/6.26.0.1` 精确引用。
3. **R38 CLI 声明**：本包为纯库（`package_type=library`，无 `bin/` 产物、`package_info` 仅设 `libs=["KF6ItemViews"]`），按 R38 例外**不需要** `commands.json`。
4. **L2 说明**：无 `bin/` 目录，W3 的 L2 二进制冒烟不适用（`skip: no bin/ dir`），不计入通过率。
5. **rule4 计数口径修正**：上游测试目标数 = `autotests/` 1 + `tests/` 3 = **4**（与审查侧实测口径一致）；其中仅 `autotests/` 那 1 项被上游注册进 CTest，其余 3 项为上游自带的交互式 GUI 演示程序，上游从未对其调用 `add_test`。**原声明 1 系漏计 `tests/` 目录，属少报，本轮已按口径修正为 4**；适配侧实测：4 个目标 4/4 编译成功、3 项交互式目标 3/3 启动通过、自动断言 1/1 通过。
6. **验证日志**：`reports/test-report.md`、`reports/w3-local-ci.log`、`reports/audit-result.json`、`reports/rule4-remediation.md`（本轮 rule4 整改说明）。
