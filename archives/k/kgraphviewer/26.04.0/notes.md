# kgraphviewer 26.04.0 — OHOS 适配笔记

## 源码身份

- 归档: https://download.kde.org/stable/release-service/26.04.0/src/kgraphviewer-26.04.0.tar.xz
- SHA256: 0c6c84b5a75c970eaaf4a5dfa6dd6c2afe4e31137c2547c78a0176c0833d3bfc
  （官方无 .sha256 伴随文件，此为实测哈希；tarball 1,608,476 字节）
- License: GPL-2.0-or-later；CMake project 版本 2.5.26040
- 上游产物: kgraphviewer（GUI 应用，D-Bus 单实例）、kgraphviewerlib
  （SHARED，PUBLIC 链 KF6::Parts + Graphviz::Graphviz）、kgraphviewerpart
  （KParts 插件，安装到 <prefix>/lib/plugins/kf6/parts/）。
  BUILD_GRAPHEDITOR 默认 OFF（未构建，保持上游默认）。

## NO_UPSTREAM_TESTS 证据闭环

- `tar -tf kgraphviewer-26.04.0.tar.xz | grep -ci test` => 0
- 全部 CMakeLists.txt `grep -rn 'add_test\|enable_testing\|BUILD_TESTING'` => 0 命中
- `.gitlab-ci.yml` 仅 build 模板（`grep -c test` => 0）
- `.kde-ci.yml:15` 声明 `require-passing-tests-on: Linux/FreeBSD/Windows`，
  但仓库不存在任何测试目标，无可执行入口
- 结论: NO_UPSTREAM_TESTS（discovery.status=EVIDENCE_COMPLETE，
  完整记录见 manifest.yaml `upstream_tests:` 段）。门禁由自建
  test_package 承担（L2 冒烟 + KParts 插件加载 + 进程内 cgraph/gvc
  布局渲染 + 鸿蒙 ELF 适配断言）。

## 主要适配点

1. **KF6 混轨困局与 vendored staging 链（E277 build-vendored-to-staging）**

   困局：kparts 未发布到 ohpcd；kparts 6.18 硬依赖 KF6KIOCore，而 kio 只
   有 6.26.0（KIOCORE_ONLY）；kxmlgui/kconfigwidgets/kjobwidgets 只有
   6.18 轨。一条 conan 图里同时消费 6.26（kio）与 6.18（kxmlgui）必须
   用 override 统一版本，而任何 KF6 依赖版本变化都会使**已发布包的
   package_id 失效**，conan --build=missing 触发源码重编，且这些配方
   在 build() 里自带 ctest——沙箱下必挂（CI 实测）：
   - r4：override qtbase→6.11.1.2 → 全量 KF6 重编路线，kcolorscheme/
     6.18.0 configure Error 1 失败终止（Qt6GuiPrivate→XKB 缺失；无
     3600s 超时事件）；
   - r5：override kconfig→6.26 → kcolorscheme/6.18.0 重编，上游源码在
     Qt 6.11 头文件下编译失败（缺 #include <QVariant>）；
   - r6：kconfigwidgets/6.18.0 重编，其自带 ctest 7 个用例沙箱失败。

   解法（本配方最终形态）：把 kconfigwidgets → kjobwidgets → kxmlgui →
   kparts 6.18.0（URL+SHA256 双 pin，sha 与仓库既有配方 conandata 一致）
   以 SHARED 形式链式构建进 staging，BUILD_TESTING=OFF（绕开沙箱 ctest
   陷阱），产物（.so + lib/cmake + headers）随本包发布。conan 图里只剩
   6.26 原生线 + graphviz 闭包，全部已发布二进制直接复用。

   - 为什么 SHARED 而非 E277 默认的 static：KParts/XmlGui 是 QObject
     框架，app + kgraphviewerlib + part MODULE 三方消费，必须共享同一份
     Q_OBJECT metaobject；静态库被多个 .so 各自链接会造成 metaobject
     重复，qobject_cast 运行期失效。
   - patch 0007：kparts 去除 PRIVATE KF6::KIOWidgets 链接（grep 全部 src
     确认 6.18 源码无 BrowserRun/BrowserExtension 类，KIO 使用仅
     KIO/FileCopyJob、KIO/StatJob；本平台 kio 为 KIOCORE_ONLY）。
   - patch 0011/0012/0013：vendored kxmlgui 去除 PrintSupport（find_package
     组件/链接行/KShortcutsEditor 打印功能 → 导出的 no-op，API 稳定）。
   - patch 0014：vendored kjobwidgets 去除 KF6Notifications 依赖
     （KNotificationJobUiDelegate 本库与 kparts 均不使用；knotifications
     仅 6.18 轨，保留会把 6.18 钉子重新拉回 conan 图）。
   - kxmlgui 用 FORCE_DISABLE_KGLOBALACCEL=ON（kglobalaccel 未发布）+
     USE_DBUS=OFF + BUILD_PYTHON_BINDINGS=OFF；kconfigwidgets 零补丁。

