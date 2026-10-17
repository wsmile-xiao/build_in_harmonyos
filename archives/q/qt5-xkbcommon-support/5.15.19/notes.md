# qt5-xkbcommon-support 5.15.19 — HarmonyOS PC 适配说明

## 1. 为什么需要这个包（W0 依赖预检结论）

`kwayland5/5.116.0` 的 `src/client/CMakeLists.txt`（第 277-281 行）在 Qt5 分支下
**无条件**链接 `Qt::XkbCommonSupportPrivate`：

```cmake
if (QT_MAJOR_VERSION EQUAL "5")
    target_link_libraries(KF5WaylandClient
        PRIVATE Qt::XkbCommonSupportPrivate PkgConfig::XKBCommon)
endif()
```

而上游 `CMakeLists.txt` 第 50 行还硬性要求：
`find_package(Qt5XkbCommonSupport REQUIRED) # Needed by Qt5::WaylandClientPrivate`

**实测证据（逐个检查已发布包的包目录）**：`qt/5.15.19.1` 与 `qt5-qtbase/5.15.2.2`
在 configure 阶段都带了 `-no-xkbcommon`（见 `archives/q/qt/5.15.19.1/conanfile.py`
第 416 行），因此两个包的包目录中：

| 检查项 | qt/5.15.19.1 | qt5-qtbase/5.15.2.2 |
|--------|--------------|---------------------|
| `lib/libQt5XkbCommonSupport.a` | 无 | 无 |
| `lib/cmake/Qt5XkbCommonSupport/` | 无 | 无 |
| `mkspecs/modules/qt_lib_xkbcommon_support_private.pri` | 无 | 无 |
| `include/QtXkbCommonSupport/`（仅 syncqt 头骨架） | 无 | 有（无库、无 cmake、无 pri） |

即：**只有头文件骨架，没有可链接的实现**。要让 kwayland5 编译通过，必须补上这个模块。

### 为什么不直接给整棵 Qt 加 `-xkbcommon` 重编

`qt/5.15.19.1` 的 CI 超时预算已经是 10800s（`ci/config/build_timeouts.txt` 第 46 行，
注释写明"664MB 源码下载 + 全量 qtbase 编译，本地实测 45-60 分钟"）。为了一个模块翻一个
开关就整体重编 Qt，等于每次 CI 多烧 1 小时预算，且会让 `qt/5.15.19.1` 的所有下游包
cache key 失效重编。因此采用**模块拆分包**方式，与本仓库既有先例一致
（registry 已有 `qtbase-gui/6.11.1`、`qtbase-sql-dbus/6.11.1` 这类 Qt 模块拆分包）。

## 2. 源码与构建系统

- 源码：`qtbase-everywhere-opensource-src-5.15.19.tar.xz`（官方 qtbase 子模块归档）
- 官方 URL：`https://download.qt.io/archive/qt/5.15/5.15.19/submodules/qtbase-everywhere-opensource-src-5.15.19.tar.xz`
- SHA256：`51e91c73abacab81e64efd01bf95794e79c0e605ad80947a024769f0dd620a32`
  （自官方 `.sha256` 同目录文件取得，并实测下载件逐字节一致）
- 大小：51,588,440 字节（对比 qt-everywhere 单包 664 MB —— 只取本模块所需的那一棵树）
- 构建系统：custom（直接调用 profile 提供的 clang++ / ar 编译两个 TU，不走 qmake/cmake）

选择子模块归档而非 qt-everywhere：本包只需要 `qtbase/src/platformsupport/input/xkbcommon`
下的 4 个文件，用 664 MB 的整包会带来无谓的下载与解压开销（HMDFS 上尤其明显）。
conandata.yml 的 url 列表把实测可达的镜像放在前面，官方 download.qt.io 保留在列表中（R39）。

## 3. 模块内容与安装产物

上游 `xkbcommon.pro`：

```
TARGET = QtXkbCommonSupport
MODULE = xkbcommon_support
QT = core-private gui-private
CONFIG += static internal_module
DEFINES += QT_NO_CAST_FROM_ASCII
QMAKE_USE += xkbcommon
clang:!intel_icc: QMAKE_CXXFLAGS += -ftemplate-depth=1024
```

