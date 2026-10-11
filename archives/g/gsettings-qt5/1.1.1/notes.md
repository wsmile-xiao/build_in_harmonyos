# gsettings-qt5 1.1.1 适配笔记（HarmonyOS PC / arm64）

## 上游信息

- 上游仓库：https://gitlab.com/ubports/development/core/gsettings-qt
- 上游维护方：UBports / Debian UBports Team
- 许可证：LGPL-3.0-only
- 源 tarball：`gsettings-qt-v1.1.1.tar.gz`
  （`https://gitlab.com/ubports/development/core/gsettings-qt/-/archive/v1.1.1/gsettings-qt-v1.1.1.tar.gz`，
  sha256 `636cff4336b8729f805bd1cb6904a4c140b69d8a8063949c61f39f8431fe9d00`，本地实测一致）
- 上游构建模式：`CMakeLists.txt` 的 `option(ENABLE_QT6 "Enable Qt6 build" OFF)` ——
  **上游默认即 Qt5**；Qt6 变体需显式 `-DENABLE_QT6=ON`。

### 与 archives/g/gsettings-qt/1.1.1（Qt6 变体）的关系

| | gsettings-qt/1.1.1（已发布） | gsettings-qt5/1.1.1（本包） |
|---|---|---|
| 上游 tarball | 同一份（同 sha256） | 同一份 |
| 构建模式 | `-DENABLE_QT6=ON` | `ENABLE_QT6=OFF`（上游默认） |
| 库名 | `libgsettings-qt6.so`（SOVERSION 1） | `libgsettings-qt.so`（SOVERSION 1） |
| pkg-config | `gsettings-qt6.pc` | `gsettings-qt.pc` |
| 头文件目录 | `include/<triplet>/qt6/QGSettings/` | `include/<triplet>/qt5/QGSettings/` |
| Qt 依赖 | qtbase/6.11.1 + qtdeclarative/6.11.1 | qt5-qtbase/5.15.2.2 + qt5-qtdeclarative/5.15.2 |

**为什么需要本包**：Qt6 构建的 `libgsettings-qt6.so` 无法被 Qt5 程序链接
（QObject/QVariant/信号槽的 ABI 与 `Qt5::Core` 不兼容）。下游
`kylin-calendar/5.0.0.0` 是 Qt5 程序：

```
CMakeLists.txt:55   pkg_check_modules(Gsetting REQUIRED gsettings-qt)
CMakeLists.txt:58   link_libraries(gsettings-qt.so)
colorarea.cpp:22 / colorarea.h:25 / custommessagebox.cpp:26 / customscrollarea.cpp:21 /
frmlunarcalendarwidget.cpp:92,94,97,99   #include <QGSettings> + QGSettings::isSchemaInstalled /
                                         new QGSettings(...) / ->get(...) / connect(...,&QGSettings::changed,...)
```

故按上游默认方式构建 **Qt5** 链，产出 `libgsettings-qt.so` + `gsettings-qt.pc`。

## 编译环境与构建系统

- 构建系统：**CMake**（上游 `CMakeLists.txt`，`project(gsettings-qt VERSION 1.1.1 LANGUAGES CXX)`）
- 编译日期：2026-10-08
- 编译器：clang/clang++ 15.0.4（OHOS SDK，aarch64-linux-ohos）
- 状态：**built**（conan create 通过 + 上游 16/16 断言通过 + test_package 13/13 通过）
- 构建方式（与 CI `ci/conan/build_and_test.sh` 同参数）：

```bash
conan create archives/g/gsettings-qt5/1.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build="gsettings-qt5/*"
```

配方内流程：`cmake configure(-DENABLE_QT6=OFF -DBUILD_TESTING=ON)` → `build` →
签名构建树 ELF → `ctest` → `install` → package 内再签名。

## 三段式依赖结论

### 【强制第三方依赖】

以下依赖必须由制品仓提供对应二进制（**均已发布**，W0 实测 `conan download --only-recipe` rc=0）：

