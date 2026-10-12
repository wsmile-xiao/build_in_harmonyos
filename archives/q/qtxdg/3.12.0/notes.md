# qtxdg (libqtxdg) 3.12.0 适配笔记

## 上游信息

| 项 | 值 |
|----|----|
| 软件 | qtxdg（上游名 libqtxdg，CMake 包名 `Qt5Xdg`） |
| 上游版本 | 3.12.0（3.x 系列为 Qt5 实现；4.x 才是 Qt6） |
| 上游仓库 | https://github.com/lxqt/libqtxdg |
| 源码 URL | https://github.com/lxqt/libqtxdg/archive/refs/tags/3.12.0.tar.gz |
| sha256 | `084e5fe7b4087d95657be7b5be3668e98bf14c2ba3b150205ebd819508774d45` |
| 许可证 | LGPL-2.1-or-later |
| 语言预检 (R47) | C/C++（`src/` 全部为 .cpp/.h；CMake 构建）——匹配任务语言 cpp |

> 版本选择：kylin-calendar/5.0.0.0 的 `CMakeLists.txt:30` 需要
> `find_package(Qt5Xdg ${QTXDG_MINIMUM_VERSION} REQUIRED)`，`QTXDG_MINIMUM_VERSION="3.3.1"`。
> libqtxdg **3.x 才是 Qt5** 版本（4.x 为 Qt6），3.12.0 满足 >= 3.3.1。
> 制品仓实测无 `qtxdg`/`libqtxdg` 任何版本，故本次为首次适配，版本号取上游 `3.12.0`（无 `.N` 后缀）。

## 构建系统

CMake（`cmake_minimum_required(3.1)`）。上游 `CMakeLists.txt` 的配置期硬依赖：

```
find_package(lxqt-build-tools 0.13.0 REQUIRED)     # CMake 宏/FindGLIB 来源
find_package(Qt5 5.15.0 CONFIG REQUIRED Widgets Svg Xml DBus)
find_package(GLIB 2.41.0 REQUIRED COMPONENTS gobject gio gio-unix)
find_package(XTerm)                                 # 可选，非 REQUIRED
```

## W0 依赖结论

**【强制第三方依赖】**
- `qt5-qtbase/5.15.2.2`（Qt5 Core/Gui/Widgets/Xml/DBus，Qt5DBus 供 XdgMimeApps/D-Bus 激活）
- `qt5-qtsvgv/5.15.2.2`（Qt5Svg，供 xdgiconloader 链接 `Qt5::Svg`）
- `glib/2.88.0`（`xdgmimeappsglibbackend.cpp` 的 GLib/GIO 后端；`find_package(GLIB REQUIRED)`）
- `lxqt-build-tools/0.13.0`（上游 configure 期 `find_package(lxqt-build-tools REQUIRED)` 的宏来源）

**【不需要单独适配】**
- `qt5-qtsvgv/5.15.2.2`、`glib/2.88.0` 制品仓均已发布（`conan download --only-recipe` rc=0），直接消费。
- `pcre2/10.45`、`libffi/3.5.2`、`proxy-libintl/0.5`、`zlib/1.3.1`、`dbus/1.14.10`、`expat/2.8.2` 均为上述包的传递依赖，制品仓已发布。
- `XTerm` 为可选依赖（上游 `find_package(XTerm)` 无 REQUIRED），OHOS 上找不到即跳过，不影响构建。

**【下一步唯一待处理依赖】**
- `lxqt-build-tools/0.13.0`：**制品仓缺失**（`conan list 'lxqt-build-tools/*' -r=ohpcd` → Found 0；`conan download lxqt-build-tools/0.13.0 -r=ohpcd --only-recipe` → Recipe not found）。
  它是纯 CMake 宏包（`LXQtConfigVars` / `LXQtCreatePkgConfigFile` / `LXQtCreatePortableHeaders` / `LXQtCompilerSettings` / `FindGLIB.cmake` 等）。
  由于单个配方 PR 只能改动自身归档目录（W2/R36 不捎带），本配方**自带其官方上游源码**
  （`https://github.com/lxqt/lxqt-build-tools/releases/download/0.13.0/lxqt-build-tools-0.13.0.tar.xz`，
  sha256 `fd3c199d0d7c61f23040a45ead57cc9a4f888af5995371f6b0ce1fa902eb59ce`），
  在 `build()` 内先配置/安装到 `build_folder/lxqt-build-tools-prefix`，再配置 libqtxdg。
  后续如将该包单独适配发布，可去掉本配方内的自带逻辑。