2. **Qt6::PrintSupport + D-Bus 切除（功能降级：无打印、无单实例）**
   已发布的 qtbase/6.11.1 线 PrintSupport=OFF 且 FEATURE_dbus=OFF。
   - 打印：patch 0001/0003/0004/0005/0006 将 simple printing 子系统整体
     编译出（13 对源文件 + 3 个 ui + 链接行），DotGraphView 的
     print/printPreview/pageSetup 保留为导出的 no-op（API 稳定），part
     不再创建打印动作并从 .rc 移除。
   - D-Bus：patch 0001（find_package 组件）/0008（adaptor codegen）/
     0009（main.cpp 单实例流程改为直接开窗）/0010（服务注册删除）。
     平台先例：kio/knotifications USE_DBUS=OFF（沙箱无 session bus）。

### 为什么不用 DBus-enabled 的 qtbase/6.11.1.2（r4 实测）

r4 曾按 baloo/26.04.3 先例 override qtbase 到 6.11.1.2（DBus ON）：
依赖图通过，但 qtbase 版本变化使**所有已发布 KF6 包的 package_id 失效**，
conan --build=missing 触发全量源码重编，kcolorscheme/6.18.0 configure
Error 1 失败终止（Qt6GuiPrivate→XKB 缺失；全程无 3600s 超时事件）。
故回退到 qtbase/6.11.1 原生线（全部 KF6 发布二进制直接复用），
代价是 D-Bus 功能切除（如实记录于上）。qtsvg/qt5compat/6.11.1
与该线原生配对，直接复用。

3. **FindGraphviz 桥接（E447 cache-variable bridge）**
   上游自带 cmake/FindGraphviz.cmake（MOAB 版，module 模式，
   pkg-config hint + find_path/find_library + PACKAGE_VERSION 正则）。
   - graphviz 13 头文件无 PACKAGE_VERSION 字符串 → patch 0002 增加
     GRAPHVIZ_VERSION(_STRING/_MAJOR/_MINOR/_PATCH) 回退链；
   - 交叉编译下 pkg-config/find* 看不到 conan 包 → generate() 预定义
     Graphviz_INCLUDE_DIRECTORIES 与 Graphviz_{GVC,CDT,GRAPH,PATHPLAN}_LIBRARY
     缓存变量（绝对路径，isfile 守卫），module 据此创建的
     Graphviz::Graphviz IMPORTED target 即携带真实 .so 位置。

4. **显式链接闭包（implement-policy 第 5 条）**
   所有 host 依赖的 libdir 与 vendored staging libdir 以
   `-L` + `-Wl,-rpath-link` 写入 CMAKE_{EXE,SHARED,MODULE}_LINKER_FLAGS
   （toolchain 缓存变量，先于任何环境快照生效，CMake 链接行可复现）。
   禁止依赖 lld 隐式 DT_NEEDED 闭包。

5. **SONAME（E537/kio 先例）**
   CMake 无 Platform/HarmonyOS 模块，显式注入
   CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG，保证 libkgraphviewer.so.0
   与 vendored libKF6{Parts,XmlGui,JobWidgets,ConfigWidgets}.so.6 带
   DT_SONAME（CI L5a 门禁）。

6. **环境（E132/kio 先例）**
   libxml2/2.15.3 声明为依赖，llvm/lib 与依赖 lib 目录注入
   LD_LIBRARY_PATH；/system/lib64 前置解决沙箱 libc++_shared.so 遮蔽。

## 依赖版本轨（ohpcd 实况）

