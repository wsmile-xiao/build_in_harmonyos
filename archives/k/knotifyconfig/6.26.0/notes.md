# knotifyconfig 6.26.0 适配笔记

## Scope

knotifyconfig 是 KDE Frameworks 6 的通知配置部件库，产出
`libKF6NotifyConfig.so.6`，导出 `KNotifyConfigWidget`（公共头
`<KNotifyConfigWidget>`）以及私有的 element / event-list 辅助类。
本包是 KF6 6.26 基线（知识库扩展）首次引入 ohpcd 的版本，无更早归档。

## 编译环境

- 构建系统: cmake (ECM/KDE)
- 编译日期: 2026-09-21
- 编译器: clang/clang++ (OHOS SDK, aarch64-linux-ohos)
- 状态: built (verified via conan create)

## 依赖版本

- qtbase/6.11.1（Qt6Widgets；ohpcd 已发布）
- qtmultimedia/6.11.1（顶层 CMakeLists 先找 Canberra，找不到则
  `find_package(Qt6Multimedia REQUIRED)`；Canberra 未发布，故走
  Qt6Multimedia 分支，用于通知声音试听）
- kcompletion/6.26.0、kconfig/6.26.0、ki18n/6.26.0、kio/6.26.0
- ecm/6.26.0（构建工具）

未启用（制品仓未发布 / 平台限制）：

- Qt6DBus —— `USE_DBUS=OFF`（ohpcd 未发布 Qt6DBus）
- KF6::KIOWidgets —— kio 在 ohpcd 以 KIOCORE_ONLY 构建，未产出
  KIOWidgets / KIOGui / KIOFileWidgets（solid / kbookmarks / kjobwidgets /
  kiconthemes 6.26 未发布）
- KF6ConfigWidgets / KF6Notifications / KF6WidgetsAddons / KF6XmlGui 6.26 ——
  ohpcd 只发布了 6.14.0 / 6.18.0，故 `BUILD_TESTING=OFF`
- Qt6LinguistTools / gettext —— 未发布，故跳过 `ki18n_install(po)`

## 适配要点

### 1. kio 是 KIOCORE_ONLY，KUrlRequester 不可用（补丁 0002/0003/0004）

上游通知声音输入框用的是 `KUrlRequester`，该类在 `KF6::KIOWidgets` 里。
KIOCORE_ONLY 的 kio 里：

- 没有 `KF6::KIOWidgets` 目标；
- 连 `KF6KIOCoreConfig.cmake` 都没有 —— `KF6::KIOCore` 由
  `KF6KIOTargets.cmake` 导出（来自 `install(TARGETS KF6KIOCore EXPORT
  KF6KIOTargets ...)`），只有在 `find_package(KF6KIO)` 之后才可见。

因此补丁 0002 把 `target_link_libraries` 的 `KF6::KIOWidgets` 换成
`KF6::KIOCore`（保留 KIO 依赖是刻意的：这样依赖图与上游差异最小，且
audiocd / baloo 6.28.0 / libkomparediff2 / kgoldrunner 已有同款先例）。

补丁 0003 把 `knotifyconfigactionswidgetbase.ui` 里的
`<widget class="KUrlRequester" name="Sound_select">` 换成 `QLineEdit`，
并且必须把整个 `<customwidgets>…</customwidgets>` 块一起删掉 —— 否则 uic
生成的代码仍会 `#include <kurlrequester.h>`。

补丁 0004 把只属于 KUrlRequester 的调用删掉/改写：

| 上游 | 适配后 |
|------|--------|
| `setStartDir(QUrl::fromLocalFile(...))`（种子「声音目录」） | 删除（QLineEdit 无文件对话框） |
| `setMimeTypeFilters({audio/x-vorbis+ogg, audio/x-wav})` | 删除（同上） |
| `setUrl(QUrl(readEntry("Sound", true)))` | `setText(readEntry("Sound", true))` |
| `text()`（save() 里本来就用 text()） | 不变 |

注意两处**不需要**改的地方，容易误伤：

- `connect(m_ui.Sound_select, SIGNAL(textChanged(QString)), ...)` ——
  `KUrlRequester::textChanged(QString)` 与 `QLineEdit::textChanged(QString)`
  同名同签名，替换后依然成立；