即本模块是**静态 internal module**（不是 .so）。据此本包安装：

```
lib/libQt5XkbCommonSupport.a
include/QtXkbCommonSupport/5.15.19/QtXkbCommonSupport/private/qxkbcommon_p.h
include/QtXkbCommonSupport/private/qxkbcommon_p.h          ← 消费者实际 include 的短路径
lib/cmake/Qt5XkbCommonSupport/Qt5XkbCommonSupportConfig.cmake
lib/cmake/Qt5XkbCommonSupport/Qt5XkbCommonSupportConfigVersion.cmake
mkspecs/modules/qt_lib_xkbcommon_support_private.pri
```

三者对应三类消费者：CMake（kwayland5）、qmake（qtwayland 5.15）、以及需要短 include
路径的源码（kwayland5 的 `surface_p.cpp` 走 `Qt5::WaylandClientPrivate`，间接依赖本模块）。

## 4. OHOS 适配要点

1. **`-fPIC` 必须显式加**：本模块是静态库，会被链进共享库
   （`libKF5WaylandClient.so`）。OHOS aarch64 上把非 PIC 目标链入共享库会报
   `relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used against symbol ...;
   recompile with -fPIC`（同类失败已记录于 zlib/1.3.1 → zlib/1.3.1.1 的 PIC 重建）。
2. **`-ftemplate-depth=1024`**：照搬上游对 clang 的处理。`qxkbcommon.cpp` 里的
   `KeyTbl` 模板展开深度超过旧 clang 的 256 层默认上限。
3. **`-DQT_NO_CAST_FROM_ASCII`**：照搬上游 `DEFINES`，否则源码里 `"..."` 字面量
   在禁用隐式转换的 Qt 头下会产生额外重载歧义。
4. **private 头依赖 `qplatformdefs.h`**：`qxkbcommon.cpp` →
   `QtGui/private/qguiapplication_p.h` → `QtCore/private/qthread_p.h` →
   `#include "qplatformdefs.h"`。该文件 Qt 放在 **mkspecs 目录**而非 include/，
   因此编译时须补 `-I<mkspecs>/harmonyos-clang`（本包按
   `harmonyos-clang` → `linux-clang` 顺序探测，取第一个存在者）。
5. **本包不做 ELF 签名**：产物只有静态库与头文件，没有可执行 ELF；需要签名的
   可执行文件由其消费者产生（消费者负责签名）。
6. **R26 系统同名库**：本模块不产出任何 .so，不与系统 `/lib`、`/lib64` 同名冲突。

## 5. CMake 包配置的发现方式（避免 CMakeDeps 遮蔽）

本包 `package_info()` 设 `cmake_find_mode = "none"` + `builddirs = ["lib/cmake"]`，
与 `qt/5.15.19.1`、`qt5-qtbase/5.15.2.2` 保持同一策略：把**手写的原生**
`Qt5XkbCommonSupportConfig.cmake` 交给 CMake，而不是让 CMakeDeps 生成一个不完整的替身，
从而避免两个 config 互相遮蔽（E451 类问题的既有处理方式）。

配置里生成的真实 CMake 列表变量（不能把引号串直接塞进 `set_target_properties`，
否则 CMake 报 `set_target_properties called with incorrect number of arguments` —— 本包
开发期实测踩过）：

```cmake
set(_Qt5XkbCommonSupport_INCLUDE_DIRS
    "<qt-pkg>/include" ... "<mkspecs>/harmonyos-clang" ...
)
add_library(Qt5::XkbCommonSupportPrivate STATIC IMPORTED)
set_target_properties(... IMPORTED_LOCATION "<pkg>/lib/libQt5XkbCommonSupport.a"
    INTERFACE_INCLUDE_DIRECTORIES "${_Qt5XkbCommonSupport_INCLUDE_DIRS}"
    INTERFACE_LINK_LIBRARIES "<libxkbcommon>/lib/libxkbcommon.so")
```