| 依赖 | 版本 | 角色 | 用途 |
|---|---|---|---|
| qt5-qtbase | 5.15.2.2 | host（transitive_headers/libs） | `Qt5::Core`（`qgsettings.h` 公开暴露 `QObject`/`QVariant`/`QStringList`）+ `Qt5::Test`（上游 cpptest）+ `bin/moc`（上游 `CMAKE_AUTOMOC ON`） |
| qt5-qtdeclarative | 5.15.2 | host（transitive_libs） | `Qt5::Qml`（QML 插件 `GSettingsQmlPlugin`）+ `Qt5QuickTest`（上游 qmltest）+ `qml/` 运行期模块 |
| glib | 2.88.0 | host（transitive_libs） | `gio-2.0`（源码 `<gio/gio.h>`；`gsettings-qt.pc` 声明 `Requires: gio-2.0`）+ `bin/glib-compile-schemas`（测试 schema） |
| pkgconf | 3.0.6 | tool_requires | `find_package(PkgConfig REQUIRED)`，提供 `pkg-config` 别名 |
| cmake-extras | 1.9 | tool_requires | `QmlPlugins.cmake` / `add_qmlplugin`（纯 CMake 模块数据包，构建期使用，不进消费者依赖链） |

**glib 版本必须是 2.88.0（不可用 2.88.3.1）**：`qt5-qtbase/5.15.2.2` 精确依赖
`zlib/1.3.1`，而 `glib/2.88.3.x` 依赖 `zlib/1.3.2` —— 二者在依赖图里硬冲突
（`ERROR: Version conflict: Conflict between zlib/1.3.2 and zlib/1.3.1`）。
`glib/2.88.0` 同样依赖 `zlib/1.3.1`，整条链的 `package_id` 与制品仓既有二进制一致，
`conan install` 全部命中 Cache（无源码重建）。

### 【不需要单独适配】

- **zlib/1.3.1**：已有制品仓二进制，但其 `libz.a` 是 `./configure --static`
  （无 `-fPIC`）产物，链进共享库会报 `R_AARCH64 relocation ... recompile with -fPIC`
  （E541）。OHOS 的 Qt5 链本身就是链接**系统** `libz.so`（`libQt5Core.so` 带
  `DT_NEEDED libz.so`），故本配方沿用同一做法（详见「适配要点」§2），**无需**为
  zlib 出包，也不需要 `override` 改版本（override 会改变 `qt5-qtbase` 的
  `package_id` → 触发 Qt5 base 源码重建）。
- **dbus/1.14.10、expat/2.8.2、pcre2/10.45、libffi/3.5.2、proxy-libintl/0.5**：
  `qt5-qtbase` / `glib` 的传递依赖，制品仓已发布，本包不直接引用、无需额外处理。
- **glib 的静态传递库**（libgio-2.0.a / libgobject-2.0.a / libgmodule-2.0.a /
  libglib-2.0.a / libintl.a / libffi.a / libpcre2-*.a）：由 `PkgConfig::Gio`
  自动带入链接（实测均可链入共享库，仅 zlib 例外），无需单独声明。

### 【下一步唯一待处理依赖】

**无。** 本条 Qt5 GSettings 消费路径已闭合：下游 `kylin-calendar/5.0.0.0` 所需的
`pkg_check_modules(gsettings-qt)` → `gsettings-qt.pc`、`#include <QGSettings>` →
`include/<triplet>/qt5/QGSettings/`、`link_libraries(gsettings-qt.so)` →
`lib/libgsettings-qt.so`（`DT_SONAME=libgsettings-qt.so.1`）三者均已由本包提供，
且 Qt5 依赖链（qt5-qtbase / qt5-qtdeclarative / glib）全部为制品仓已发布二进制。

> 运行期 GSettings schema（如 `org.kylin.calendar.plugin`）由应用自身或其
> schema 包安装，不属于本库的构建/链接依赖；本包不引入该运行期依赖。

## R51 上游测试三步法

### 第一步：清点上游测试

