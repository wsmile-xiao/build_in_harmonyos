# isoimagewriter 26.04.0 适配笔记

## 编译环境

- 构建系统: cmake（CMake 4.1.2 + ECM 6.26.0）
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos）
- Conan: 2.29.1（OHOS 适配版）
- 状态: built（conan create + test_package 通过）

## 编译步骤

```bash
conan create archives/i/isoimagewriter/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 上游测试清点（R51 三步法）

| 步骤 | 做法 | 结果 |
|------|------|------|
| 1. 清点 | `find . -iname "*test*"`；`grep -rn "enable_testing\|add_test\|add_subdirectory(autotests)" CMakeLists.txt isoimagewriter/CMakeLists.txt` | 0 个测试文件；仅 `find_package(Qt6 ... Test)` 一处；`autotests/` 目录不存在 → **上游 N=0** |
| 2. 运行 | 无上游测试可运行 | **0/0（不适用）** |
| 3. 回填 | 按 R51「上游 N=0 → 适配后必须补增测试」新增 test_package 消费者测试 | 鸿蒙特有测试 1 项（9 断言） |

> 上游把 Qt6 Test 组件写进 `find_package` 只是为了链接 `Qt::Test`，并未注册任何
> CTest 用例（无 `enable_testing()` / `add_test()`）。

## 平台适配

### 1. `CMAKE_SYSTEM_NAME=HarmonyOS` 与上游平台三分支

OHOS 适配版 Conan 的 CMakeToolchain 把 `CMAKE_SYSTEM_NAME` 设为
`HarmonyOS`（CMake 4.1.2 自带 `Platform/OHOS.cmake`，内容等价 Linux）。
上游 `isoimagewriter/CMakeLists.txt` 只识别 `Windows / Linux / FreeBSD`：

```cmake
elseif(CMAKE_SYSTEM_NAME STREQUAL Linux)   # HarmonyOS 落不进这里
    set(isoimagewriter_SRCS ${isoimagewriter_SRCS}
        platform_lin.cpp usbdevicemonitor_lin.cpp externalprogressbar_lin.cpp)
else()
    message("Unsupported Platform " . ${CMAKE_SYSTEM_NAME})   # → 平台源码全部丢失
endif()
```

后果：`platformEnumFlashDevices()` / `ensureElevated()` / `UsbDeviceMonitor`
的全部实现缺失 → 链接期 undefined reference；`.desktop` / `appdata.xml`
也不会安装。

**补丁 0001** 把 `HarmonyOS` 并入三个 Linux 分支（平台源码选择、`KF6::Solid`
+ `Qt::DBus` 链接、desktop/appdata 安装），**不引入任何平台宏**，属 POSIX
兼容写法（同 azure-core-cpp / dfc / fastfetch / egl 的既有模式）。

### 2. Qt 平台宏无需处理

Clang 目标三元组为 `aarch64-linux-ohos`，Qt6 的 `qsystemdetection.h` 由
`defined(__linux__)` 分支定义 `Q_OS_LINUX`，因此 `main.cpp` 的
`#if !defined(Q_OS_WIN32) && !defined(Q_OS_LINUX) ... #error Unsupported platform!`
不会触发，无需为它打补丁。

### 3. Qt6::DBus 需要 `qtbase-sql-dbus` 变体

`platform_lin.cpp` 用 QtDBus 访问 `org.freedesktop.UDisks2`，上游
`find_package(Qt6 ... DBus ...)` 是必需组件。制品仓的 `qtbase/6.11.1` 构建时
`FEATURE_dbus=OFF`（其 notes 明确「DBus ... disabled」），故改用
`qtbase-sql-dbus/6.11.1`（`FEATURE_sql=ON` / `FEATURE_dbus=ON`，actiona 先例）。

> 注意：KF6 框架包的 `requires` 里带的是 `qtbase/6.11.1`，因此依赖图中同时存在
> `qtbase` 与 `qtbase-sql-dbus` 两个同版本 Qt6 副本（actiona 3.11.1 同样如此）。
> 二者源码版本一致、ABI 相同，运行期按 `LD_LIBRARY_PATH` 取其一，实测
> test_package 全部通过。

### 4. Gpgmepp / QGpgmeQt6 为可选依赖

上游：

```cmake
find_package(Gpgmepp ${GPGME_REQUIRED_VERSION} CONFIG)     # 无 REQUIRED
find_package(QGpgmeQt6 ${GPGME_REQUIRED_VERSION} CONFIG)   # 无 REQUIRED
if(QGpgmeQt6_FOUND)
    add_definitions(-D_USE_GPG)
    target_link_libraries(isoimagewriter QGpgmeQt6)
endif()
```