include 根按**编译期实际用到的那一套**导出：QtCore/QtGui 公共头 + 两者的
`private` + `qpa` + Qt5 版本目录 + mkspecs。这样消费者 `find_package` 后
`target_link_libraries(... Qt5::XkbCommonSupportPrivate)` 即拿到可编译的完整环境。

## 6. qmake 模块 pri

`mkspecs/modules/qt_lib_xkbcommon_support_private.pri` 的**变量形态**并非凭空写就，而是
读 `qt/5.15.19.1` 包内真实的 support 模块 pri（`qt_lib_fontdatabase_support_private.pri`、
`qt_lib_service_support_private.pri`）逐字段对照后生成：

```
QT.xkbcommon_support_private.VERSION = 5.15.19
QT.xkbcommon_support_private.name = QtXkbCommonSupport
QT.xkbcommon_support_private.module = Qt5XkbCommonSupport
QT.xkbcommon_support_private.libs = <本包>/lib          ← 指向包内，而非 Qt 自身 libdir
QT.xkbcommon_support_private.includes = <本包>/include/QtXkbCommonSupport{,/5.15.19{,...,/QtXkbCommonSupport}}
QT.xkbcommon_support_private.depends = core_private gui_private
QT.xkbcommon_support_private.module_config = v2 staticlib internal_module
QT.xkbcommon_support_private.enabled_features = xkbcommon
QT_CONFIG += xkbcommon
QT_MODULES += xkbcommon_support
```

要点：`module` 字段必须是 `Qt5XkbCommonSupport`（qmake 据此生成 `-lQt5XkbCommonSupport`，
对应真实归档名 `libQt5XkbCommonSupport.a`）；`libs`/`includes` 必须是**包内绝对路径**，
因为 `QT_MODULE_LIB_BASE` 指向 Qt 自己的 libdir，本包的归档不在那里。

## 7. R51 上游测试清点（三步法）

**第一步 · 清点**：本模块上游**无自带测试**。

```
$ tar tf qtbase-everywhere-opensource-src-5.15.19.tar.xz \
      | grep 'platformsupport/input/xkbcommon/' 
qtbase-everywhere-src-5.15.19/src/platformsupport/input/xkbcommon/
qtbase-everywhere-src-5.15.19/src/platformsupport/input/xkbcommon/qxkbcommon.cpp
qtbase-everywhere-src-5.15.19/src/platformsupport/input/xkbcommon/qxkbcommon_3rdparty.cpp
qtbase-everywhere-src-5.15.19/src/platformsupport/input/xkbcommon/qxkbcommon_p.h
qtbase-everywhere-src-5.15.19/src/platformsupport/input/xkbcommon/xkbcommon.pro
→ 4 个文件（1 x .pro + 2 x .cpp + 1 x .h），无 tests/ 目录

$ grep -cE 'test|check' <module>/xkbcommon.pro
→ 0（无 test target）
```

因此 `upstream_tests = 0`，`upstream_test_in_build = false`。

**第二步 · 可运行环境实测**：上游无测试可跑，故本 PR 的实质测试全部落在
`test_package/`（消费者视角），三层测试对应关系见 §8。

**第三步 · 如实回填**：`test_package/MANIFEST.yml` 的 `upstream_tests: []`、
`assertion_count: 18` 均为实测值，无占位符。

## 8. 三层测试（docs/TEST_QUALITY_SPEC.md）

| 层 | 内容 | 本包实现 |
|----|------|---------|
| 单元/接口测试 | 被测包的 API 行为 | `test_package/src/test_xkbsupport.cpp`：18 条断言，覆盖两个 TU 的 API |
| 集成测试 | 与真实依赖协同 | 同上：真实链接 libxkbcommon，构造 keymap + live `xkb_state`，用模块函数翻译 keycode |
| 消费者构建测试 | `find_package` 可用性 | `test_package/CMakeLists.txt`：`find_package(Qt5XkbCommonSupport REQUIRED)` + 断言 `Qt5::XkbCommonSupportPrivate` 目标与其 `IMPORTED_LOCATION` 真实存在 |

