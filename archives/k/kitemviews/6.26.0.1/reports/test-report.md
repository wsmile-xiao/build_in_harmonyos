# kitemviews 6.26.0.1 测试报告

- 软件 / 版本：kitemviews 6.26.0.1（上游 6.26.0 + `.1` 适配修订后缀，R37）
- 源码：https://download.kde.org/stable/frameworks/6.26/kitemviews-6.26.0.tar.xz
- SHA256：`e76cc9d7561d0aae22b07a77552fbcddf61c8066bac5cfac9958ac065b617e74`
- 构建系统：CMake（ECM）；依赖 `qtbase/6.11.1`
- 目标平台：HarmonyOS PC / OHOS aarch64（`ci/conan/profiles/ohos-aarch64`）

## 1. 上游测试用例清点（R51）

**计数口径**：上游**测试目标（测试源文件）**数 = `autotests/` 1 + `tests/` 3 = **4**（与 PR 审查侧实测口径一致）。

| 项 | 数量 |
|---|---|
| 上游测试目标合计 | 4 |
| 其中：上游注册进 CTest 的自动用例 | 1（`kitemviews-klistwidgetsearchlinetest`） |
| 其中：上游自带交互式 GUI 演示目标（上游从不 `add_test`） | 3（`tests/kcategorizedviewtest`、`tests/ktreewidgetsearchlinetest`、`tests/kwidgetitemdelegatetest`） |
| 适配后测试目标编译成功 | 4 / 4 |
| 在 OHOS 上实际执行的自动用例 | 1 / 1 |
| 环境限制排除的自动用例 | 0 |
| 上游集成 / 其他框架用例 | 0 |

## 2. 实际运行结果（真实执行，非缓存）

配方 `conanfile.py::build()` 内（`BUILD_TESTING=ON`）：

```
ctest --test-dir "<build_folder>" --output-on-failure --no-tests=error
```

结果：

```
1/1 Test #1: kitemviews-klistwidgetsearchlinetest ...   Passed    0.31 sec

100% tests passed, 0 tests failed out of 1
```

- 上游通过率：**1/1 (100%)**，无排除项（`-E` 未使用）。
- 整个 `conan create` 结束 RC=0（`=== RC=0 END 2026-09-30T12:43:53Z ===`）。

### 2.1 上游 4 个测试目标的实测证据

```
$ ls build/Release/bin/          # 4/4 测试目标编译成功
kcategorizedviewtest                kitemviews-klistwidgetsearchlinetest
ktreewidgetsearchlinetest           kwidgetitemdelegatetest

$ ctest -N                       # 上游仅注册 1 项
  Test #1: kitemviews-klistwidgetsearchlinetest
Total Tests: 1

$ cat build/Release/tests/CTestTestfile.cmake
# (空 —— tests/ 下 3 个目标未被上游注册)

$ QT_QPA_PLATFORM=offscreen timeout 6 ./bin/<target>     # 3 项交互式目标启动验证
kcategorizedviewtest        rc=124
ktreewidgetsearchlinetest   rc=124
kwidgetitemdelegatetest     rc=124
# rc=124 = 超时触发、事件循环存活；stderr 仅 QFontDatabase 字体目录提示
```

## 3. 排除项

无。上游注册的 1 项 CTest 在 OHOS aarch64（offscreen QPA）下直接通过，未做任何运行期排除（`-E` 未使用），未删除/改写任何上游测试源码。

上游 `tests/` 下 3 个目标**并非被排除，而是上游自身未注册**：`tests/CMakeLists.txt` 中的 `ecm_mark_as_test` 在 ECM 实现里不调用 `add_test`（仅在 `BUILD_TESTING=OFF` 时影响构建），因此它们从未出现在上游 CTest 清单中（实测 `tests/CTestTestfile.cmake` 为空）。本轮对三者做了「编译 + offscreen 启动」验证，均通过。

## 4. 适配方补全用例（`test_package/`，R34）

`test_package/test.cpp` 真实调用被测包 API：

```cpp
QApplication app(argc, argv);
QTreeWidget tree;
KTreeWidgetSearchLine searchLine(&tree);
searchLine.setTreeWidget(&tree);
if (searchLine.treeWidget() != &tree) { /* FAIL */ }
```

- 运行结果：

```
1/1 Test #1: test_kitemviews ..................   Passed    0.06 sec
100% tests passed, 0 tests failed out of 1
PASS: KTreeWidgetSearchLine constructed and wired OK
```

- 该用例以 CTest（`CMakeLists.txt` + `cmake.test()`）与二进制直跑双路径执行，同时覆盖头文件可用性与 `libKF6ItemViews.so.6` 链接（SONAME 由本 `.1` 修订修复注入）。

## 5. 测试用例对比

| 测试类型 | 上游 N → 适配后 M | 通过率 |
|---|---|---|
| 单元测试（上游 CTest 自动用例） | 1 → 1 | 1/1 (100%) |
| 单元测试（上游交互式 GUI 目标，未注册 CTest） | 3 → 3 | 编译 3/3；启动验证 3/3（rc=124），无程序化断言 |
| 集成测试 | 0 → 0 | — |
| 其他测试（鸿蒙消费者用例） | 0 → 1 | 1/1 (100%) |
| **合计** | **4 → 5** | **自动断言 2/2 (100%)**；3 项交互式目标附具体技术原因与启动证据 |

## 6. 结论

编译 rc=0、上游 4 个测试目标 4/4 编译成功、CTest 自动用例 1/1 全绿、`test_package` 1/1 通过、`libKF6ItemViews.so.6` SONAME 正确。作为 `kio/6.26.0.1` 依赖闭包的一员交付。
