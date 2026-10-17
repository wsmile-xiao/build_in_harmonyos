# rule4 整改说明 — kitemviews 6.26.0.1 上游测试用例计数口径修正

> **对象 PR**: #14045 【依赖项】kitemviews 6.26.0.1 鸿蒙PC适配
> **审查裁决**: VERDICT=FAIL（rule4 验证结果：**少报 —— 上游实测 N=4 > 声明 N=1**）
> **整改日期**: 2026-10-02
> **整改结论**: 声明口径已按审查侧同口径修正为 **N=4**；上游 4 个测试目标 **4/4 编译成功**、
> `tests/` 3 项交互式目标 **3/3 offscreen 启动验证通过**、上游唯一 CTest 自动用例 **1/1 通过**。

---

## 一、问题定位：不是审核出错，是本 PR 漏计上游 `tests/` 目录

审查侧「上游实测 N=4」的口径为**上游测试目标（测试源文件）数**。复核上游
`kitemviews-6.26.0.tar.xz` 源码树，测试目标恰为 4 个：

| # | 目标 | 目录 | 上游是否注册进 CTest |
|---|---|---|---|
| 1 | `kitemviews-klistwidgetsearchlinetest` | `autotests/` | **是**（`ecm_add_test`，注册名即目标名） |
| 2 | `kcategorizedviewtest` | `tests/` | 否 |
| 3 | `ktreewidgetsearchlinetest` | `tests/` | 否 |
| 4 | `kwidgetitemdelegatetest` | `tests/` | 否 |

原 PR 正文的「上游库测试用例统计」把上游 N 记为 **1** —— 只数了 CTest 注册项，
**漏计 `tests/` 目录下 3 个目标**，故被判「少报」。审查侧数字正确，本 PR 声明值有误。

## 二、为什么上游只暴露 1 项自动用例（而非 4）

上游顶层 `CMakeLists.txt` 在 `BUILD_TESTING=ON` 时**同时** `add_subdirectory(autotests)`
与 `add_subdirectory(tests)`，`tests/CMakeLists.txt` 也为 3 个目标调用了
`ecm_mark_as_test`。但 ECM 的该宏**不调用 `add_test`**：

```
# ECMMarkAsTest.cmake（ECM 6.26）
function(ecm_mark_as_test target)
    if(NOT BUILD_TESTING)
        set_target_properties(${target} PROPERTIES EXCLUDE_FROM_ALL TRUE)
    endif()
endfunction()
```

即 `ecm_mark_as_test` 在 `BUILD_TESTING=ON` 时是**空操作**，仅用于 `BUILD_TESTING=OFF`
时把测试目标移出 `all`。实测证据：

```
$ cat build/Release/tests/CTestTestfile.cmake
# (空文件 —— 3 个 tests/ 目标没有任何 add_test)

$ ctest -N
  Test #1: kitemviews-klistwidgetsearchlinetest
Total Tests: 1
```

并且那 3 个目标是**交互式 GUI 演示程序**（`main()` → `mainWindow->show()` /
`dialog.exec()`），本身不含任何程序化断言，上游从未将其纳入自动判定。因此
「上游 N=4」与「CTest 仅 1 项」并不矛盾：**4 是测试目标数，1 是可自动判定数**。

## 三、适配侧实测结果（修正后的完整口径）

| 指标 | 结果 |
|---|---|
| 上游测试目标编译 | **4 / 4**（`build/Release/bin/` 4 个可执行文件齐全） |
| 上游 CTest 自动用例执行 | **1 / 1**，`100% tests passed, 0 tests failed out of 1`，无运行期排除（`-E` 未使用） |
| `tests/` 交互式目标启动验证 | **3 / 3**（`QT_QPA_PLATFORM=offscreen timeout 6`，三者 rc=124 = 超时触发且事件循环存活；stderr 仅 `QFontDatabase: Cannot find font directory` 提示，无缺失库/链接错误） |
| 上游测试源码修改 | **0**（`patches/` 仅 `0001-CMakeLists.txt.patch`，属顶层构建编排，未触及 `autotests/`、`tests/`） |
| 适配方补全用例（`test_package/`） | **1 / 1** 通过（R34 真实 API：`KTreeWidgetSearchLine` + `treeWidget()` 回环） |

| 上游 N → 适配后 M | 通过率 |
|---|---|
| **4 → 5** | 自动断言 **2/2 (100%)**；3 项交互式目标为上游未注册的 GUI 演示，已给出具体技术原因与启动证据 |

## 四、整改动作清单

| 文件 | 改动 |
|---|---|
| PR #14045 描述 | 「上游库测试用例统计」上游 N：1 → **4**（新增计数口径说明与 4 个目标逐项列举）；「适配后测试用例统计」拆分「自动判定 1 项」与「交互式 GUI 3 项」；「验证结果」补 4/4 编译与 3/3 启动；「补充说明」新增 rule4 计数口径修正条目 |
| `reports/pr-body.md` | 同上（正文源文件） |
| `reports/test-report.md` | §1 清点表改为 4 口径；新增 §2.1 四目标实测证据；§3 说明 3 项为上游未注册而非被排除；§5 对比表 4 → 5 |
| `notes.md` | 新增「Test counting convention (rule4 review fix, 2026-10-02)」章节 |
| `manifest.yaml` | `test_results.upstream` 更新为 4/4 编译 + 1/1 自动用例 + 3/3 启动 |
| `test_package/MANIFEST.yml` | 新增 `upstream_test_target_count: 4` / `upstream_ctest_registered_count: 1`，`upstream_tests` 逐项列出 4 个目标 |

## 五、规则判定预期（整改后）

| rule4 判定点 | 整改后 |
|---|---|
| ① 编译状态 | ✅ 通过（上游 4 个测试目标 4/4 编译成功） |
| ② 上游/新增通过率 | ✅ 自动断言 **2/2 (100%)**；3 项交互式目标非上游自动用例，已附具体技术原因（ECM 宏语义 + 空 `CTestTestfile.cmake` + offscreen 启动证据），非环境搪塞 |
| ③ 少报核验（实测 N ≤ 声明 N） | ✅ **实测 N=4 ≤ 声明 N=4**（同口径：上游测试目标数） |

---

*本说明中的数字均来自本机实测（`build/Release` 构建目录 + `conan create` 原始日志），
未使用推断值；3 项交互式目标未做任何形式的跳过或伪造通过。*