`test()` 用 `ctest --output-on-failure` 执行，未通过则非零退出（非 print-only 空壳，满足 PF3）。

### 断言覆盖的两条实现路径

`QXkbCommon` 的实现分布在两个 TU 里，测试刻意各覆盖若干，避免"只链上没链全"的假绿：

- `qxkbcommon.cpp`：`keysymToQtKey`（含 KeyTbl 查表、修饰键稳定性、KP_0 数字键盘）、
  `isKeypad`、`isLatin1`、`modifiers(live state)`、以及带 `xkb_state` 的三参重载
  `keysymToQtKey(sym, mods, state, code)`
- `qxkbcommon_3rdparty.cpp`：`qxkbcommon_xkb_keysym_to_upper`、
  `xkbcommon_XConvertCase`（字母转换 + 数字恒等）、`lookupStringNoKeysymTransformations`

### 实测平台约束（已写入测试注释）

本机镜像上 libxkbcommon 1.6.0 的默认数据目录 `/share/X11/xkb` **不存在**
（实测报错 `xkbcommon: ERROR: failed to add default include path /share/X11/xkb`，
`xkb_context_new(XKB_CONTEXT_NO_FLAGS)` 因此返回 nullptr）。该返回值为**平台事实**而非
本包缺陷，故测试改用 `XKB_CONTEXT_NO_DEFAULT_INCLUDES` + 自包含 keymap 字符串
（该写法不依赖任何数据文件），仍真实驱动了库、静态归档与模块的翻译路径。

## 9. 本地验证（W3，阻塞门禁）

```
$ conan create archives/q/qt5-xkbcommon-support/5.15.19 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing -c tools.build:jobs=2
EXIT=0
```

日志关键行：

```
-- FIND_PACKAGE_OK Qt5::XkbCommonSupportPrivate=/storage/.../p/lib/libQt5XkbCommonSupport.a
1/1 Test #1: xkbsupport_api ...................   Passed    0.04 sec
100% tests passed, 0 tests failed out of 1
assertions=18 failures=0          （直接运行构建出的 test_xkbsupport，EXIT=0）
```

开发过程记录（每次都是真实失败→定位→修复，非一次通过）：

| 轮次 | 现象 | 根因 | 修复 |
|------|------|------|------|
| 1 | `fatal error: 'qplatformdefs.h' file not found` | Qt 把该头放在 mkspecs 目录，未加 `-I` | 编译/导出 include 列表补 `mkspecs/harmonyos-clang` |
| 2 | CMake `set_target_properties called with incorrect number of arguments` | 引号串整体塞进 `INTERFACE_INCLUDE_DIRECTORIES`，生成 `""a" "b""` | 改为生成真实 CMake 列表变量后 `"${var}"` |
| 3 | 编译期 `'QtXkbCommon/private/qxkbcommon_p.h' file not found` | 测试头路径笔误 | 更正为 `QtXkbCommonSupport/private/...` |
| 4 | 运行期 1 条断言失败（`xkb_context_new` 返回 nullptr） | 平台无 `/share/X11/xkb` 数据目录 | 改用 `NO_DEFAULT_INCLUDES` + 自包含 keymap |
| 5 | `ask` 全绿 18/18 | — | — |

## 10. 消费方式（供 kwayland5 / qtwayland 使用）

CMake：

```cmake
find_package(Qt5XkbCommonSupport REQUIRED)
target_link_libraries(<your-target> PRIVATE Qt5::XkbCommonSupportPrivate)
```

qmake：

```qmake
QT_FOR_PRIVATE += xkbcommon_support-private
```

## 11. 已知限制

- 本包只覆盖 `QtXkbCommonSupport` 这一个模块的**构建**；`xkbcommon-x11` 相关代码
  （上游同目录之外）未包含，OHOS 无 X11，不需要。
- 运行期 xkb keymap 数据目录（如 `/share/X11/xkb`）不属于本包职责；需要完整
  keymap 规则的下游（如合成器）须自行提供 xkb 数据，或使用自包含 keymap。

