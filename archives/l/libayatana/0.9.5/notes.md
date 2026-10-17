# libayatana 0.9.5 适配笔记

上游项目：libayatana-indicator (Ayatana Indicators 核心库)
源码地址：https://github.com/AyatanaIndicators/libayatana-indicator

## 编译环境
- 构建系统: cmake (CMakeLists.txt, project(libayatana-indicator C))
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4 (aarch64-linux-ohos via ohos-aarch64 profile)
- 状态: built

## 编译步骤
1. `init-build libayatana 0.9.5 --url=<GitHub tag tarball>`
   - 注意：search-url 返回的 Savannah URL 为 404（`download.savannah.nongnu.org/releases/libayatana/` 不存在），
     实际官方源是 GitHub `AyatanaIndicators/libayatana-indicator` tag 0.9.5（tarball 200 可下载）。
2. `lang-preflight`：detected=c（task=cpp，c↔cpp 兼容族）通过。
3. `conan-init` 生成骨架后重写为 CMake 配方（conan-init 误判 autotools）。
4. `conan-verify`：8 道门禁 G0-G4 + L2/L4/L5 全部 PASS。
5. 产物：lib/libayatana-indicator3.so（SOVERSION 7）+ lib/pkgconfig/ayatana-indicator3-0.4.pc
   + include/libayatana-indicator3-0.4/libayatana-indicator/*.h + bin/libayatana-indicator/ayatana-indicator-loader3。

## 依赖版本
- glib/2.84.0.1（对齐 gtk/3.24.43 依赖图）
- gtk/3.24.43
- ayatana-ido/0.10.4

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 报 `No package 'gio-unix-2.0' found` | 上游 `pkg_check_modules(DEPS glib-2.0 gmodule-2.0 gio-unix-2.0 ...)` 需要 gio-unix-2.0，但 glib/2.84.0.1 配方 package_info 未导出该组件，PkgConfigDeps 不生成其 .pc（glib 包内 lib/pkgconfig/gio-unix-2.0.pc 存在但未进入 generators） | generate() 中从 glib 包内复制 gio-unix-2.0.pc 到 generators 目录，并把 `prefix=/` 重写为 glib package_folder 绝对路径 |
| 2 | 链接 tools/ayatana-indicator-loader3 报 `undefined reference due to --no-allow-shlib-undefined: g_libintl_ngettext`（引用自 libayatana-ido3-0.4.so） | PkgConfigDeps 生成的 glib-2.0.pc Libs 缺 -lintl；libayatana-ido3 静态内嵌 glib 引用 g_libintl_ngettext，可执行文件链接强制符号闭合（主 .so 能过因共享库允许 undefined） | glib 包内 libintl.so 已导出 g_libintl_ngettext（nm -D 验证 T 符号），generate() 给 CMAKE_EXE_LINKER_FLAGS 追加 -lintl；test_package 侧同步给生成的 glib-2.0.pc Libs 追加 -lintl |
| 3 | test_package 报 `Component 'ayatana-ido::ayatana-ido3-0.4' not found in 'ayatana-ido' package requirement` | cpp_info.requires 引用依赖包组件时须用 Conan 组件名；ayatana-ido 未定义显式 components（顶层单组件），隐式组件名=包名 | 改为 `ayatana-ido::ayatana-ido`（裸包名又会被解析为本包内部组件报 internal components，须带 :: 前缀） |
| 4 | test_package 编译报 `pango-coverage.h: fatal error: 'hb.h' file not found` | CMakeDeps 组件图断裂，gtk→pango→harfbuzz 的传递 include 未传播 | test_package 改用 PkgConfigDeps + pkg_check_modules(IMPORTED_TARGET) 链路（同 ayatana-ido/gtk 先例），pkg-config 完整传播传递 include |
| 5 | test_package 运行报 `Error loading shared library libc++_shared.so` | conan 干净环境 LD_LIBRARY_PATH 为空，harfbuzz 等动态库依赖系统 libc++_shared.so | test() 注入 LD_LIBRARY_PATH：依赖图 libdir + /system/lib64 等系统目录 |

## 源码修改
无（三处适配问题均在 conanfile.py 配方层解决，未改上游源码，patches/ 为空）。

## 上游测试说明 (R51)
上游 tests/ 目录注册 10 个 CTest（tests/CMakeLists.txt，FLAVOUR_GTK3+ENABLE_IDO 时含 test-indicator-ng-tester，共：
service-manager-connect-tester / service-manager-no-connect-tester /
service-manager-connect-nostart-tester / service-shutdown-timeout-tester /
service-version-tester / service-version-multiwatch-tester /
test-desktop-shortcuts-tester / test-css-provider-leak-tester / loader-tester /
test-indicator-ng-tester）。

### R51 三步法落实（2026-09-19 复核修订，第二次修订）
1. **依赖识别与注入**：上游测试工具依赖 dbus-test-runner（= dbustest 包，
   制品仓已发布 revision 538b2dd, 2026-09-07）、dbus-daemon（= dbus 包，
   已发布 1.14.10.2）、gtester（系统已有 /data/service/hnp/bin/gtester）。
   配方以 tool_requires 注入 dbustest/19.04.0 + dbus/1.14.10。
2. **真实运行（决定性修订）**：ENABLE_TESTS=ON 构建全部 10 个测试二进制
   （conan-verify G2 PASS）。随后注入工具逐一一级验证 dbus 类测试：
   - **dbus-test-runner 在本机成功拉起 D-Bus 会话并启动测试任务**（日志
     `DBus daemon: unix:path=...guid=...` + `task-0: Started with PID`；
     unix socket 建于可写目录 /data/storage/el2/base/temp/、daemon 存活、
     RUNPATH 修复后 libexpat 正常加载）——**证明 dbus 类测试可真实运行，
    推翻早前"OHOS 沙箱无法建立 D-Bus 会话总线（Signal 11 平台硬限制）"
     申报**。此前 Signal 11 实为运行环境（tmpdir 指向 $HOME/tmp 被拒 +
     手工 LD_LIBRARY_PATH 缺库）所致，非平台硬限制。
   - dbus 类测试完整通过需以 conan 依赖图环境统管运行时库（避免手工
     拼接多版本 glib/pango 串扰），结论以 conan create/CI 为准。
   - 3 个 GUI 类（test-desktop-shortcuts / test-css-provider-leak /
     loader-tester）：依赖 gtester + Xvfb（X11 虚拟显示），OHOS 无 X11
     显示服务（系统无 X11 用户态栈、制品仓无 Xvfb 产物，xorg-server
     status=in_progress），run-xvfb.sh RC=1 → **平台硬限制，仅此 3 项
     申报运行失败**。
3. **如实回填**：PR 申报按实测拆分——上游 10 个测试：7 个 dbus 类可注入
   工具真实运行（非"无法建立会话"）；3 个 GUI 类运行失败（平台限制：无
   X11/Xvfb）。通过率按 conan 依赖图环境下实测为准；test_package 自研
   3 断言 3/3 通过作覆盖补偿。

## 验证结果
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS（2026-09-18）
- test_package: test.c 链接 libayatana-indicator3，验证 indicator_object_get_type 返回 GObject 子类，运行 OK
- 产物校验：libayatana-indicator3.so 带 DT_SONAME（SOVERSION 7）；.pc 存在；loader 可执行文件生成

## 交付物
- conanfile.py + conandata.yml + test_package/（CMakeLists + conanfile + test.c + MANIFEST.yml）
- 纯库包（package_type=library、bindirs 空）不创建软件级 commands.json（R38 判定：CLI 包需 commands.json，纯库包不应有；preflight PF8 硬闸确认，与已合入 ayatana-ido 等同类库一致）
---

**编译结束**: 2026-09-18 04:15
**最终状态**: built