制品仓 `gpgmepp/1.23.2` 未启用 Qt6 binding（无 `libqgpgmeqt6.so`），因此
`QGpgmeQt6_FOUND` 为假，编译的是上游自带的**非 GPG 变体**
（`_USE_GPG` 未定义，`isoverifier.cpp` / `mainwindow.cpp` 的 `#ifdef _USE_GPG`
分支关闭）。这是上游支持的配置组合，**不是 stub**，写盘与写后回读校验主链路
不受影响，仅 ISO 镜像签名校验入口不可用。未为此重建/捎带 gpgmepp 依赖
（避免 R36 捎带依赖，PR 保持单包原子性）。

### 5. KDE/ECM 相关构建变量

| 变量 | 值 | 原因 |
|------|----|------|
| `KF_IGNORE_PLATFORM_CHECK` | `TRUE` | HarmonyOS 不在 KDE 平台清单内 |
| `KF_SKIP_PO_PROCESSING` | `ON` | 顶层 `ki18n_install(po)` 需 msgfmt，构建镜像无 gettext 工具（accessibility 26.04.3 / akonadi 25.12.3 先例，全仓 64 例） |
| `CMAKE_INSTALL_LIBDIR` | `lib` | KDEInstallDirs 默认可能选 lib64 |
| `ECM_MODULE_PATH` | ecm 的 modules/find-modules/kde-modules | CMakeDeps 生成的 `ECMConfig.cmake` 不传递该变量 |
| `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` | `conan_cmakedeps_paths.cmake` | qtbase 与全部 KF6 包用 `cmake_find_mode=none`，CMakeDeps 不会把它们的 `lib/cmake` 加入 `CMAKE_PREFIX_PATH` |

### 6. 构建/安装环境

ECM 6.26 的 `KDEInstallDirs6` 在 configure 阶段会调用 qtbase 的 `qtpaths` 宿主
工具；继承来的 `LD_LIBRARY_PATH` 含无法解析的空白填充项，且
`/data/storage/el1/bundle/libs/arm64` 下的 `libc++_shared.so` 会遮蔽兼容版本，
因此在 build/package 阶段显式前置依赖 `lib` + `bin`（KF6 包把 .so 也装在
`bin/`）、`/system/lib64`、`/system/lib64/platformsdk`、`/system/lib64/ndk`
（kcrash 6.26.0 / kconfig 6.26.0 先例）。

安装后对整个包内 ELF 重新签名（RPATH 改写会令鸿蒙原签名失效，未签名 ELF
不可执行）：`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign`。

### 7. 运行期 E537：KF6 库的相对 / 陈旧绝对 DT_NEEDED

实测发布版 KF6 库存在两类非常规 DT_NEEDED：

| 形态 | 实例 | 处理 |
|------|------|------|
| 相对路径（相对进程 CWD 解析） | `libKF6ConfigGui.so` → `../../bin/libKF6ConfigCore.so`；`libKF6I18nLocaleData.so` → `../../bin/libKF6I18n.so` | test_package 在 `<scratch>/a/b` 下运行，并把该相对路径物化成真实文件 |
| 陈旧绝对路径（原构建机 conan home） | `/storage/Users/currentUser/.cache/conan2/p/<id>/p/lib/libKF6*.so`（5 项，本机不存在） | 按 basename 在依赖包中定位后物化到该绝对路径 |

受影响的 KF6 包（kcrash / kconfig / kcoreaddons / kguiaddons / ki18n 等）均为
已发布二进制，无法在配方内修正，故在 test_package 侧等价修复
（accessibility 26.04.3 / alligator 26.04.0 同款做法）。

**本机沙箱差异**：沙箱把 conan 进程映射到外部 uid（实测 uid=20020178，而文件
属主为 20001006），导致该进程**创建符号链接报 EACCES，但创建普通文件成功**。
故物化实现为「先 symlink，失败回退 `shutil.copy2`」；CI 环境 uid 一致时走
symlink 路径，与既有先例完全一致。

### 8. Conan `run()` 输出流继承 → clang 全量静默编译失败（本轮最大坑）

**现象**：`conan create` 在本机交互 shell 下成功；但由 `build_and_test.sh`（W3）
与 `conan-verify` 的 G2 调用时，**每个编译单元都失败且编译器零输出**：

```
[ 82%] Building CXX object isoimagewriter/CMakeFiles/.../platform_lin.cpp.obj
make[2]: *** [.../platform_lin.cpp.obj] Error 1
...（14 个 .obj 全部 Error 1，没有任何 error:/warning: 行）
make: *** [Makefile:136: all] Error 2
```

**根因**：`ConanFile.run()` 会把 recipe 进程的 stdout/stderr **继承**给子进程
（`conan_run()` 内部 `stdout = stdout or sys.stderr`），此平台下 clang 在该形态
下静默失败，make 只能报 `Error 1`。