| ctest 用例 | 上游文件 | 注册方式 | 用例数（实测） |
|---|---|---|---|
| `cpptest` | `tests/cpptest.cpp`（QtTest） | `tests/CMakeLists.txt` `add_test(NAME cpptest ...)` | 7（initTestCase + 5 测试槽 + cleanupTestCase） |
| `qmltest` | `tests/test.cpp` + `tests/tst_GSettings.qml`（QtQuickTest） | `tests/CMakeLists.txt` `add_test(NAME qmltest ...)` | 9（initTestCase + 7 QML 测试函数 + cleanupTestCase） |

清点依据：`tests/CMakeLists.txt` 两个 `add_test`；`cpptest.cpp` 的
`private slots:` 5 个测试槽；`tst_GSettings.qml` 的 7 个 `function test_*`。

### 第二步：真实运行

配方 `build()` 内真实执行上游 ctest（不是声明式占位）：

```
ctest --test-dir <build> --output-on-failure --parallel 1
```

逐用例结果（明细见 `reports/upstream-tests.log`）：

| 用例 | 结果 | 通过/失败/跳过 |
|---|---|---|
| `cpptest` | **Passed** | 7 通过 / 0 失败 / 0 跳过 |
| `qmltest` | **Passed** | 9 通过 / 0 失败 / 0 跳过 |

为让 qmltest 在 OHOS Qt5 链下可运行，配方做了两处**测试环境**适配（均不改上游文件、
不改依赖包内容）：
1. 把 `qt5-qtdeclarative` 包的 `qml/` 模块软链进构建树（Qt5 的 QML 引擎只读
   `QML2_IMPORT_PATH`，而上游 `set_tests_properties` 把它固定为 `${CMAKE_BINARY_DIR}`）；
   其中 `QtTest` 模块需从其 `src/imports/testlib/` 补齐 `TestCase.qml` /
   `SignalSpy.qml` / `testlogger.js` / `plugins.qmltypes`（该包 install 未搬运）。
2. 注入 `QV4_FORCE_INTERPRETER=1`：OHOS 受限内核拒绝 `mprotect(PROT_EXEC)`，QML V4
   基线 JIT 会 `SegFault`（`mprotect failed in ExecutableAllocator::makeExecutable`），
   上游为该类平台预留了此开关。

### 第三步：PR 回填实测

- 上游用例：**16 / 16 通过，通过率 100%**（0 失败、0 跳过，全量执行无跳过项）
- 命令：`ctest --test-dir <build> --output-on-failure --parallel 1`
- 证据：`reports/upstream-tests.log`（注：本仓库 `.gitignore:96` 忽略 `reports/`，
  故原始日志仅存本地；下方摘录原文以便评审核对）
- test_package：13 项断言全部 PASS（`OK: 0 failure(s)`）

原始输出摘录（`ctest -V`）：

```
1: PASS   : TestGSettingQt::initTestCase()
1: PASS   : TestGSettingQt::test_deferredDelete()
1: PASS   : TestGSettingQt::test_get_set_reset()
1: PASS   : TestGSettingQt::test_default_value()
1: PASS   : TestGSettingQt::test_keys()
1: PASS   : TestGSettingQt::test_changed()
1: PASS   : TestGSettingQt::cleanupTestCase()
1: Totals: 7 passed, 0 failed, 0 skipped, 0 blacklisted, 2ms
1/2 Test #1: cpptest ..........................   Passed    0.03 sec

2: PASS   : GSettings::initTestCase()
2: PASS   : GSettings::test_aaa_read_defaults()
2: PASS   : GSettings::test_changed()
2: PASS   : GSettings::test_choices()
2: PASS   : GSettings::test_invalid_schema()
2: PASS   : GSettings::test_non_existing()
2: PASS   : GSettings::test_reset()
2: (process:62808): GLib-GIO-WARNING **: g_settings_set_value: value for key 'test-enum' in schema 'com.ubports.gsettings.Test' is outside of valid range
2: QWARN  : GSettings::test_write() unable to set key 'testEnum' to value 'notanumber'
2: PASS   : GSettings::test_write()
2: PASS   : GSettings::cleanupTestCase()
2: Totals: 9 passed, 0 failed, 0 skipped, 0 blacklisted, 6ms
2/2 Test #2: qmltest ..........................   Passed    0.19 sec

100% tests passed, 0 tests failed out of 2
Total Test time (real) =   0.22 sec
```