- 6.26 轨: qtbase/6.11.1（原生线）, qtsvg/6.11.1, qt5compat/6.11.1,
  graphviz/13.1.2, kconfig, kcoreaddons, ki18n, kservice, kwidgetsaddons,
  karchive, kcolorscheme, kguiaddons, kiconthemes, kitemviews,
  kwindowsystem, kio(KIOCORE_ONLY), ecm(tool), boost/1.90.0.3（仅头文件，
  spirit classic；与 graphviz 闭包 poppler 的 pin 一致）
- 6.18 轨: kcodecs（kconfigwidgets staging 依赖）; kxmlgui/
  kconfigwidgets/kjobwidgets/kparts 不进 conan 图（vendored staging）。

### 依赖图版本统一（r1-r6 实测，graph info 预检通过）

r1: qtsvg/6.11.1 钉 qtbase/6.11.1（最终采用该线）。
r2: graphviz 闭包内 zlib（graphviz 1.3.1.1 vs gd 1.3.1）→ override 到
1.3.1.1；后续 graph info 消解 fontconfig（cairo 2.18.1 vs pango
2.18.1.1 → 2.18.1.1）、expat（2.8.2 vs 2.8.2.1 → 2.8.2.1）、boost
（→ 与 poppler 一致的 1.90.0.3，spirit classic 头文件用法兼容）。
KF6 混轨最终以 vendored staging 消解（见上），不再需要任何 KF6
override。最终 `conan graph info` 零冲突后才进 CI。

## 排障检索记录（builder 排障优先级链命中）

- E277（vendored→staging；本例 SHARED 链式变体）、E447（Find 模块 cache
  变量桥接 + 版本正则修补）、E487（Qt6LinguistTools 缺失 →
  KF_SKIP_PO_PROCESSING=ON，kio/kxmlgui 先例）、E132（SDK lld
  libxml2.so.16）、E537（SONAME 显式标志）——worktree knowledge/graph
  只读命中。
- 仓库配方先例（archives/ 只读检索）：baloo/26.04.3（qtbase override
  思路，r4 实测全量重编失败后弃用，但 KF6 override 手法由此而来）、kxmlgui/
  6.18.0（其 OHOS 补丁验证了 kxmlgui 无 GlobalAccel/无打印可构建）、
  alligator/audiocd-kio（KF6 伞包 find_package 可用）。
- 设备 conan 缓存损坏一例（r3：harfbuzz/14.2.0.1 包条目在库但目录缺失，
  conan create 在 install 阶段 os.utime 崩 FileNotFoundError）→
  `conan remove "<ref>:*"` 后重建解决；已记入 manifest knowledge。

## r10 → r11 回修记录（vendored kparts：KUriFilter 缺失）

- r10 失败点（22:56 日志）：staging 链仅剩 kparts 一环编译失败——
  `kde-src/kparts/src/navigationextension.cpp:15:10 fatal error:
  'KUriFilter' file not found`（KF6Parts 目标内，其余翻译单元均过）。
- 排障（优先级链①②）：
  - 设备 conan 缓存全部 9 个 kio 包条目逐一核查：唯一含 payload 的
    kio/6.26.0（KIOCORE_ONLY）`include/KF6/KIOCore` 头文件清单里没有
    kurifilter.h / KUriFilter 转发头，`grep -ril urifilter` 全缓存 0 命中
    → 方向 (a)（补 include 路径/链接目标）不可行，平台确实不供给。
  - vendored kparts 6.18 源码内 `grep -rEn 'KUriFilter'`：仅
    navigationextension.cpp 引用（include + pasteRequest() 一处函数体）；
    `NavigationExtension` 类本身被 readonlypart.cpp/h 以
    `findChild<KParts::NavigationExtension*>()` 形式引用（public API），
    整文件剔除会引入 moc/链接不确定性 → 不整体剔除文件。
  - kgraphviewer 源码与 test_package `grep -rEn NavigationExtension` =>
    0 命中（不消费该扩展点，pasteRequest 行为变化无观测面）。
- 修复（patch 0015，最小可解释）：保留 navigationextension.cpp/h 编译与
  注册（零 API 变化），仅将 pasteRequest() 的 KUriFilter URL 过滤替换为
  `QUrl::fromUserInput(..., AssumeLocalFile)` 直开（上游无过滤器命中时
  的同款回退路径），`#include <KUriFilter>` → `#include <QUrl>`。
  补丁以 diff -u 对 6.18.0 原始 tarball 提取文件生成，GNU patch 与
  git apply 双验证可干净应用。

