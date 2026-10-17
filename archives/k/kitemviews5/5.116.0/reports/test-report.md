# Test Report — kitemviews5 5.116.0 (KDE Frameworks 5 / Qt5)

- 平台: HarmonyOS PC (aarch64, OHOS 6.0, clang 15, libc++)
- 构建: `conan create archives/k/kitemviews5/5.116.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- 配方: kcoreaddons5 / kconfig5 同源 KF5 骨架（qt5-qtbase/5.15.2.2 + ecm/6.26.0）

## 1. 上游测试（R51 三步法）

清点（tarball 实测）:
- `autotests/klistwidgetsearchlinetest.cpp` → 1 个 ctest 用例
  （`ecm_add_test(... TEST_NAME kitemviews-klistwidgetsearchlinetest ...)`）。
- `tests/{kcategorizedviewtest,kwidgetitemdelegatetest,ktreewidgetsearchlinetest}.cpp`
  → 3 个可执行程序，仅 `ecm_mark_as_test()` 标记（该函数不调用 `add_test()`），
  **未被 ctest 注册**（实测 `build/Release/tests/CTestTestfile.cmake` 为空）。

实跑（真机原生，build() 内 ctest）:
```
Start 1: kitemviews-klistwidgetsearchlinetest
1/1 Test #1: kitemviews-klistwidgetsearchlinetest ...   Passed    0.34 sec
100% tests passed, 0 tests failed out of 1
Total Test time (real) =   0.35 sec
```

| 口径 | N | 实际运行 N′ | 通过率 |
|------|---|------------|--------|
| ctest 注册项 | 1 | 1 | 100% |
| tests/ 交互式 GUI 示例（未注册） | 3 | 3（启动级，超时终止） | 不适用（无断言） |

不可自动化项（具体技术原因）:
- `kcategorizedviewtest` / `kwidgetitemdelegatetest`: `main()` 创建 QMainWindow +
  KCategorizedView/QListView 后进入 `app.exec()`，需人工交互，无断言。
- `ktreewidgetsearchlinetest`: `main()` 进入 `QDialog::exec()`，需人工交互，无断言。
- 证据（`~/tmp/kitemviews5-gui-demos/*.log`）: 三者在
  `QT_QPA_PLATFORM=offscreen` 下 `timeout 5` 实跑均进入事件循环（rc=124，未崩溃）；
  `kwidgetitemdelegatetest` 实际运行 KWidgetItemDelegate 的 createItemWidgets 路径。

## 2. test_package（R34 + R53）— 16/16 PASS

```
SUMMARY: 16 passed, 0 failed
```

HarmonyOS 适配路径断言:
- `QApplication::platformName() == "offscreen"`（OHOS 无显示 GUI 路径）。
- `libKF5ItemViews.so` 已映射进进程。
- 该库 DT_SONAME 为无版本号 `libKF5ItemViews.so`（readelf 实测一致）。
- 该库带 DT_RUNPATH（E537 install-RPATH 链接，安装期不二次改写 ELF）。

功能 API 断言（真实调用）:
- KListWidgetSearchLine 过滤/恢复 + listWidget 往返。
- KTreeWidgetSearchLine 过滤 + treeWidget 往返。
- KFilterProxySearchLine 驱动 QSortFilterProxyModel（rowCount=1 → "banana"）。
- KCategorizedSortFilterProxyModel 分类开关 + 按 CategorySortRole 排序。
- KCategorizedView + KCategoryDrawer setModel/setCategoryDrawer 往返。

## 3. conan-verify（G0-G4 + L2/L4/L5）

`reports/conan-verify-report.md` verdict = PASS（G2 `conan create 成功`，
G3 `无系统同名库冲突`）。未 upload → manifest status = built。

## 4. 结论

- 上游 ctest 用例 1/1 通过；test_package 16/16 通过。
- 无 ctest 排除项；无源码补丁；无系统同名库冲突。