（`test_write` 中的 `GLib-GIO-WARNING` / `QWARN` 是上游「写入越界枚举值应被拒绝」
负向断言触发的预期输出，随后 PASS。）

### W3 本地 CI 模拟（finish 内，阻塞门禁）

```
conan create 通过 → .ci-result.json: {"exit_code": 0, "step": "W3_local_ci"}
```

> 注：本地 `finish` 的 W3 日志（`reports/w3-local-ci.log`）与 `.ci-result.json`
> 均为框架产物。本工作区 HEAD（`feat/kylin-calendar-5.0.0.0`）与 `origin/main`
> 相差约 2.8 万文件，且分支上存在**其他软件**遗留的 `.staging-verified` 状态文件
> （`archives/l/libbfio/20260623/`、`archives/t/thc/3.8/`），使 `junk_check.sh`
> 落到 incremental 全分支模式后误报 JC1/JC5/JC6。CI 侧用 `pr.diff` 走 prdiff
> 模式（只检查本 PR 文件清单），故本次以 `JUNK_PR_DIFF`（框架自带的同一入口）
> 提供本 PR 的真实文件清单（`git status --untracked-files=all archives/g/gsettings-qt5`
> 的 12 个非忽略文件）复现 CI 口径，`JC_RESULT=pass`。与本包无关的仓库级噪音
> 未做任何改动。

## 适配要点

1. **Qt5 分支**：`-DENABLE_QT6=OFF`（上游默认）→ 库名 `gsettings-qt`、`.pc` 名
   `gsettings-qt.pc`、头文件装到 `include/<triplet>/qt5/QGSettings/`。
2. **系统 libz.so 替代非 PIC 静态 zlib**：制品仓 `zlib/1.3.1` 的 `libz.a` 无 `-fPIC`，
   链进共享库必然报 `R_AARCH64_ADR_PREL_PG_HI21 ... recompile with -fPIC`。OHOS 的
   Qt5 链本身即链接系统 `libz.so`（`libQt5Core.so` 的 `DT_NEEDED` 含 `libz.so`），
   本配方三处对齐：
   - `generate()` 把 `PkgConfigDeps` 生成的 `zlib.pc` 的 `Libs` 由
     `-L"${libdir}" -lz` 改为 `-lz`；
   - 从 `conan_toolchain.cmake` 的 `CMAKE_LIBRARY_PATH` 里移除 zlib 包 libdir
     （否则 CMake 的 `FindPkgConfig` 会用 `find_library()` 把 `-lz` 解析回 Conan 的 `libz.a`）；
   - Qt5 bridge 里置空 `zlib::zlib` 目标并 `set(zlib_FOUND TRUE)`，避免
     `Qt5::Core` 注入静态 `libz.a`。
   结果：`libgsettings-qt.so` 带 `DT_NEEDED libz.so`，与 `libQt5Core.so` 一致；
   运行期 `cpptest`/`qmltest`/test_package 均正常。
3. **Qt5 umbrella CMake bridge**：上游 `find_package(QT NAMES Qt5 REQUIRED COMPONENTS Core Qml)`
   在本制品仓的 Qt5 拆包下会「成功但无 `Qt5::Qml` 目标」，且 CMakeDeps 的
   `Qt5Config.cmake` 既不提供 AUTOMOC 所需的 moc 目标 / Qt 版本变量，也不提供
   上游链接用的无版本前缀 `Qt::Core`/`Qt::Qml`/`Qt::Test`/`Qt::QuickTest`。`generate()`
   把 generators 里的 `Qt5Config.cmake` 改名为 `Qt5ConanBaseConfig.cmake`，写入
   自研 bridge：先置空 zlib、include 基座配置，再补 moc 工具链、`Qml`/`QuickTest`
   分派、`Qt::<Module>` 别名。
4. **qmlplugindump 可选化（补丁 0001）**：OHOS 的 Qt5 链没有 `qmlplugindump` 宿主
   工具（`qt5-qtdeclarative` 包不含 `bin/`），而上游 `GSettings/CMakeLists.txt`
   以 `find_program(... REQUIRED)` 查找、`cmake-extras` 的 `QmlPluginsConfig.cmake`
   在其缺失时 `FATAL_ERROR`。补丁把该查找改为可选：缺失时提供占位 imported target，
   并跳过（可选的）`plugins.qmltypes` 元数据生成；**QML 插件本体照常编译安装**。