## r11 → r12 回修记录（应用 configure：Qt6Svg 组件定位失败）

- r11 失败点：staging 链四环全部编译装出（patch 0015 生效，
  navigationextension.cpp 通过），首次推进到 kgraphviewer 应用自身
  configure——`CMakeLists.txt:36 find_package(Qt6 COMPONENTS Core Widgets
  Svg Core5Compat)` 报 `Failed to find required component "Svg"`，
  Qt6Config.cmake 期望 Qt6SvgConfig.cmake 位于 qtbase 包前缀内。
- 排障（优先级链①②）：
  - Qt6Config.cmake（qtbase 包）对组件配置只在其自身前缀内以
    NO_DEFAULT_PATH 搜索，不遍历 CMAKE_PREFIX_PATH（r11 实证：qtsvg 的
    lib/cmake 已在 CMAKE_PREFIX_PATH 上仍找不到）；该文件消费 Qt 官方的
    QT_ADDITIONAL_PACKAGES_PREFIX_PATH（158/164 行）。
  - 仓库配方先例命中：archives/a/alligator/26.04.0/conanfile.py 对
    (qtdeclarative, qtsvg, qtshadertools) 设置
    QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<包前缀>（generate() 实证）。
  - 设备 qtsvg 包（qtsvg71500288c3055）lib/cmake/Qt6Svg 存在，
    qt5compat 包同理承载 Qt6Core5Compat（r11 时 Svg 先失败，
    Core5Compat 未及搜索）。
- 修复：generate() 设
  QT_ADDITIONAL_PACKAGES_PREFIX_PATH=<qtsvg 包前缀>;<qt5compat 包前缀>
  （跟随 alligator 先例，取本配方实际依赖的两个 Qt 组件包）。

## r12 → r13 回修记录（应用编译：打印子系统残留引用）

- r12 失败点：QT_ADDITIONAL_PACKAGES_PREFIX_PATH 生效，Qt6Svg/
  Qt6Core5Compat 均解析成功，应用 configure 通过；编译期
  `dotgraphview.cpp:1699 no member named 'm_printCommand'`——patch 0004
  删除了 DotGraphViewPrivate::m_printCommand 成员，但遗漏了
  hideToolsWindows() 中的第二处使用点（此前各轮均未到达应用编译，
  该问题首次暴露）。
- 排障（优先级链①）：全源码扫描打印子系统残留引用
  （grep KGVSimplePrintingCommand/simpleprinting/QPrinter/PrintSupport）：
  - dotgraphview.cpp hideToolsWindows()（被 kgraphviewer_part.cpp:170
    调用，方法保留、函数体 no-op）；
  - KgvPageLayout.cpp `#include <QPrinterInfo>` +
    KgvPageFormat::defaultFormat() 使用 QPrinterInfo::defaultPrinter()
    （Qt6::PrintSupport 不可用，设备亦无打印机）→ defaultFormat()
    直接返回 PG_DIN_A4（上游无匹配分支的同款回退值）；其余命中仅为
    simpleprinting*（已编译出）与字符串/注释。
- 修复：patch 0004 以 diff -u 重新生成（追加 hideToolsWindows no-op
  hunk，往返验证）；新增 patch 0016（KgvPageLayout 无打印机 A4 回退，
  注册进 conandata.yml）。

## r15 → r16 回修记录（E537：soname-less 依赖的绝对路径 DT_NEEDED 泄漏）

- r15 里程碑：应用与 test_package 编译全部通过，测试真实执行。两类失败：
  ① 自建 OHOS ELF 断言拦截 libkgraphviewer.so.0 / libKF6Parts.so.6（进一步
  readelf 检查发现 4 个 vendored .so + app + plugin 全部）存在绝对路径
  DT_NEEDED；② bin/kgraphviewer --version 冒烟 rc=127（musl 重定位
  symbol not found）。
