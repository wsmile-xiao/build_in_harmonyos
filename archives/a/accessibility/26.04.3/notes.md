# notes — accessibility 26.04.3 (HarmonyOS PC；上游产品 accessibility-inspector)

## 身份与来源

- 上游: https://invent.kde.org/accessibility/accessibility-inspector
  （KDE Accessibility 组；run_key `accessibility-26.04.3` 无伞形归档，
  本包为组内与名字唯一对应的官方 tarball，KDE Gear 26.04.3）
- 归档: https://download.kde.org/stable/release-service/26.04.3/src/accessibility-inspector-26.04.3.tar.xz
- SHA256: c25dec84fc29a0449ce07108ed6e2643342b322cd713b0656d3ac181b47cc77f
  （设备端 sha256sum 实算）
- license: LGPL-3.0-or-later（LICENSES/ 目录 + REUSE.toml；main.cpp 中
  KAboutLicense::LGPL_V2 为上游笔误，文件头 SPDX 均为 BSD-2/LGPL-3）
- 包名说明（2026-09-08 重命名重构）：conan 包名与包目录名为
  `accessibility`（平台任务认领名）。原候选以 accessibility-inspector
  命名；因 PR 流水线门禁 L0n（分支名去前缀后须精确等于
  {包名}-{版本}）与 L0m-4（conanfile.name 须等于包目录名），且平台
  任务分支固定为 feat/accessibility-26.04.3，故包名重构为
  accessibility。上游产品不变：源码 tarball 仍为
  accessibility-inspector-26.04.3.tar.xz（URL/SHA256 不动），交付
  二进制仍为 bin/accessibilityinspector（test_app.sh 对
  `accessibilityinspector 26.04.3` 输出的断言保留）。

## 产物

- bin/accessibilityinspector —— AT-SPI 无障碍树查看器（Qt6 Widgets GUI）
- lib/libaccessibilityinspector.so.1 —— 内部 helper 库（非公共 API）

## 适配要点

1. C++20：上游 CMAKE_CXX_STANDARD 20；CI profile cppstd=17 → 配方内
   CMAKE_CXX_STANDARD=20 + CMAKE_CXX_FLAGS=-std=c++20 覆盖
   （kdbusaddons 6.29.0 先例，不改全局 profile）。
2. 依赖闭包（全部为 ohpcd 已发布制品）：
   - qtbase/6.11.1.1（override=True 统一全图到含 DBus 的 Qt6.11.1.1）
   - KF6 6.14.0 闭包：kcoreaddons、ki18n、kconfigwidgets、kxmlgui、
     kcrash + 传递面（kconfig/kcolorscheme/kcodecs/kguiaddons/
     kiconthemes/kitemviews/kwidgetsaddons/kwindowsystem/knotifications/
     karchive）+ qtsvg/6.11.1（calligra 24.12.3 验证过的集合）
   - kdbusaddons/6.29.0：唯一发布在 6.29 线的 DBusAddons（构建于
     qtbase/6.11.1.1，与本配方钉的同 ref，无版本冲突）
   - qaccessibilityclient/0.6.0：上游 REQUIRED 的 QAccessibilityClient6，
     本 run 新增配方（同 run 依赖，先 conan export 本地消费；制品仓
     发布走 release 流水线）
   - extra-cmake-modules/6.29.0（tool）
3. KF_SKIP_PO_PROCESSING=ON：ki18n_install(po) 需要 gettext/msgfmt，
   OHOS 无 gettext 工具链；po→mo 跳过不影响功能（calligra 先例）。
4. ECM_MODULE_PATH / find-modules 手工注入（FindKF6 伞形解析）、
   QUERY_EXECUTABLE=qtpaths6（ECMQueryQt 的 Qt6::qtpaths 在本 qtbase
   布局下不可解析，mobipocket 先例）、conan_cmakedeps_paths.cmake
   手工生成（qtbase cmake_find_mode=none）。
