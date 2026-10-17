# ayatana-indicator-messages 24.5.2 — 适配笔记

## 上游信息
- 仓库: https://github.com/AyatanaIndicators/ayatana-indicator-messages
- 版本: 24.5.2（上游 git 仓库无此 tag，最新 tag 24.5.1；24.5.2 为
  Debian/Ubuntu/Kali 已打包的上游发布，ChangeLog 对应，PROJECT_VERSION=24.5.2）
- 源码: `ayatana-indicator-messages_24.5.2.orig.tar.gz`（Ubuntu archive 官方
  orig tarball，2026-06-12 上游 mtime），sha256=`a1304d2d28fde2912a91741856b2b6b2242d3b508f2666412b37a35005b3664b`
- 构建系统: CMake（min 3.13，C/C++）

## 功能定位
消息菜单系统指示器服务：聚合各应用（telepathy/libnotify 等）的消息到
`org.ayatana.indicator.messages` 菜单。产物：
- `ayatana-indicator-messages-service` 可执行（安装到
  `libexec/ayatana-indicator-messages/`，GNUInstallDirs 在 OHOS 上 LIBEXECDIR 取 bin）
- `libmessaging-menu.so`（SHARED）+ messaging-menu.pc + 头文件

## OHOS 适配要点
1. **依赖**（顶层 CMakeLists `pkg_check_modules(PROJECT_DEPS REQUIRED ...)`）：
   - `glib-2.0>=2.36` / `gio-unix-2.0>=2.36`（制品仓 glib/2.88.0.1）
   - 通过 PkgConfigDeps 生成 .pc（CMakeToolchain 自动注入 PKG_CONFIG_PATH）
2. **accountsservice 裁剪**（0001+0002 补丁，核心难点）：
   - 上游顶层把 `accountsservice` 列入 REQUIRED；仓库与制品仓均无此配方
     （OHOS 无 AccountsService 系统守护进程的客户端库）
   - 0001：`ENABLE_ACCOUNTS_SERVICE`（默认 ON，配方设 OFF）→ 不再 REQUIRED，
     找到时把 include/lib 追加进 PROJECT_DEPS 并定义 HAVE_ACCOUNTS_SERVICE
   - 0002：im-accounts-service.c 以 `#ifdef HAVE_ACCOUNTS_SERVICE` 包裹
     act/act.h 实现；OFF 时编译 stub——ref_default 返回空 GObject、
     set_draws_attention 为 no-op、get_show_on_greeter 恒 FALSE
     （产品消息菜单核心逻辑不受影响）
3. **SKIP_DATA_PO=ON**（0001）：data/CMakeLists 用 `find_package(GSettings)`+
   `add_schema`、po/CMakeLists 用 `find_package(Intltool REQUIRED)`，
   OHOS 均无这些 CMake 模块 → 跳过 data/ 与 po/（与 libayatana-common 同法）
4. **SKIP_DOC=ON**（0001）：doc/reference 用 gtkdoc-scan/gtkdoc-scangobj，
   OHOS 无 gtk-doc 工具 → 跳过
5. **ENABLE_INTROSPECTION=OFF**（0003）：libmessaging-menu/CMakeLists 用
   `find_package(GObjectIntrospection REQUIRED)` + `find_package(Vala REQUIRED)`
   生成 MessagingMenu-1.0.gir/.typelib/.vapi——OHOS 制品仓无
   GObjectIntrospection/Vala 工具链，跳过（只构建并安装 libmessaging-menu.so
   及其 .pc/头文件，桌面语言绑定非核心）
6. **ENABLE_TESTS=OFF**：主构建保持 OFF（上游默认）。审查要求测试真实
   执行 → test_package build() 拉上游源码真实编译运行 test-gactionmuxer
   （6/6 PASSED，gtest-run.log 证据，探针断言）；indicator-test / test-client
   因 dbustest-1 / GI 工具链不可得，提供 OHOS 适配方案（见"上游测试"节）

## 上游测试（真实统计）
- `tests/indicator-test.cpp`：**4 个 TEST_F**（RootAction / SingleMessage /
  MessageReply / IconNotification），端到端 DBus 集成测试：spawn 真实
  `ayatana-indicator-messages-service` 进程 + dbusmock 的
  org.ayatana.indicator.messages 服务，断言菜单树 root/message/reply/icon。
  依赖 GTEST + GMock + `pkg_check_modules(DBUSTEST REQUIRED dbustest-1)`
  （tests/CMakeLists.txt）。**OHOS 适配方案**：dbustest-1 为上游测试专用
  D-Bus mock 框架，制品仓无配方、上游（AyatanaIndicators/libdbustest）
  源码不可得（仓库 404）→ 当前不可真实执行；后续引入自制 libdbustest 包
  （依赖 gtest/gmock/dbus-glib，制品仓均有）后可执行。
- `tests/test-gactionmuxer.cpp`：**6 个 TEST**（Sanity / Empty / AddAndRemove /
  ActionAttributes / Signals / ActivateAction），对 src/gactionmuxer.c 的
  纯逻辑单元测试，依赖 GTEST/GMOCK——**OHOS 真实执行**：test_package
  build() 拉上游源码，用制品仓 gtest/1.17.0+gmock/1.17.0 编译运行，
  **6/6 PASSED**（gtest-run.log 证据，探针断言）。关键点：gactionmuxer.c
  编译需 `-DG_LOG_DOMAIN="Ayatana-Indicator-Messages"`（与上游
  src/CMakeLists.txt:42 一致），否则 g_test_expect_message 匹配不到日志域。
- `tests/test-client.py`：**2 个测试方法**（test_registration / test_status），
  经 GI typelib 调用 libmessaging-menu 客户端。**OHOS 适配方案**：typelib 需
  ENABLE_INTROSPECTION=ON + gobject-introspection 工具链生成（制品仓有
  gobject-introspection/1.78.1，主配方当前 OFF 裁剪桌面绑定）；后续启用并
  重建 libmessaging-menu 后可执行。
- `tests/indicator-messages-service-activate.c`：55 行辅助激活程序（非测试断言）。
- `tests/CMakeLists.txt` 另含 `cppcheck` 静态分析 target（--enable=all），
  OHOS 无 cppcheck 工具链，未运行。
- 适配后 test_package 端到端验证（2 项）：① service 可执行文件存在 +
  conanrun 环境启动（deps linked）；② 上游 test-gactionmuxer 真实执行
  6/6 PASSED（探针断言 gtest-run.log）。

## 产物
- `libexec/ayatana-indicator-messages/ayatana-indicator-messages-service`（可执行）
- `lib/libmessaging-menu.so`（SHARED）
- 运行时依赖：glib/gio（经 conanrun 注入）
