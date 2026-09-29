# mlite 0.5.5 适配笔记

## 编译环境
- 构建系统: qmake（Qt5；制品仓无 ohos mkspec，使用自定义 mkspec 继承 qtbase 的 `linux-clang`）
- 编译日期: 2026-09-29
- 编译器: clang/clang++ 15.0.4（OHOS SDK，profile `ci/conan/profiles/ohos-aarch64`）
- 目标: OHOS aarch64（os=OHOS / arch=armv8 / compiler.libcxx=libc++）
- 状态: built
- 上游: https://github.com/sailfishos/mlite ，tag `0.5.5` → commit `42c3b2102dadfc54a2cc7c87c6e4cfb28437c908`

## 构型说明（重要）
本配方采用**上游原生的「dconf 关闭」构型**：

- 上游 `src/src.pro:21-26` 为 `CONFIG += link_pkgconfig` + `PKGCONFIG += glib-2.0`，其后 `packagesExist(dconf) { … }` 才启用 `dconf` 与 `mdconf*.cpp`；为假时上游打印
  `warning("dconf not found; MDConfItem will not be built")`（`src/src.pro:46-48`）。
- 本构型下产物不含 `MGConfItem / MDConfItem / MDConfGroup`，`tests/tests.pro` 亦不构建 `ut_mdconfgroup / ut_mdconfitem`。
- 选择该构型的原因（实测证据见 `../reports/test-report.md` 与 manifest.yaml `knowledge_gained`）：
  1. 制品仓 `dconf/0.40.0` 的预编译 `.so` 自签名与内容不符，OHOS 加载器以 `Permission denied` 拒载 → 链接它的任何可执行体在本平台无法运行（全新 `CONAN_HOME` 重新下载 md5 一致仍失败；同批下载的 `expat` 可正常加载；用 SDK `binary-sign-tool -selfSign 1` 重新自签名后可加载）；
  2. `glib/2.84.0` 在制品仓只有静态库：`libdconf.so` 静态链入 glib（不导出 glib 符号），消费者再静态链入一份 → 同进程两份 GLib，GObject 类型系统失配（dconf `changed` 信号查不到 → 崩溃，`ut_mdconf*` 实测 SIGSEGV）。

## 编译步骤

```bash
# 依赖（dconf 不引入 → packagesExist(dconf) 为假）
conan install --requires=qt5-qtbase/5.15.2.2 --requires=glib/2.84.0 \
  --tool-requires=pkgconf/3.0.6 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=never

# 配方内的构建动作（build()）
# 1) 修复 qtbase 包可重定位性：qt.conf + mkspecs/**/*.pri 内的构建期绝对路径 → 包目录
# 2) 生成自定义 mkspec（继承 linux-clang，补 QMAKE_LFLAGS += -L/lib）
qmake -spec <generators>/mlite-ohos VERSION=0.5.5 mlite.pro
make -j4 sub-src-all sub-tools-all
```

## 遇到的问题与解决方案

| # | 问题（首个错误原文） | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Project ERROR: Unknown module(s) in QT: core dbus` + `Cannot read …/mkspecs/modules-inst/qt_lib_core.pri: No such file or directory` | `qt5-qtbase/5.15.2.2` 包内 `bin/qt.conf` 与 `mkspecs/**/*.pri` 内嵌构建期绝对路径 `…/.conan2/p/b/qt5-qXXXX/b`，该目录在包上传后不存在 | 构建期改写 `qt.conf` 与 `mkspecs/**/*.pri`（替换为包目录；与 `archives/l/libngf-qt/0.3.1` 的处理一致），实测修复 50 个 `.pri` |
| 2 | `fatal error: 'dconf.h' file not found` / `'common/dconf-enums.h' file not found with <angled> include` | conan `dconf` 包的 `include/dconf/{common,client}` 未出现在 pkg-config `Cflags`（上游 `dconf.pc` 为 `-I${includedir}/dconf`，配合系统隐含 `/usr/include`） | 本构型不引入 dconf，该问题不再出现（如将来启用 dconf，需在构建期提供 `Cflags: -I${inc} -I${inc}/dconf` 的修正 `.pc`） |
| 3 | `ld.lld: error: unable to find library -l:ld-musl-aarch64.so.1` | glib 的 pkg-config `Libs` 含 `-L/lib -l:ld-musl-aarch64.so.1`，`-L/lib` 被 pkg-config 当系统路径剔除 | 自定义 mkspec 末尾 `QMAKE_LFLAGS += -L/lib` |
| 4 | `Makefile.ut_mdesktopentry:526: ut_mdesktopentry.qm] Error 127`（仅构建上游 tests 时） | 上游 `tests/ut_mdesktopentry.pro:7` 硬编码 `$$[QT_INSTALL_BINS]/lrelease`；qt5-qtbase 不含 Qt Linguist，制品仓无 Qt5 qttools（`qt5-qttools/5.15.2` → 404） | 打包阶段不构建 tests（`make sub-src-all sub-tools-all`）；适配阶段跑上游测试时自备 `lrelease`（实测 Qt6 `qttools/6.11.1` 生成的 `.qm` 能被 Qt5 `QTranslator` 正确加载，翻译用例全绿） |
| 5 | `Project ERROR: dconf development package not found`（仅 `ut_mdconfgroup` 子项目） | 该子项目 qmake 调用未继承 `PKG_CONFIG_PATH` | 构建脚本在子 make 前统一导出 `PKG_CONFIG_PATH`（配方中由 `Environment` 在 `build()` 内统一提供） |