## 依赖版本（本次实测解析）

```
qt5-qtbase/5.15.2.2, qt5-qtsvgv/5.15.2.2, glib/2.88.0,
pcre2/10.45, libffi/3.5.2, proxy-libintl/0.5, zlib/1.3.1,
dbus/1.14.10, expat/2.8.2
profile: ci/conan/profiles/ohos-aarch64 (os=OHOS/6.0 arch=armv8 clang15 libc++ cppstd=17 Release)
```

## 适配要点与踩坑

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `find_package(lxqt-build-tools REQUIRED)` 失败 | 制品仓无此包，单个配方不能捎带适配依赖 | 配方自带官方 0.13.0 源码；`build()` 内 `cmake -S ... -B ...` 配置 + `cmake --install` 到 `build_folder/lxqt-build-tools-prefix`，其 `lxqt-build-tools-config.cmake` 会把 modules/find-modules 追加进 `CMAKE_MODULE_PATH` |
| 2 | lxqt-build-tools 配置期 `find_package(Qt5Core REQUIRED)` 失败 | 它是无条件调用；且 qt5-qtbase 包内**原生 Qt5 配置不可重定位**（`*ConfigExtrasMkspecDir.cmake` 烘焙构建目录 `.../b//mkspecs/linux-clang`，`_qt5_Core_check_file_exists` 直接 FATAL） | 为该步骤提供 `Qt5CoreConfig.cmake` 桩（只需 `Qt5Core_FOUND`），并传 `-DLXQT_ETC_XDG_DIR=/etc/xdg` 绕过 qmake 查询 |
| 3 | `find_package(Qt5 ... Widgets Svg Xml DBus)` 无法用原生配置 | 同上：原生 Qt5 umbrella 配置不可重定位 | 打补丁改为消费 Conan CMakeDeps 目标：`find_package(Qt5 CONFIG REQUIRED)`（qt5-qtbase 包级 `cmake_file_name=Qt5`）+ `find_package(qt5-qtsvgv CONFIG REQUIRED)`（提供 `Qt5::Svg`） |
| 4 | `QT5_ADD_DBUS_INTERFACE` / `qt5_generate_moc` 未定义、`Qt5Gui_PRIVATE_INCLUDE_DIRS` 为空、`qplatformdefs.h` 找不到 | CMakeDeps 只生成 target，不产出原生 Qt5 的宏与私有头变量 | `generate()` 生成 `qtxdg_qt5_compat.cmake`，经 `CMAKE_PROJECT_INCLUDE` 注入：设置 moc/rcc/qdbusxml2cpp 路径、`Qt5Core/Qt5Gui_PRIVATE_INCLUDE_DIRS`、`include(qt5-qtbase 的 Qt5CoreMacros.cmake / Qt5DBusMacros.cmake)`、并把 `mkspecs/linux-clang` 加入 include（`qplatformdefs.h`） |
| 5 | `find_package(GLIB REQUIRED)` 被 CMakeDeps 的 `glib-config.cmake` 抢占，`GLIB_INCLUDE_DIRS` 为空 | Conan toolchain 设 `CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON`；上游只用**大写** `GLIB_INCLUDE_DIRS/GLIB_LIBRARIES`（仅 FindGLIB 定义） | `deps.set_property("glib", "cmake_find_mode", "none")`，让 module 模式命中 lxqt-build-tools 的 `FindGLIB.cmake`（test_package 的 CMakeDeps 不受影响） |
| 6 | FindGLIB 的 `gio-unix` 组件失败：`No package 'gio-unix-2.0' found` + 缺 `GLIB_GIO_UNIX_INCLUDE_DIR` | glib conan 包不导出 `gio-unix` 组件，PkgConfigDeps 不生成 `gio-unix-2.0.pc` | `generate()` 手写 `gio-unix-2.0.pc`（`Cflags: -I${includedir}`，prefix 指向 glib 包），使 find_path 命中 `include/gio-unix-2.0/gio/gdesktopappinfo.h` |
| 7 | `.so` 链接报 `relocation R_AARCH64_ADR_PREL_PG_HI21 ... z_errmsg ... recompile with -fPIC` | OpenHarmony 的 `zlib/1.3.1` 与 `glib/2.88.0` 都是**非 PIC 静态库**（glib 的 gio 又依赖 zlib） | `Qt5Xdg`/`Qt5XdgIconLoader` 构为 **STATIC**（上游 add_library 写死 SHARED，补丁放开；同 quazip 先例）；图标引擎插件保持 `MODULE`（只在 shim 里把 `zlib::zlib` 置空避免非 PIC zlib 混入模块） |
| 8 | 消费者/test 链接 static `Qt5Xdg` 后 `undefined symbol: ffi_* / g_libintl_* / g_module_* / pcre2_* / inflate*` | 上游链接行只列 `${GLIB_LIBRARIES} ${GLIB_GOBJECT_LIBRARIES} ${GLIB_GIO_LIBRARIES}`，不含 glib 的传递静态归档 | 新增 `${QTXDGX_GLIB_STATIC_DEPS}`（libffi.a / libgmodule-2.0.a / libintl.a / libpcre2-8.a / libz.a，绝对路径由配方从依赖包解析）注入 `Qt5Xdg` 的 PUBLIC 链接接口 |
| 9 | 上游测试 `qtxdg_test` 失败：`test2.allKeys().size() == 4` returned FALSE | 测试硬编码写 `/tmp/test.list`，OHOS `/tmp` 只读（E002） | 补丁 `0004` 改用 `QDir::tempPath()`；并在 `build()` 运行 ctest 时把 `TMPDIR` 指向 build 目录下可写目录 |
| 10 | test_package 编译期 `'QtCore/qglobal.h' file not found` | CMakeDeps 对“非直接依赖”的 qt5-qtbase 不导出 include 目录 | test_package 显式 `self.requires("qt5-qtbase/5.15.2.2")` |

