# kcoreaddons5 5.116.0 适配笔记

> KF5 系列（Qt5 版）kcoreaddons，与已有的 kcoreaddons/6.x (KF6) 归档分开。
> 参考配方：attica-kf5/5.116.0（同依赖 qt5-qtbase/5.15.2 + ecm/6.20.0）。

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++ (15.0.4, OHOS toolchain)
- 状态: built（探索性编译通过，待 conan 配方固化）

## 编译步骤

源码：https://download.kde.org/stable/frameworks/5.116/kcoreaddons-5.116.0.tar.xz

手工 cmake 配置（探索阶段，依赖从 conan 制品仓安装）：
```bash
conan install --requires=qt5-qtbase/5.15.2 --requires=ecm/6.20.0 \
  -r=ohpcd -pr:h=ohos-aarch64 --build=missing

QTBASE=$(conan cache path "qt5-qtbase/5.15.2:...")
ECM=$(conan cache path "ecm/6.20.0:...")

cmake -S $SRC -B $BUILD \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=$PREFIX \
  -DKF_IGNORE_PLATFORM_CHECK=TRUE \
  -DKDE_INSTALL_USE_QT_SYS_PATHS=OFF \
  -DBUILD_TESTING=ON \
  -DUSE_DBUS=OFF \
  -DBUILD_QCH=OFF \
  -DECM_MODULE_PATH="$ECM/share/ECM/modules;$ECM/share/ECM/find-modules;$ECM/share/ECM/kde-modules" \
  -DCMAKE_PREFIX_PATH="$QTBASE/lib/cmake;$ECM/share/ECM/cmake"
```
`make -j2` → 100% 构建成功 → `make install DESTDIR=$TEST_PREFIX` → `ctest`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "System is unknown to cmake, create Platform/HarmonyOS"，`if(UNIX)` 不成立导致 `_unix.cpp` 源（kuser_unix/kshell_unix 等）未编译，链接报 `undefined symbol: KUser::homeDir()` | CMake 4.1 无 Platform/HarmonyOS.cmake，UNIX 变量未置位 | conanfile 用 `tc.variables["CMAKE_SYSTEM_NAME"]="Linux"`（或 toolchain 传 `-DCMAKE_SYSTEM_NAME=Linux`），使 `if(UNIX)` 成立。OHOS 为 POSIX 系，Linux 平台语义完全兼容 |
| 2 | configure 报 `Could not find Qt5LinguistTools` | `ecm_install_po_files_as_qm(poqm)` 需要 Qt5LinguistTools，但 qt5-qtbase 包未含、制品仓无 qt5-linguisttools | CMakeLists 注释掉 `ecm_install_po_files_as_qm(poqm)`（同 KF6 kcoreaddons 0001 补丁思路） |
| 3 | configure 报 `Qt5DBus missing` | USE_DBUS=OFF 时 find_package(QtDBus) 仅置 HAVE_QTDBUS，DBus 源由 `if(HAVE_QTDBUS)` 守卫，无碍 | 保持 USE_DBUS=OFF 即可；`Qt5Widgets not found, examples not built` 为可选 |
| 4 | Qt5CoreConfigExtras 引用 `../b/mkspecs/linux-clang` 文件不存在 | qtbase 包内 mkspec 路径问题（attica-kf5 同款 `_prepare_qt_mkspec_compat`） | 复制 `p/mkspecs` 到 `../b/mkspecs`（含 common/ 子目录，需整目录拷贝不含只 linux-clang） |

## 验证结果（探索性 ctest）

ctest 34 项：**91% passed，3 failed**，失败项均为 OHOS 平台能力限制（非代码缺陷）：
- `kusertest` — user/group 数据库不可用（getpwuid/getgrgid 返回空），`user.isValid()` FALSE
- `kdirwatch_stat_unittest` / `kdirwatch_qfswatch_unittest` — `testHardlinkChange()` 中 `::link()`（硬链接）失败、inotify_add_watch 权限受限

> 与 KF6 kcoreaddons 6.26.0 知识一致：OHOS 上 user/group 数据库和硬链接不可用，需在上游 autotest 中做运行时 skip。本配方 conan build() 不内嵌 ctest（若内嵌，上述 3 项 OHOS 平台限制会使 conan create 失败）；上游 34 项 ctest 已在探索性/真机阶段实际运行，结果如实记录于 reports/test-report.md，test_package/MANIFEST.yml 的 upstream_test_in_build 如实声明为 false。

## 依赖版本

- qt5-qtbase/5.15.2 （qt5-qtbase 5.15.2，制品仓已发布）
- ecm/6.20.0（ECM，制品仓已发布）
- zlib/1.3.1（qt5-qtbase 传递依赖）

## 注意事项

- 构建系统检测为 CMake；init-build 误判为 autotools，conan-init 需指定 cmake 模板。
- 平台符号：`#ifdef __OHOS__` 在源码/patches 中禁用（R8），平台差异一律用 CMake 层（CMAKE_SYSTEM_NAME=Linux、KF_IGNORE_PLATFORM_CHECK）处理。
- 产物 `libKF5CoreAddons.so` + 头文件 + KF5CoreAddonsConfig.cmake（cmake_find_mode=none 参考 attica-kf5）。
---

**编译结束**: 2026-09-18 12:33
**最终状态**: built