## 源码修改
**无**。本版本未改动上游任何源码文件（`diff` 与解压后的 pristine 树一致），OHOS 适配全部落在配方侧：
1. qtbase 包可重定位性修复（问题 1）；
2. 自定义 mkspec（问题 3）。

## 依赖版本
- `qt5-qtbase/5.15.2.2`（Qt5Core + Qt5DBus；唯一以 `configure -dbus` 构建的版本，`5.15.2` 为 `-no-dbus`）
- `glib/2.84.0`（仅满足上游无条件 `PKGCONFIG += glib-2.0`，本构型不引用 glib 符号）
- 传递：`dbus/1.14.10`、`expat/2.8.2`、`zlib/1.3.1`、`libffi/3.4.4`、`pcre2/10.40`
- 未引入 `dconf`（见「构型说明」）

## 验证结果

**统一口径**（与 `manifest.yaml`、`test_package/MANIFEST.yml`、`reports/test-report.md` 一致）：

| 指标 | 数量 |
|---|---|
| 上游测试程序总数（`tests/tests.pro`；`tests.xml.in` 声明 5 个 case） | **6** |
| 本构型（dconf 关闭）可构建 | **4** |
| 本构型实际执行 | **2** → 断言 **103 通过 / 0 失败 / 0 跳过** |
| 因依赖缺陷不可运行 | **2**（`ut_mremoteaction` 5 项 + `ut_mnotification` 3 项 = 8 项） |
| 按上游条件未构建 | **2**（`ut_mdconfgroup` / `ut_mdconfitem`，`packagesExist(dconf)` 为假） |
| 4 个可运行用例的断言总数（含依赖修复场景） | **111** = 103 + 8（补共享 `libdbus-1.so` 后实测 5/5 + 3/3 通过） |

> **漏测申报（已确认接受）**：4 例未执行 —— `ut_mremoteaction` / `ut_mnotification`（QtDBus 运行期缺共享 `libdbus-1.so`）与 `ut_mdconfgroup` / `ut_mdconfitem`（上游 `packagesExist(dconf)` 为假，dconf 关闭构型）。已按统一口径在 `manifest.yaml`、`test_package/MANIFEST.yml`、`reports/test-report.md §2.2` 显式申报，并经用户于 2026-09-29 确认接受（路径 B）。依赖侧修复完成后将以 `mlite/0.5.5.1` 打开 dconf 构型补齐 6/6。

```bash
# conan create / conan-verify（见 reports/）
G1: PASS  G2: PASS  G3: PASS  G4: PASS
L2: PASS  L4: PASS  L5: PASS
# 上游测试（P3 构型 = 上游原生 dconf 关闭构型，真机实跑）
ut_mdesktopentry   Totals: 85 passed, 0 failed, 0 skipped   # ✅
ut_mfiledatastore  Totals: 18 passed, 0 failed, 0 skipped   # ✅
ut_mremoteaction   —— 未执行（依赖缺陷：QtDBus 运行期缺共享 libdbus-1；直连总线为 1 passed / 1 failed）
ut_mnotification   —— 未执行（同上；上游入口 dbus-launch 在制品仓包内路径失效）
ut_mdconfitem / ut_mdconfgroup —— 本构型上游 packagesExist(dconf) 为假，未构建
# test_package（conan create 内自动执行）
SUMMARY: 17 checks, 0 failures（含 3 项 OHOS 专有检查）
```

