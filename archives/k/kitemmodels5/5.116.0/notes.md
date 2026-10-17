# kitemmodels5 5.116.0 — 适配笔记

> 归档时间: 2026-09-24
> 状态: built（本机 conan create 全绿：上游 12/12 + 消费者 15/15）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | kitemmodels5（KF5 线） |
| 版本 | 5.116.0（KDE Frameworks 5.116） |
| 上游 | https://invent.kde.org/frameworks/kitemmodels tag v5.116.0 |
| 源码 | https://download.kde.org/stable/frameworks/5.116/kitemmodels-5.116.0.tar.xz |
| 许可 | LGPL-2.0-or-later |
| 构建系统 | CMake + ECM（extra-cmake-modules） |
| 语言 | C++ / Qt5 |

## 二、任务背景

任务 #14105（wave10 P0，KF5 复国首件——解锁后续 KF5 链含 kpeople5 #14106）。
taskBranch=feat/kitemmodels5-5.116.0。
main 无 kitemmodels5 归档（KF6 线 kitemmodels/6.18.0.1 已有——本件为 KF5 平行线，不冲突）。

## 三、依赖核验（W0）

- qt5-qtbase/5.15.2.2 ✅（制品仓已发布，widgets-capable 版——5.15.2 是 -no-widgets 桩）
- ecm/6.26.0 ✅（制品仓已发布，tool_requires）
- 注：kitemmodels 是 KF tier1，只需 Qt（不依赖 kcoreaddons/ki18n）

## 四、适配要点（kitemviews5/kcoreaddons5 骨架直复用）

1. **QT_MAJOR_VERSION=5**：5.15.2.2 提供原生 Qt5 CMake configs（cmake_find_mode=none 消费）。
2. **CMAKE_SYSTEM_NAME=Linux**：OHOS→HarmonyOS 平台 CMake 无 UNIX 变量，强制 Linux 恢复
   ECM 的 ctest 注册（if(NOT CMAKE_CROSSCOMPILING)）与 POSIX 编译/rpath 设置。
3. **Qt5Qml 可选缺失**：上游 find_package(Qt5Qml NO_MODULE) 非 REQUIRED——qt5-qtbase 无 Qml，
   src/qml 子目录由 if(TARGET Qt5::Qml) 守卫自动跳过；QML autotests 同理不注册。
4. **KF_SKIP_PO_PROCESSING=ON**：Qt5LinguistTools 不随 qtbase 发布，跳过 po→qm。
5. **E537 + SONAME**：CMAKE_BUILD_WITH_INSTALL_RPATH=ON（OHOS 拒绝链接后被改写的 ELF）+
   CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE（无版本 DT_SONAME，L5 门禁）。
6. **CMAKE_BUILD_PARALLEL_LEVEL=1**：HMDFS 无法创建 make jobserver fifo（EPERM）。
7. **mkspecs 兼容层**：Qt5CoreConfigExtrasMkspecDir.cmake 硬编码 build-tree 路径
   <prefix>/../b/mkspecs——generate() 从包内 mkspecs/ 重建（kcoreaddons5 先例）。
8. **ctest 运行时 symlink 层**：测试可执行文件在 <build>/bin，其 libKF5ItemModels/Qt5 运行时
   依赖在 build tree/conan 包目录——_prepare_ctest_runtime_links() 在 <build>/../bin 建 symlink。
9. **/system/lib64 前置**：沙箱 LD_LIBRARY_PATH 带不兼容 libc++_shared.so，前置系统库优先解析。

## 五、上游测试（rule4 全量口径）

上游 autotests 注册（ecm_add_tests/ecm_add_test，CMake 构建 add_test 实测）：
1. kcolumnheadersmodeltest
2. kconcatenaterowsproxymodeltest
3. kdescendantsproxymodel_smoketest
4. kdescendantsproxymodeltest
5. kextracolumnsproxymodeltest
6. klinkitemselectionmodeltest
7. kmodelindexproxymappertest
8. knumbermodeltest
9. krearrangecolumnsproxymodeltest
10. krecursivefilterproxymodeltest
11. kselectionproxymodel_smoketest
12. kselectionproxymodeltest

**N=12，本机 conan create 内 ctest 真跑 12/12 全过（0 失败）**。

未注册（非缺测——上游条件未满足，如实申报）：
- kconcatenaterows_qml / ksortfilterproxymodel_qml：需 Qt5Qml/Qt5Quick（qt5-qtbase 未提供，
  if(TARGET Qt5::Qml) 守卫未满足不注册）。
- tests/proxymodeltestapp：示例程序（非 add_test 注册的测试，BUILD_TESTING 分支下因
  Qt5Script/QuickWidgets 缺失不构建）。

### test_package 消费者测试（15 断言全过）
- KConcatenateRowsProxyModel：拼接行数 3+1=4 + 第二源模型数据映射
- KExtraColumnsProxyModel（派生实现 extraColumnData）：附加列 2+1=3 + 源数据映射 + 附加列数据服务
- KDescendantsProxyModel：树扁平化 1 root + 2 children = 3 行
- KNumberModel：min=1 max=10 step=2 → 5 行，首值 "1" 末值 "9"
- KSelectionProxyModel：ExactSelection 过滤选中行 = 1 行
- KModelIndexProxyMapper：两条代理链间索引映射
- KRecursiveFilterProxyModel：递归过滤保留匹配子项的父项
- R53 ELF 断言：DT_SONAME=libKF5ItemModels.so（无版本）+ DT_RUNPATH 存在（E537）

## 六、踩坑记录

1. **qt5-qtbase/5.15.2 无 Widgets**：BUILD_TESTING=ON 时 find_package(Qt5 REQUIRED Test Widgets)
   失败——必须用 5.15.2.2（widgets-capable 版，kitemviews5 先例）。
2. **KExtraColumnsProxyModel 是抽象类**：消费者必须派生并实现 extraColumnData()；
   构造函数只收 parent（QObject*），源模型须构造后 setSourceModel(src) 再 appendColumn()。
3. **KNumberModel 5.x API**：setMinimumValue/setMaximumValue/setStepSize（不是
   setFirstNumber/setLastNumber——那是误记）；data() 返回格式化字符串（locale 相关）。
4. **KSelectionProxyModel 构造**：explicit KSelectionProxyModel(QItemSelectionModel*, QObject*)
   ——选择模型在构造时传入（无 setSelectionModel）。
5. **test_package 链接顺序**：target_link_libraries 须含 Qt5::Gui（QStandardItem 在 QtGui）——
   只链 Core/Test 时 Gui 的 include 路径不传递。
6. **环境库污染**：本机 shell export SDK 的 LD_LIBRARY_PATH（含与系统不匹配的 libc++.so）会
   污染 conanrun 测试执行（Error relocating libhicollie.z.so）——跑 test_package 前须 unset。

## 七、本机验证

```
cd archives/k/kitemmodels5/5.116.0
unset LD_LIBRARY_PATH   # 防 conanrun 环境污染
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
```
结果：上游 ctest 12/12 通过 + test_package 15 断言 15/15 通过。

## 八、交付物清单

- conanfile.py（kitemviews5 骨架 KF5 配方）
- conandata.yml（KDE 官方 tarball + sha256，无补丁）
- test_package/（CMakeLists + conanfile + test_kitemmodels5.cpp 15 断言含 R53）
- manifest.yaml ×2（软件级 + 版本级）
- README.md（软件级）
- notes.md（本文件）