5. **构建期工具注入**：`bin/moc`（qt5-qtbase）、`bin/glib-compile-schemas`（glib）
   经 `PATH` 注入；测试可执行文件的 Qt5 运行库经 `LD_LIBRARY_PATH` 补齐；
   `PkgConfigDeps` 生成的 `.pc` 经 `PKG_CONFIG_PATH` 注入。
6. **平台呈现为 Linux**：CMake 无 `Platform/HarmonyOS.cmake`，本工程只用标准平台
   规则，故 (`CMAKE_SYSTEM_NAME`, `CMAKE_HOST_SYSTEM_NAME`) = Linux，OHOS clang 驱动
   仍生成 aarch64-linux-ohos 目标（与 `qt5-qtbase` 配方同源处理）。
7. **OHOS ELF 签名**：构建树内的测试可执行文件 / QML 插件在运行前、安装后的 `.so`
   在打包后，均用 `binary-sign-tool -selfSign 1` 自签名。
8. **网络**：无需现场下载（仅 `source()` 取官方 tarball）。

## 源码修改

仅一个补丁：`patches/0001-ohos-optional-qmlplugindump.patch`（`GSettings/CMakeLists.txt`，
+12/-2 行，见 `conandata.yml` 的 `patch_description`）。其余适配全部在配方侧
（构建环境注入 / CMake 配置桥接 / 依赖声明 / 安装布局识别）解决。补丁不含任何
平台宏（无 `__OHOS__`）。

## 依赖版本

| 依赖 | 版本 | 类型 | 用途 |
|---|---|---|---|
| qt5-qtbase | 5.15.2.2 | host | `Qt5::Core`、`Qt5::Test`、`bin/moc` |
| qt5-qtdeclarative | 5.15.2 | host | `Qt5::Qml`、`Qt5QuickTest`、`qml/` 模块 |
| glib | 2.88.0 | host | `gio-2.0`、`glib-2.0`、`bin/glib-compile-schemas` |
| pkgconf | 3.0.6 | tool | `find_package(PkgConfig REQUIRED)` |
| cmake-extras | 1.9 | tool | `QmlPlugins.cmake` / `add_qmlplugin` |

## 验证结果

```bash
# W0：依赖可消费（实测 rc=0）
conan download qt5-qtbase/5.15.2.2 qt5-qtdeclarative/5.15.2 glib/2.88.0 \
    pkgconf/3.0.6 cmake-extras/1.9 -r=ohpcd --only-recipe
# → 全部 rc=0

# 本地构建 + 上游测试 + test_package（W3，CI 同参数）
conan create archives/g/gsettings-qt5/1.1.1 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing --build="gsettings-qt5/*"
# → exit 0
#   上游 ctest: 100% tests passed, 0 tests failed out of 2（16/16 断言通过）
#   test_package: 13 项断言全部 PASS（OK: 0 failure(s)）
```

## 交付物

| 文件 | 说明 |
|---|---|
| `lib/libgsettings-qt.so.1.0.0`（+ `.so.1`、`.so`） | 库本体（SOVERSION 1，`DT_SONAME=libgsettings-qt.so.1`，已签名） |
| `include/aarch64-linux-ohos/qt5/QGSettings/{qgsettings.h,QGSettings}` | 公开头文件与转发头 |
| `lib/pkgconfig/gsettings-qt.pc` | pkg-config 元数据（`Name: GSettingsQt`，`Requires: gio-2.0`，`Libs: -lgsettings-qt`，`Cflags: -I${includedir}` 指向 `.../qt5/QGSettings`） |
| `lib/qt5/qml/GSettings/{qmldir,libGSettingsQmlPlugin.so}` | QML 模块 GSettings 1.1 |

## 注意事项