## 注意事项
- 上游 `tests/` 需要 Qt Linguist（`lrelease`）才能构建，本配方不构建上游测试；上游测试结果见 `reports/test-report.md`。
- 产物 `RUNPATH` 为构建期 conan 缓存路径（qtbase mkspec 的固有行为，与 `archives/l/libngf-qt` 一致）；消费方通过 conan 生成的运行环境解析 Qt5。OHOS 下不可事后改 ELF（会破坏代码签名导致拒载）。
- `MNotification` / `MRemoteAction` 的 D-Bus 能力依赖可用的 QtDBus：当前 `qt5-qtbase` 以 `-dbus`（运行期 `dlopen("libdbus-1")`）构建而制品仓 `dbus` 只提供静态库，需依赖侧补齐共享 `libdbus-1.so`（或 qt5-qtbase 改 `-dbus-linked`）后才能真正连通总线。
## 对话记录

### 对话 #1 — 首次 qmake 失败：Qt 模块解析
- 命令：`qmake -spec linux-clang VERSION=0.5.5 mlite.pro`
- 输出：`Project ERROR: Unknown module(s) in QT: core dbus` + 大量 `Cannot read …/mkspecs/modules-inst/qt_lib_*.pri: No such file or directory`
- 定位：qtbase 包 `bin/qt.conf` 与 `mkspecs/**/*.pri` 内嵌构建期路径（`…/.conan2/p/b/qt5-qXXXX/b`，包上传后不存在）
- 处置：改写 qt.conf + 逐文件把该前缀替换为包目录（首次正则写窄，产生 `/storage/Users/storage/Users/...` 重复前缀；二次修正后共修复 50 个 `.pri`），`qmake exit=0`

### 对话 #2 — 链接失败：musl 加载器库名无搜索路径
- 输出：`ld.lld: error: unable to find library -l:ld-musl-aarch64.so.1`
- 定位：glib 的 pkg-config `Libs` 含 `-L/lib -l:ld-musl-aarch64.so.1`，而 `-L/lib` 被 pkg-config 当系统路径过滤
- 处置：自定义 mkspec 末尾补 `QMAKE_LFLAGS += -L/lib`，链接成功

### 对话 #3 — 上游 tests 构建失败：缺 lrelease
- 输出：`Makefile.ut_mdesktopentry:526: ut_mdesktopentry.qm] Error 127`
- 定位：`tests/ut_mdesktopentry.pro:7` 硬编码 `$$[QT_INSTALL_BINS]/lrelease`，qt5-qtbase 不含 Qt Linguist，制品仓无 Qt5 qttools（`qt5-qttools/5.15.2` → 404）
- 处置：打包只构建 `sub-src-all sub-tools-all`；跑上游测试时用 Qt6 `qttools/6.11.1` 的 lrelease 生成 `.qm`（Qt5 QTranslator 可正确加载，翻译用例全绿）

### 对话 #4 — 运行期加载/崩溃：依赖 ELF 自签名与双 GLib
- 输出：`Error loading shared library libdconf.so.1: (needed by libmlite5.so.0) … Permission denied`；dconf 用例 `Bail out! GLib-GObject:ERROR … weak_ref_data_get_surely`
- 定位：① `dconf/0.40.0` 预编译二进制自签名与内容不符（重新下载 md5 一致仍失败；`binary-sign-tool -selfSign 1` 重签后可加载）；② glib 仅静态库，dconf 与其消费者各静态链入一份 → 同进程两份 GLib 实例
- 处置：本配方采用上游原生 dconf 关闭构型（不引入 dconf）；2 个 dconf 用例按上游条件不构建，QtDBus 相关用例如实申报为依赖缺陷不可运行（详见 `reports/test-report.md`）

### 对话 #5 — 配方收敛与验证
- `conan create … --build=missing --build="mlite/*"` → **exit 0**；test_package 17 项检查全绿（含 OHOS 专有用例）
- `conan-verify` → G1/G0/G2/G3/G4 + L2/L4/L5 **全部 PASS**
- `finish mlite 0.5.5 built` → W3 本地 CI 模拟（JC/L0-L5）**通过**；W2 原子性检查通过；submit 就绪预检 4 项全绿
---

**编译结束**: 2026-09-29 13:09
**最终状态**: built