## R51 上游测试三步法

**第 1 步 — 清点上游测试（tests 目录数 + ctest 注册数）**

```
源码包 test/ 目录：
  test/CMakeLists.txt        # qtxdg_add_test(qtxdg_test tst_xdgdirs tst_xdgdesktopfile)
  test/qtxdg_test.cpp/.h
  test/tst_xdgdirs.cpp
  test/tst_xdgdesktopfile.cpp
注册数：ctest -N  →  3 个测试
  #1 qtxdg_test   #2 tst_xdgdirs   #3 tst_xdgdesktopfile
```
清点证据：`test/CMakeLists.txt` 的 `qtxdg_add_test()` 宏注册 3 个可执行文件；
`example/`、`util/` 不注册 ctest。`ctest -N` 实测输出 **3**。

**第 2 步 — 可运行环境实际运行（BUILD_TESTS=ON，真机/CI）**

```
$ ctest --output-on-failure
    Start 1: qtxdg_test
1/3 Test #1: qtxdg_test ............... Passed
    Start 2: tst_xdgdirs
2/3 Test #2: tst_xdgdirs .............. Passed
    Start 3: tst_xdgdesktopfile
3/3 Test #3: tst_xdgdesktopfile ....... Passed
100% tests passed, 0 tests failed out of 3
```

**第 3 步 — 实测结果回填**

| 指标 | 值 |
|------|----|
| 上游注册测试数 N | **3** |
| 实际运行数 N′ | **3** |
| 通过率 | **3/3 = 100%** |
| 未运行的测试及技术原因 | 无（`qtxdg_test` 的 `testDefaultApp/testTextHtml/testMeldComparison` 非 `Q_SLOTS`，上游本身未注册为 ctest 用例） |
| 唯一适配调整 | `qtxdg_test.cpp` 的 `/tmp` → `QDir::tempPath()`（OHOS /tmp 只读）；运行 ctest 时注入可写 `TMPDIR` |

## 源码修改（patches/）