- `slotPlay()` 里的 `m_ui.Sound_select->text()` —— 本来就只用 text()，
  上游注释也写明「don't use .url() here, .notifyrc files have predefined
  "static" entries with no path」。

### 2. 原生 OHOS 构建没有 SONAME 规则

`os_build == os_host == OHOS` 时 CMake 不会设 `CMAKE_SYSTEM_NAME`，于是停在
Generic 平台模块 —— 该模块没有共享库 SONAME 规则，`-Wl,-soname` 被丢掉，
结果是 `libKF6NotifyConfig.so.6` 没有 `DT_SONAME`，且导出的 CMake 目标会带上
`IMPORTED_NO_SONAME TRUE`。配方在 `settings.os == "OHOS"` 时手工补：

```python
tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
```

### 3. 安装后必须重签 ELF

CMake 在 install 阶段会重写已安装共享库的 RUNPATH，这一步会让 OHOS 构建期写入
的 `.codesign` 段失效，OHOS 加载器随后拒绝加载（表现为 `Permission denied`）。
`package()` 因此在 `cmake.install()` 之后调用 `_sign_ohos_elf_tree()`：对包内
每个 ELF 先 `llvm-objcopy --remove-section .codesign`，再
`binary-sign-tool sign -inFile X -outFile X -selfSign 1`。
（kiconthemes 6.26.0 / kitemmodels 6.18.0.1 / kirigami 6.18.0 先例，均已在 main。）

### 4. 两个手工生成的 CMake 文件

- `ECM_MODULE_PATH`：ECM 自己安装的 `ECMConfig.cmake` 会设这个变量，但
  CMakeDeps 生成的那份不会，而项目顶层 `set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})`
  依赖它，故配方手工拼出 `modules` / `find-modules` / `kde-modules` 三个目录。
- `conan_cmakedeps_paths.cmake`：qtbase 用 `cmake_find_mode=none`，
  CMakeDeps 因此不会生成这个文件，也就不会把 qtbase 的 `lib/cmake` 加进
  `CMAKE_PREFIX_PATH`。配方手工生成一份，并把**所有**依赖的
  `lib/cmake` / `lib` / `include` 都前置进去，好让
  `KF6KIOConfig.cmake` 里的 `find_dependency` 链（KF6CoreAddons、Qt6Network）
  全部解析得到。

### 5. 构建期 LD_LIBRARY_PATH

- ECM 6.26 的 `KDEInstallDirs6` 会在 configure 阶段调用 qtbase 的 `qtpaths`
  宿主工具（`ecm_query_qt` → `QT_INSTALL_PREFIX`）。沙箱的
  `LD_LIBRARY_PATH` 里 `/data/storage/el1/bundle/libs/arm64` 下有一个不兼容的
  `libc++_shared.so` 会把它顶掉，故前置 `/system/lib64`
  （kconfig 6.26.0 / bluez-qt 6.28.0 先例）。
- SDK 的 `llvm/lib` 同样前置，供 lld 解析 `libxml2.so.16`。

## 测试说明（N 申报，rule2 / rule4）

上游 N=2 → 适配后 N'=0，减少 2，原因具体如下：

- 上游 `tests/CMakeLists.txt` 里唯一可执行目标是
  `add_executable(knotifytest main.cpp knotifytestwindow.cpp)`，经
  `ecm_mark_as_test(knotifytest)` 注册进 CTest，测试名 `knotifytest`。
  朴素扫描口径（tests/ 目录内 `add_executable` 1 处 +
  `ecm_mark_as_test` 1 处）= 2；CTest 实际注册数 = 1。上游默认分支 master
  的 `tests/CMakeLists.txt` 与 6.26.0 tag 完全一致（已逐行比对）。
- 上游 `knotifytest` 本身没有断言：`tests/main.cpp` 只是
  `QApplication` + `show()` + `exec()` 的手工 GUI 演示程序。