- 排障（优先级链①命中）：
  - 直接证据：readelf -d 显示泄漏项恰好是被消费的已发布包
    libKF6{ColorScheme,ConfigCore,ConfigGui,CoreAddons,GuiAddons,I18n,
    Service,WidgetsAddons}.so 与 libQt6Core5Compat.so——逐一核查它们的
    readelf：全部无 DT_SONAME → CMake 以绝对路径传链接输入、ld 原样
    记录路径（E537 完全同型；kio 自身的 NEEDED 还带着构建机
    .cache/conan2 的过期绝对路径，平台既有状态）。
  - knowledge/graph E537（kpackage !6997 先例）：链接期 basename 修复；
    patchelf 事后改写在 HMDFS 上运行期被拒（forbid），只能链接期做。
  - 设备实验（tmp/soname-exp）：CMake 4.1.2 下 IMPORTED_NO_SONAME/
    IMPORTED_SONAME stamp 不改变链接行；把 IMPORTED_LOCATION(_RELEASE)
    改写为裸文件名后链接行出现裸 `libKF6ColorScheme.so`（-L 显式闭包
    由配方 linker flags 提供）。
- 修复（0017-0021，同一 fixup 块追加到 5 个 consumer CMakeLists 末尾）：
  app 根 CMakeLists（0017）、vendored kparts/kxmlgui/kconfigwidgets/
  kjobwidgets 各自顶层 CMakeLists（0018-0021），把 11 个 soname-less
  导入目标（上列 9 个 + 防御性 ItemViews/WindowSystem，逐一 readelf 确认
  无 SONAME）的 location 改写为裸名。运行期由 LD_LIBRARY_PATH 按
  裸名解析（与 kio 等已发布包的 plain DT_NEEDED 同一机制）。

## r16 → r17 → r18 回修记录（E537 最终方案：patchelf 代理 + -L 引号修复）

- r16 失败：patch 0017 基于 stale 基线（未计入 0001 的行号偏移；Conan 内置
  patch 不做偏移搜索）→ 以 0001 应用后的状态为基线用 diff -u 重新生成。
- r17 失败：0017-0021 改写 IMPORTED_LOCATION 为裸文件名的方案在 clang
  驱动层不成立——裸 `libKF6X.so` token 被当作相对路径文件而非 -l 搜索
  （`clang-15: error: no such file or directory: 'libKF6WidgetsAddons.so'`）。
  实验同时证明：IMPORTED_NO_SONAME/IMPORTED_SONAME stamp 与
  IMPORTED_LOCATION 改写成 `-l<name>` 在本 CMake 4.1.2 均无效（后者被
  make 当成 target 依赖，"No rule to make target '-lKF6ConfigCore'"）。
- 关键发现（连锁根因）：配方 `_link_dirs` 生成的 `-L"path"` 内嵌引号经
  Conan toolchain 写入 `set(CMAKE_*_LINKER_FLAGS "...")` 后被 CMake 按多参
  解析，产生 `-L;` 断裂与带尾引号的无效目录——**此前所有轮次的 -L 闭包
  实际从未生效**（链接一直靠导入目标绝对路径输入，未暴露）；引入 -l 项
  后立刻暴露。实现策略 5 的显式闭包必须配对有效 -L。
- 最终方案（E537 变体，全部实验验证）：
  1. `_link_dirs` 去引号（conan 缓存路径无空格）→ -L 闭包首次真正生效；
  2. 生成的 conan_cmakedeps_paths.cmake（CI 定制 toolchain 在每个工程——
     主构建 + 4 个 vendored staging——include 它）注入 find_package 宏钩子：
     每次配置后把 11 个 soname-less 导入目标（CoreAddons/I18n/ConfigCore/
     ConfigGui/ColorScheme/GuiAddons/WidgetsAddons/Service/ItemViews/
     WindowSystem/Qt6Core5Compat，逐一 readelf 确认无 SONAME）的
     IMPORTED_LOCATION 换成构建目录内 `ohos-soname-proxies/` 私有副本
     （`patchelf --set-soname <basename>`，/data/service/hnp/bin/patchelf）；
     ld 读取代理的 SONAME → DT_NEEDED 只记裸名（直接编译验证：
     -L<dir> -lKF6ConfigCore ⇒ NEEDED [libKF6ConfigCore.so]）；运行期
     LD_LIBRARY_PATH 按裸名解析到真实发布库。代理仅作链接输入，永不发布
     （E537 forbid：patchelf 改写文件在 HMDFS 运行期被拒）。
  3. test_package 注入同一钩子（其 paths 文件由自身 generate 写出）。
  - 撤销 0017-0021 五个补丁（方案被上述取代）。