## 12. 鸿蒙特有测试：端到端消费者用例（rule 12）

本模块的职责是把键盘硬件输入翻成 Qt 键事件与文本，因此「完整消费者用例」就是
**跑一遍真实的打字会话，全程走模块自己的翻译路径**（静态归档已链入）。见
`test_package/e2e/xkbcommon_e2e.cpp`（ctest 用例 `xkbcommon_typing_e2e`）：

```
① 自包含 XKB keymap（无 include 指令，不读本机不存在的 /share/X11/xkb）
   编译成活的 xkb_keymap / xkb_state

② 「Ca1」打字会话（Shift+c → 'C'、a → 'a'、1 → '1'），每键经：
     QXkbCommon::lookupString(state, code)                    取文本
     QXkbCommon::keysymToQtKey(sym, mods, state, code)        取 Qt 键
     QXkbCommon::modifiers(state)                             取修饰键

③ 产出文本**逐字符比对**必须等于字面量 "Ca1"（载荷比对，非计数）

④ Shift 层不是硬编码：用 QXkbCommon::qxkbcommon_xkb_keysym_to_upper()
   （第三方 TU）由基础层**推导**出 Shift 层并要求相等
   → 该 TU 若被抽空/打桩，用例立刻失败

⑤ 反向通路：由会话产出的 Qt 键构造 QKeyEvent → QXkbCommon::toKeysym()
   必须映回同一 Qt 键，且 xkb_keysym_to_utf32() 与会话自身 keysym 表示同一字符
```

实测输出（`conan create` 全流程，退出码 0）：

```
ok   - xkb_context_new(XKB_CONTEXT_NO_DEFAULT_INCLUDES)
ok   - keymap compiled from the self-contained description
ok   - typing session through QXkbCommon produced exactly "Ca1"
ok   - Shift+c produced Qt::Key_C
ok   - a produced Qt::Key_A
ok   - 1 produced Qt::Key_1
ok   - Shift level equals qxkbcommon_xkb_keysym_to_upper(base level)
ok   - QXkbCommon::modifiers reports Shift while it is held
ok   - QXkbCommon::modifiers drops Shift after release
E2E STEP toKeysym(Qt::Key_A from the session) = 0x01000061 (unicode form), session keysym = 0x00061
ok   - round trip: the keysym maps back to the same Qt key
ok   - round trip: the keysym denotes the same character as the session's
assertions=15 failures=0
hongmeng_e2e_flow=PASS
```

开发中真实踩到 **2 个我自己写错的预期**（均非模块缺陷，已改正为模块的真实契约）：

| # | 现象 | 根因 | 修复 |
|---|------|------|------|
| 1 | `round trip: toKeysym(typed key) == the keysym the session produced` FAIL（14/15） | 我误以为 `toKeysym(Qt::Key_A)` 会返回会话里的 `XKB_KEY_a`；实测模块对表外键走 **Unicode 形式回落**，返回 `0x01000061`（`0x01000000 \| codepoint`，见 `qxkbcommon.cpp:57-62`） | 断言改为模块的真实契约：该 keysym 必须**映回同一 Qt 键** |
| 2 | 改用大小写折叠比较后仍 FAIL | `qxkbcommon_xkb_keysym_to_upper(0x01000061)` 与 `(XKB_KEY_a)` 不相等——大小写折叠只对 Latin-1 keysym 有效，两种形式本就不在同一域 | 改用 `xkb_keysym_to_utf32()` 判**字符等价**，这才是两种形式的共同语义 |

要点：

- **该用例是「真有功能流程」的判据**：它不断言「函数能被调用」，而是要求一整条
  输入→键值→文本链路产出**指定的字符串**；且 Shift 层由第三方 TU 推导，主 TU
  单独正确也不能让用例通过。
- 断言计数口径：本用例 15 条，与 `test_xkbsupport` 的 18 条**分开计**；
  `test_package/MANIFEST.yml` 的 `assertion_count` 为两者之和 33
  （另有 configure 期 `FATAL_ERROR` 断言不产生 `assertions=` 计数）。
