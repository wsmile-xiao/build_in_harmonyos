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

---

## 5.116.0.1 — 安装期重链破坏 .codesign

R37 版本后缀修订。`5.116.0` 已发布，不能覆盖，故行为修复升为 `5.116.0.1`。

**症状**：制品在运行时无法加载，而构建树里的同一份库可以：

```
Error loading shared library .../p/lib/libKF5CoreAddons.so.5.116.0: Permission denied
```

**根因**：配方为保住 KDE 的 `if(UNIX)` 源文件选择而显式设了
`CMAKE_SYSTEM_NAME=Linux`，于是加载了完整的 Linux ELF 链接规则。CMake 因此给构建树
目标写入一条 rpath（由所链接库的目录推导），并在 `install` 时把它**重写**为安装树的
值——这是一次真正的重新链接。重链发生在 OHOS 签名之后，`.codesign` 不再匹配，加载器
随即拒绝该文件。两份副本只差 100 字节 `.dynstr`，正是两条 rpath 字符串。

**修复**：`CMAKE_SKIP_RPATH=ON`。构建树与安装树因此一致（都为空），CMake 安装期无事可
改，不再重链，签名保持有效。依赖改用 `LD_LIBRARY_PATH` 定位——OHOS 加载器是认这个变量
的（实测：给一个无 rpath 的构建配上完整闭包的 `LD_LIBRARY_PATH`，它成功加载并运行）。

**验证**：设备重建后，安装副本与构建树副本逐字节一致（`cmp -l` 无差异），两者
`readelf -d` 均无 RPATH/RUNPATH，`ctypes.CDLL` 加载安装副本成功。

**影响面**：所有在运行时从 `package_folder` 加载该库的消费方——包括下游 KF5 库的上游
测试与 test_package 消费者。`5.116.0` 的制品未修复，消费方应显式引用 `5.116.0.1`。

## 5.116.0.1 — 精简版 lsof 没有 +d（上游测试门禁修复）

CI worker 的 PATH 含 `/system/bin`，镜像在那里放了一份**精简版** lsof。它的用法行是
`lsof [-lt] [-p PID...] [FILE...]`，**不实现 +d 目录查询**：把 `+d` 当路径名，
`lsof: Can't stat +d: No such file or directory`，退出码 1、stdout 为空。
`KListOpenFilesJobTest::testOpenFiles()` 因此拿到空 processInfoList，
`!processInfoList.empty()` 断言失败。同一台机器上 `lsof -t <file>`（直接给文件
路径）工作正常——同 uid 进程的 `/proc/<pid>/fd` 可读，所以这不是 /proc 限制。

上游 `klistopenfilesjob_unix.cpp` 只读 stdout、不看退出码，失败因此是静默的：
job 报 NoError、列表为空。修复走 `patches/0002-klistopenfilesjob-unix-lsof-fallback.patch`：
检测到该特征后，把目录查询退回为对**目录直接子项**逐路径查询
（先一次批量；批量被整单拒绝时逐项重试），即 +d 的 depth-1 语义；
认识 +d 的 lsof 永远不会进入回退分支。

**证据**（HarmonyOS PC，2026-10-10，kcore7a9f011a6850f 构建树）：

| 探测/场景 | 结果 |
|---|---|
| `/system/bin/lsof --help` | `usage: lsof [-lt] [-p PID1,PID2,...] [FILE...]` |
| `/system/bin/lsof -t +d <dir>` | rc=1，stdout 空，stderr `Can't stat +d` |
| `/system/bin/lsof -t <file>`（holder 进程持 fd） | rc=0，输出 holder pid |
| `lsof -t f1 f2`（f2 无进程持） | rc=0，只输出 f1 的 pid |
| `lsof -t f1 <不存在>` | rc=1，**整单无输出**（一个坏参数废掉整批 → 逐项重试的依据） |
| 修复前，CI 式 PATH 跑该测试 | 5p/1f/0s，断言与 CI 日志逐字一致（行 81） |
| 修复后，CI 式 PATH 跑该测试 | 6p/0f/0s |
| 修复前/后，farm PATH（无 lsof） | 3p/0f/3s，行为不变（上游 QSKIP） |
| LD_PRELOAD identity_shim 开/关 | 两个环境结果完全一致——shim 与该失败无关 |

配方侧配套（同一次提交）：测试环境 PATH 在存在且未包含时追加 `/system/bin`，
使 farm 验证与 CI 门禁解析到同一份系统工具；lsof 探针改为按测试环境 PATH 解析；
新增 `lsof +d support` 能力探针，让每个日志直接写明本机是否处于该回退工况。