| 补丁 | 内容 |
|------|------|
| `0001-cmake-consume-conan-qt5-and-qtsvg.patch` | `CMakeLists.txt`：`find_package(Qt5 ... Widgets Svg Xml DBus)` → `find_package(Qt5 ... CONFIG REQUIRED)` + `find_package(qt5-qtsvgv CONFIG REQUIRED)` |
| `0002-cmake-build-qtxdg-static-with-glib-static-deps.patch` | `src/qtxdg/CMakeLists.txt`：`add_library(... SHARED)` → `STATIC`；链接行追加 `${QTXDGX_GLIB_STATIC_DEPS}` |
| `0003-cmake-build-iconloader-static.patch` | `src/xdgiconloader/CMakeLists.txt`：`add_library(... SHARED)` → `STATIC` |
| `0004-test-use-portable-temp-dir.patch` | `test/qtxdg_test.cpp`：硬编码 `/tmp` → `QDir::tempPath()`（平台可移植，非平台宏） |

## 验证结果

```bash
# W3：finish 内部 ci/conan/setup.sh + build_and_test.sh（即 conan create 同源门禁）
python3 scripts/ohc-run.py finish qtxdg 3.12.0 built
# → L0a-L0q 质量门禁通过；conan create 成功；.ci-result.json exit_code=0

# build() 内上游测试：ctest 3/3 通过
# test_package：find_package(Qt5Xdg) + 链接 Qt5Xdg + 调用 XdgDirs/XdgDesktopFile API，15/15 断言通过
```

- 打包产物：`lib/libQt5Xdg.a`、`lib/libQt5XdgIconLoader.a`（静态）、`plugins/iconengines/libQt5XdgIconPlugin.so`、头文件、cmake/pkgconfig 配置。
- R26（系统同名库）：`libQt5Xdg.so` / `libQt5XdgIconLoader.so` / `libQt5XdgIconPlugin.so` 均**不存在于** `/lib`、`/lib64`；且已静态，无污染风险。
- R38（命令行工具）：`BUILD_DEV_UTILS=OFF`（上游默认），本包**未打包任何可执行文件**（核对：`util/` 下的 `qtxdg-desktop-file-start`、`qtxdg-iconfinder` 未构建），故软件级目录不需要 `commands.json`。

## 注意事项

- 本包为 **静态库**。下游（如 kylin-calendar）链接 `Qt5Xdg` 时会一并链接 glib 及其传递静态归档；
  由于 glib/zlib 为非 PIC 静态库，下游若自身构建共享库需注意同一约束（可执行程序不受影响）。
- `qt5-qtsvgv`（而非 `qt5-qtsvg`）被选作 Qt5Svg 提供者：`qt5-qtsvg/5.15.2.1` 精确 pin `qt5-qtbase/5.15.2`，
  需 `override=True` 才能升级到 5.15.2.2，而 override 会让 CMakeDeps 丢掉 Qt5 include 目录。
- **CI 临时镜像注入（非本配方内容）**：`ci/conan/build_and_test.sh` 在 W3/CI 运行期会把
  `conandata.yml` 的官方 URL 临时改写为 `gh-proxy.com` 镜像列表（并预下载），退出时由
  `trap _restore_conandata EXIT` 还原。若该脚本被中途杀死（SIGKILL）则 trap 不执行、文件残留镜像 URL。
  本归档提交的 `conandata.yml` 已确认为**官方源单 URL 形式**（R39/PF7）；
  若后续重跑 `finish`/W3 后又出现 `gh-proxy.com`/`ghfast.top`/`file://`，请还原为官方 URL 再提交。

## 对话记录

### 对话 #1

- 读取 SKILL.md 全文（v12.22，1046 行），按 W0–W5 工作流执行。
- W0 依赖检查：核验 qt5-qtbase/5.15.2.2、qt5-qtsvgv/5.15.2.2、glib/2.88.0 均已发布；
  发现 `lxqt-build-tools` 制品仓缺失 → 配方自带官方源码（见 W0 结论）。
- 源码获取：`git ls-remote` 核验 gitee openkylin/libqtxdg 与上游 github lxqt/libqtxdg 的
  `upstream/3.12.0` / tag `3.12.0` 内容一致，采用官方上游 release 源（R39/PF7）。
- 手工打通编译（mode B）：逐步解决 Qt5 配置宏、FindGLIB、非 PIC 静态库等 9 个问题，
  确认 `BUILD_SHARED_LIBS=OFF` 静态构建 + ctest 3/3 通过。
- 固化配方（conanfile.py + conandata.yml + patches/ + test_package/），`conan create` 全绿。
- W3：`ohc-run.py finish qtxdg 3.12.0 built` 产出 `.ci-result.json`。
---

**编译结束**: 2026-10-08 18:37
**最终状态**: built