- 知识检索命中：knowledge/graph E537（本机只读），alligator/26.04.0
  （QT_ADDITIONAL_PACKAGES_PREFIX_PATH，r12 修复），kpackage/6.26.0
  patches/0005（E537 裸 -l 手法来源）。

## r19 → r23 最终记录（运行期门禁打通 + CI 全绿）

- r19 失败：test() 重构残留 `env.define(...)`（NameError，line 291）——
  运行环境改为直接写 os.environ 后旧 Environment 残行未清。
- r20：冒烟 rc=0（offscreen QApplication 构建通过）；ctest 的测试二进制
  失败——`QPluginLoader::instance()` 返回的是 KPluginFactory（插件根
  对象），直接 qobject_cast<KParts::ReadOnlyPart*> 必然失败；改为
  `qobject_cast<KPluginFactory*>` + `factory->create<KParts::ReadOnlyPart>()`
  （KParts 插件标准布局，补 #include <KPluginFactory>）。
- r21：smoke rc=0 + ctest 100% 通过；显式第二遍运行 rc=127——
  self.run(cwd=ohos-runtime/cwd/x) 下二进制路径须为绝对（相对路径
  ./test_kgraphviewer 在 runtime cwd 下不存在）→ os.path.abspath。
- r22：test_package ALL PASSED（smoke rc=0 / ctest 100% / 显式 rc=0 /
  ELF 断言全过），但 CI L5b 门禁拦下 libKF6ConfigWidgets.so.6 的绝对
  DT_NEEDED：/p/kcode9da5b50c2debb/.../libKF6Codecs.so——KF6::Codecs
  也是 soname-less 发布依赖（readelf SONAME=0 确认），此前清单遗漏。
  OHOS_SONAME_LESS_DEPS 补入 KF6::Codecs。
- r23：权威 CI 全绿（CI_EXIT=0）：G0/KC/JC pass；L0 pass；L1 pass
  （upstream tests + test_package executed）；L2 skip（CI 自带
  version/help 探测在无运行环境注入时无法拉起 GUI KDE 应用——L2 语义
  由 test_package 冒烟 rc=0 等价覆盖）；L4 warn（CI 静态扫描正则
  `(strcpy|sprintf|gets|strcat)\b` 只有尾部词边界、缺前导词边界，误匹配
  补丁上下文中以 "gets" 结尾的标识符——Widgets/KF6::JobWidgets/
  KF6::KIOWidgets/KF6PartsTargets/KgvUnitWidgets.cpp，命中 0001/0003/
  0007/0011/0014 五个补丁文件；全部补丁无真实 system() 调用，非本配方
  引入）；L5 pass；构建 100%（1/1）。
- 运行期环境设计（test_package test()，全部在测试沙箱内自包含）：
  LD_LIBRARY_PATH = 全部依赖 libdir + 被测包 lib + /system/lib64；
  运行 cwd = <build>/ohos-runtime/cwd/x 且 <build>/ohos-runtime/bin
  预置全部依赖库符号链接（吸收发布 kconfig 包 libKF6ConfigGui.so 的
  cwd 相对 DT_NEEDED ../../bin/libKF6ConfigCore.so——平台缺陷，另记）；
  QT_PLUGIN_PATH 指向 qtbase/qtsvg plugins；QT_QPA_PLATFORM=offscreen；
  HOME/XDG_* 指向测试私有目录。
- 设备环境修复（非仓库内容，已披露）：发布 KF6 库（kio/kconfig/
  kcolorscheme/kservice/kguiaddons/ki18n/kcoreaddons/kcrash/kwidgetsaddons/
  kiconthemes/kitemviews/kwindowsystem/kcodecs 时代混杂交错）携带指向
  旧 conan home 的机器本地绝对 DT_NEEDED；在
  /storage/Users/currentUser/.cache/conan2/p/ 为现存于当前
  .conan2/p/ 的同 hash 包目录建立兼容符号链接（可逆；r3 conan 缓存
  修复同类先例）。平台级缺陷（发布包带机器本地绝对 NEEDED、迁移期
  双 home 混杂）建议沉淀知识条目。