**修复（配方内，已落地）**：`_cmake_step()` 把 configure/build/install 三步各自
绑定独立日志文件（`cmake.configure(stdout=log, stderr=log)` 等），失败时回显日志
尾部并抛出带日志路径的异常。修复后 G2 与 W3 均一次通过。

> 先例：`archives/l/libncurses/6.6_p20260516` 的 `_run_ohos_step()`（同一平台、
> 同一现象）。**注意这是配方缺陷而非环境问题**——不要把它当"换个会话重跑"处理。

### 9. 沙箱 uid 映射 → conan test 进程无法创建符号链接

E537 物化 DT_NEEDED 时，本地沙箱把 conan 进程映射到外部 uid（实测
uid=20020178，而文件属主为 20001006）：该进程**创建符号链接报 EACCES，创建普通
文件正常**。故物化实现为「先 `os.symlink`，失败回退 `shutil.copy2`」；CI 环境
uid 一致时走 symlink 路径，与既有先例（alligator / accessibility）一致。

## 依赖版本

- qtbase-sql-dbus/6.11.1（Qt6 Core/Gui/Widgets/Network/DBus/Test/Sql）
- karchive/6.26.0、kcoreaddons/6.26.0、kcrash/6.26.0、ki18n/6.26.0、
  kiconthemes/6.26.0、kwidgetsaddons/6.26.0、solid/6.26.0
- ecm/6.26.0（build tool_requires）
- 传递依赖：dbus/1.14.10、gettext/0.22.5、zstd/1.5.7、expat 2.8.2.1、
  qtsvg 6.11.1、kconfig 6.26.0、kguiaddons 6.26.0、kcolorscheme 6.26.0

## 验证结果

- `conan create`（G2 干净构建 / W3 本地 CI 模拟）通过，`.ci-result.json` exit_code=0
- conan-verify：G1 pass / G2 pass / G3 pass / G4 pass；其 L2 / L4 / L5 三行虽打印
  PASS，但 `reports/conan-verify-report.md` 内为「⏭️ 跳过（无 cache 路径）」，
  即**并未真正执行**（conan-verify 未取到该包 id 的 cache 路径）。L2/L4/L5 的权威
  证据是下方 W3 实测值。
- W3 harness 逐门禁实测：`JC pass / KC pass / G0 pass / L0 pass / L1 pass /
  L1e pass / L5 pass`；两项非 pass 如实记录：
  - `L2_RESULT=skip`（非阻塞）：harness 只用继承环境跑 `bin/isoimagewriter
    --version`。这是 Qt GUI 程序，没有 `QT_QPA_PLATFORM=offscreen` + Qt/KF6 的
    `LD_LIBRARY_PATH`/插件路径时加载不到 QPA 平台插件（加载器 exit 127）。同一
    二进制在 `test_package`（自建运行环境）中**正常执行**，L2 按 harness 设计为
    非阻塞。
  - `L4_RESULT=warn`（非阻塞）：harness 用正则 `(strcpy|sprintf|gets|strcat)\b`
    扫 `patches/`，命中的是 `KF6::IconWidgets` 里的子串 `gets` —— 扫描器**误报**，
    补丁未引入任何危险函数。
- `finish` step [3/10]（`clean_verify.py`）对本包跳过：该工具为 autotools 专用
  （硬编码 `./configure`），本包是 CMake 项目；该步按 SKILL 约定非阻塞，权威构建
  证据由 G2 `conan create` 与 W3 本地 CI 模拟提供。
- 上游测试用例通过率：0/0（不适用，上游无测试；清点证据见上）
- 新增（鸿蒙特有）测试用例通过率：1/1（100%），9 断言全部通过
- test_package 实测输出：`--version` → `isoimagewriter`（Qt 在
  `KAboutData::setApplicationData()` 之前处理 `--version`，故 applicationVersion
  为空，属上游行为）；`--help` → 列出 `--version / --lang / --dir / [File]`

## 产物

- `bin/isoimagewriter`
- `share/applications/org.kde.isoimagewriter.desktop`
- `share/metainfo/org.kde.isoimagewriter.appdata.xml`
- `share/icons/hicolor/scalable/apps/org.kde.isoimagewriter.svg`
- `share/isoimagewriter/{neon,arch,ubuntu}-signing-key.gpg`

## 已知限制

1. ISO 镜像签名校验不可用（上游可选的 QGpgmeQt6 未启用，见第 4 节）；写盘与
   写后回读校验不受影响。
2. 运行期需要可用的 UDisks2（`org.freedesktop.UDisks2`）system bus 与
   KF6::Solid 设备后端才能枚举可移动盘；本包为编译级适配，GUI 交互未在设备端
   实际点击验证（无桌面会话）。
3. `--version` 输出不含版本号（上游在 `KAboutData::setApplicationData()` 之前
   处理选项）；版本由产物内嵌字符串与 aboutData 版本号保证。
---

**编译结束**: 2026-09-23 20:12
**最终状态**: built