- 本基线 `BUILD_TESTING=OFF`，所以实际执行 0 个：`tests/` 需要
  KF6ConfigWidgets / KF6Notifications / KF6WidgetsAddons / KF6XmlGui 6.26
  加 Qt6Test，而 ohpcd 上这四个 KF6 包只有 6.14.0 / 6.18.0，没有 6.26.0，
  `find_package` 必然失败。

验证由 `test_package` 承担（消费者视角，20 条断言）：

1. `test_knotifyconfig.cpp` —— 真 API 读改存往返。测试自己往
   `$XDG_CONFIG_HOME/knotifyconfig-consumer.notifyrc` 写入
   `[Event/test-event] Action=Sound|Popup / Sound=bell.ogg`，然后
   `setApplication` → `selectEvent` → `disableAllSounds` → `save`，
   最后读回文件断言：
   - `Action` 变成 `Popup`（`disableAllSounds` 生效）；
   - `Sound` 仍是 `bell.ogg` —— 这一条是补丁 0004 的回归闸门：
     若 `setConfigElement()` 的 `setText()` 丢了，`text()` 会是空串，
     文件里的 `Sound` 就被写空；若 `save()` 的 `text()` 改错了，同样失败；
   - 同组 `Name` 未被破坏（证明写回的是同一个文件、其余键被保留）。
   另外用 `changed(bool)` 信号断言 `disableAllSounds()` 确实发出
   `changed(true)`（证明事件表里真的解析出了带 Sound 的 `test-event`）、
   `save()` 发出 `changed(false)`。
2. `test_knotifyconfig_elf.py`（OHOS 专项）—— 只做结构化 ELF 头/节表读取，
   不对二进制做文本 grep：`lib/libKF6NotifyConfig.so*` 恰有一个实体文件、
   `.so` / `.so.6` 软链齐全；实体文件为 ELF64、小端、`ET_DYN`、
   `EM_AARCH64`；节表含 `.text` 与 `.codesign`（`package()` 重签产物）。

运行环境：`QT_QPA_PLATFORM=offscreen`（部件需要 QApplication 但无显示），
`HOME` / `XDG_CONFIG_HOME` / `XDG_CONFIG_DIRS` / `XDG_DATA_HOME` /
`XDG_DATA_DIRS` 全部指向构建目录下的临时树，避免宿主 `~/.config` 或
`/usr/share` 干扰 `KNotifyEventList::fill()` 的查找。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `target_link_libraries` 找不到 `KF6::KIOWidgets` | kio 在 ohpcd 是 KIOCORE_ONLY，不构建 KIOWidgets | 补丁 0002 改链 `KF6::KIOCore` |
| 2 | uic 生成的代码 include 了 `kurlrequester.h` | 只换了 widget class，没删 `<customwidgets>` | 补丁 0003 同时删除整个 `<customwidgets>` 块 |
| 3 | `ki18n_install(po)` 失败 | Qt6LinguistTools / gettext 未发布到 ohpcd | 补丁 0001：非 HarmonyOS 才调用（运行时 i18n 仍走 KF6::I18n） |
| 4 | `find_package(KF6ConfigWidgets 6.26)` 失败 | 6.26 未发布到 ohpcd | `BUILD_TESTING=OFF` |
| 5 | 安装出来的 `.so.6` 没有 DT_SONAME | 原生 OHOS 构建落在 CMake Generic 平台模块，无 SONAME 规则 | 手工设 `CMAKE_SHARED_LIBRARY_SONAME_{CXX,C}_FLAG` |
| 6 | 安装后的库运行时 `Permission denied` | install 重写 RUNPATH 使 `.codesign` 失效 | `package()` 用 objcopy + binary-sign-tool 重签 |
| 7 | 编译期 `fatal error: 'KConfig' file not found`，而同一次 configure 里 `KF6Config` 报 found | `<KConfig>/<KConfigGroup>` 是 `include/KF6/KConfigCore/` 下的转发头，只有 `KF6::ConfigCore` 带它的 include 目录；上游靠 `KF6::KIOWidgets → … → KF6::ConfigCore` 的**传递** usage requirement 拿到，而补丁 0002 换掉的 KIOWidgets 正是那条隐式路径 | 补丁 0005：显式链接 `KF6::ConfigCore` |