- 纯库包（无命令行工具）→ **不需要** `commands.json`（R38 仅 CLI 工具适用）。
- `.pc` 的 `Requires` 只声明 `gio-2.0`（上游行为）：Qt5 的 `Qt5Core` 需由消费方
  自行 `find_package(Qt5 COMPONENTS Core)` / `pkg_check_modules` 提供，
  与下游 kylin-calendar 的现有链接方式一致，本包未改动上游 `.pc` 语义。
- QML 模块的 `plugins.qmltypes` 元数据在 OHOS Qt5 链下无法生成（缺 `qmlplugindump`），
  属可选开发期元数据，不影响插件运行（`qmldir` + `.so` 均已提供）。
- `libgsettings-qt.so` 采用静态吸收 glib / 动态依赖系统 `libz.so` 的组合；
  在 OHOS 上 `libz.so` 为系统库，运行期可用（与 `libQt5Core.so` 一致）。
- 软链接使用 `os.symlink`（先判断 `os.path.lexists`），规避 HMDFS 下 `ln -sf`
  覆盖受限的问题。

---

### 对话 #1 — 首次适配（2026-10-08）

- **目标**：为 Qt5 消费者（kylin-calendar）提供 QGSettings 的 Qt5 conan 包
  （独立包名 `gsettings-qt5`，不与已发布的 Qt6 变体 `gsettings-qt/1.1.1` 冲突）。
- **前置**：`conan download --only-recipe` 验证 5 个直接依赖可消费（rc=0）；
  `conan list "gsettings-qt5/*" -r=ohpcd` 确认制品仓无同名包（版本 1.1.1 可用）。
- **执行链**：源码下载/校验（sha256 与 Qt6 变体一致）→ 读上游 `CMakeLists.txt`
  确认 Qt5 为默认分支 → 编写 conanfile.py（Qt5 依赖链 + CMake bridge + 系统 libz.so）
  → 补丁 0001 → `conan create` 迭代 5 次 → 上游 ctest 2/2（16/16 断言）→
  test_package 13/13。
- **失败与修复**：
  1. `ERROR: Version conflict: Conflict between zlib/1.3.2 and zlib/1.3.1`
     → 根因：`glib/2.88.3.1` 依赖 `zlib/1.3.2`，`qt5-qtbase/5.15.2.2` 精确依赖 `zlib/1.3.1`；
       修复：改用 `glib/2.88.0`（同为 `zlib/1.3.1`，全链命中 Cache）。
      （试过 `zlib/1.3.x override=True`，实测会改变 `qt5-qtbase` 的 `package_id`
       → "Main binary package missing" → 需重建 Qt5 base，故不采用。）
  2. `ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 ... 'z_errmsg'; recompile with -fPIC`
     → 根因：Conan `zlib/1.3.1` 为非 PIC 静态 `libz.a`（E541）；`gio` 静态库引用 zlib 符号。
       修复：改用系统 `libz.so`（三处处理，见「适配要点」§2）。
  3. `find_package(QT NAMES Qt5 REQUIRED COMPONENTS Core Qml)` 后无 `Qt5::Qml` 目标、
     `Qt::Core` 缺失、`AUTOMOC` 未生效（"No valid Qt version found for target"）
     → 根因：Qt5 配置在本制品仓被拆包且 CMakeDeps 配置缺上述内容。
       修复：自研 Qt5 umbrella bridge（见「适配要点」§3）。
  4. configure 阶段 `Could not locate qmlplugindump` → 根因：OHOS Qt5 链无该宿主工具。
     修复：补丁 0001 将其改为可选。
  5. `qmltest` 失败 `module "QtTest" is not installed` → `Type TestCase unavailable`
     → `SegFault`（`mprotect failed in ExecutableAllocator::makeExecutable`）
     → 根因与修复见「R51 上游测试三步法」第二步（QML 模块软链 + QtTest 模块补齐 +
       `QV4_FORCE_INTERPRETER=1`）。
- **结果**：上游 16/16 断言通过；test_package 13/13 通过；`conan create` exit 0。
- **未做（按要求停止）**：commit / push / Issue / PR / 上传制品 / 远端 Review。
---

**编译结束**: 2026-10-08 21:29
**最终状态**: built