5. 链接期 soname（E537 类，本 run 实测沉淀）：OHOS CMake 平台模块不
   定义 SONAME flag → 库无 DT_SONAME、消费者记录路径形 DT_NEEDED。
   配方以 CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname, 打开，
   libaccessibilityinspector.so 带 SONAME `libaccessibilityinspector.so.1`，
   app 二进制记录裸名并以 CMAKE_INSTALL_RPATH（$ORIGIN/../lib + 依赖
   包 lib 目录）解析。
   更正（2026-09-04 归档探针，reports/builder/probe-soname-sign/）：
   patchelf 后处理并非不可行——naive 路径（改后不重签）报
   Operation not permitted (rc=126)；未先 remove-section .codesign 直接
   binary-sign-tool 重签报 `.codesign section already exists` → SignElf 29
   （即 E077 forbid_2 记载的失败模式）；按 E077 四步流程
   （remove-section → patchelf → sign -selfSign 1 → chmod）后 exec 与
   dlopen 均正常。本 run 仍选链接期修复（producer 侧一次修复、无需逐
   产物重签），E077 流程作为 post-link 合规 fallback。
6. test_package 采用 calligra 24.12.3 的 link-farm + 绝对路径物化方案，
   兼容已发布 KF6 库内部的 `../../bin/...` 路径形 DT_NEEDED（已发布的
   kconfig/kiconthemes 库实测存在）。

## 上游测试

- src/autotests/ 4 个 QtTest 目标（mainwidgettest、
  accessibletreeviewtest、accessibletreewidgettest、
  propertytreeviewtest），BUILD_TESTING=ON 时经 ctest 在 build() 内
  真实运行（offscreen QPA，--timeout 90）。
- 本机实测结果：**4/4 全部通过**（100% tests passed）。测试构造真实
  Qt Widgets 并经 QAccessibilityClient 走 AT-SPI 客户端代码路径；
  offscreen 平台下无显示依赖，Widget/模型层断言不依赖活动 a11y 总线。
- a11y 总线穷尽证据（与 qaccessibilityclient/0.6.0 同）：dbus daemon
  在制品包与系统均不存在；at-spi2-core registryd 依赖 daemon；qtbase
  未发布 accessibilitybridges 插件 → GUI 壳可运行，树内容为空。

## 运行时功能边界（交付说明必读）

accessibility-inspector 是纯 AT-SPI 查看器：核心功能 = 经 D-Bus 连接
AT-SPI2 总线并展示"其它应用"的无障碍树。鸿蒙 PC 无桌面 a11y 总线，
默认只有 GUI 壳 + 空树可用；需用户级 `dbus-daemon --session` +
`at-spi2-core`（两者配方均已发布）才可能有内容，且内容取决于其它
OHOS 应用是否暴露 AT-SPI 接口。

## L2 smoke 说明

CI L2 以无环境变量方式直接执行 `bin/accessibilityinspector
--version/--help`：本包 NEEDED 中已发布 KF6 库为路径形条目（在构建机
conan cache 内可解析），但自有库与 Qt6 为裸 soname，需要
LD_LIBRARY_PATH/RPATH 才能解析；HarmonyOS 平台模块同样不支持
CMAKE_INSTALL_RPATH（实测未生效），故 L2 为 warn 非阻塞。真实消费
路径（test_package，带 conanrun 环境 + link-farm）已验证
`accessibilityinspector 26.04.3` 输出。终端用户运行需按交付说明设置
LD_LIBRARY_PATH 指向各依赖包 lib/ 目录（或随包部署）。

## CI 与上游测试结果（权威 CI，ci/conan/build_and_test.sh）

- 本包（accessibility/26.04.3）于 2026-09-08 包名重构后以最终 tree
  FULL 重跑权威 CI；CI_RC 与 L0n/L0i/测试证据行记录于本 run
  reports/builder/split-plan.md（PR2 节）。
- 依赖 qaccessibilityclient/0.6.0 已发布制品仓（ohpcd），L0i 全部自
  registry 解析，无 same-run 本地豁免。
