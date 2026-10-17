# libayatana-indicator 0.9.4 — 适配笔记

## 上游事实（全部基于 0.9.4 自身 tarball 逐项核实，非 0.9.5 推断）

- 源码: `https://github.com/AyatanaIndicators/libayatana-indicator/archive/refs/tags/0.9.4.tar.gz`
  sha256 `a18d3c682e29afd77db24366f8475b26bda22b0e16ff569a2ec71cd6eb4eac95`
  （本地 `.tmp-src/libayatana-indicator-0.9.4.tar.gz` sha256sum 实测一致）
- License: **GPL-3.0-only**（源码树 COPYING 为 "GNU GENERAL PUBLIC LICENSE Version 3"；上游 CMakeLists 无 LGPL 声明）
- 构建系统: CMake >= 3.13（`cmake_minimum_required(VERSION 3.13)`）
- 根 CMakeLists DEPS（pkg-config）:
  `glib-2.0 >= 2.37`、`gmodule-2.0`、`gio-unix-2.0`、
  `gtk+-3.0 >= 3.24`（FLAVOUR_GTK3 默认 ON）、
  `libayatana-ido3-0.4 >= 0.8.2`（ENABLE_IDO 默认 ON）
- 子目录: src/ data/ tools/（ENABLE_LOADER）tests/（ENABLE_TESTS）
- 安装产物（FLAVOUR_GTK3 + ENABLE_IDO + ENABLE_LOADER，GNUInstallDirs）:
  - `lib/libayatana-indicator3.so` + `ayatana-indicator3-0.4.pc`
  - `include/libayatana-indicator3-0.4/libayatana-indicator/` 下 **7 个公共头**:
    desktop-exec.h indicator-desktop-shortcuts.h indicator-image-menu-item.h
    indicator-ng.h indicator-object.h indicator-service-manager.h
    indicator-service.h（另安装 indicator-enum-types.h/indicator-marshal.h 生成头到同目录，公共 API 计 7）
  - `libexec/libayatana-indicator/ayatana-indicator-loader3`（tools/）
  - `share/libayatana-indicator/80indicator-debugging`（data/）
- 上游测试（tests/CMakeLists.txt, ENABLE_TESTS=ON 时）:
  **9 个 ctest 条目**（我们构建形态 FLAVOUR_GTK3=ON + ENABLE_IDO=ON 下全部注册）:
  1. `service-manager-connect-tester`
  2. `service-manager-no-connect-tester`
  3. `service-manager-connect-nostart-tester`
  4. `service-shutdown-timeout-tester`
  5. `service-version-tester`
  6. `service-version-multiwatch-tester`
  7. `test-desktop-shortcuts-tester`
  8. `test-indicator-ng-tester`（FLAVOUR_GTK3 AND ENABLE_IDO 才注册）
  9. `loader-tester`
  其中 6 个 service-* tester 依赖 `dbus-test-runner` + `dbus-daemon` +
  session bus；3 个 *-tester 脚本内部用 `gtester` 包装 + `run-xvfb.sh`
  （Xvfb）。g_test 可执行本体与用例数（逐文件数 g_test_add_func /
  indicator_ng_test_add 宏）:
  - `test-loader`: **11 用例**（ref_and_unref / filename_bad / dummy/null_load /
    blank_load / simple_load / simple_accessors / simple_location / signaler /
    entry_funcs / entry_func_window / visible）
  - `test-desktop-shortcuts`: **4 用例**（creation / globalnosho / nicknames / launch）
  - `test-indicator-ng`: **3 用例**（non-existing / instantiation /
    instantiation-with-profile；g_test_dbus 自建私有 bus，需 dbus-daemon 二进制）
  另有 test-vg valgrind 包装（add_test 未注册,不计入）。
  注: 早期草稿记 test-loader 6 用例 / test-indicator-ng 2 用例为误,
  以本次逐行清点为准（11 / 4 / 3, 共 18 个 g_test 用例）。
  **上游正式逻辑测试总数 = 18 个 g_test 用例 + 6 个独立 service-*
  CTest tester = 24**（CTest runner 数不与内部 g_test 重复相加）。

## 0.9.4 vs 0.9.5 源码差异（逐行 diff 已核实）

- 0.9.4 src/CMakeLists.txt 链接行为与 0.9.5 相同结构:
  `target_link_libraries(ayatana-indicator3 ${PROJECT_DEPS_LIBRARIES} ...)` —
  pkg_check_modules 只产 -l 裸名单，`_LIBRARY_DIRS` 的 -L 目录从未进链接行。
  （0.9.5 后续版本把变量改名为 PROJECT_DEPS_LINK_LIBRARIES，语义不变。）
- set_target_properties: 0.9.4 的 VERSION 7.0.0 / SOVERSION 7 无版本化守卫
  （0.9.5 同值加了 if(NOT ANDROID) 守卫；HarmonyOS 平台 CMake 不产
  soname flag 的问题两版根因一致）。
- 0.9.5 增 css-provider-leak 测试（gcem 专项），0.9.4 无 → 0.9.4 ctest 计 9。

## OHOS 适配（conanfile.py 内处理，无源码补丁）

1. **-L 注入**: 遍历依赖图收集全部 package libdir，追加到
   CMAKE_SHARED_LINKER_FLAGS / CMAKE_EXE_LINKER_FLAGS（与
   ayatana-ido/0.10.4 的 pkg-config _LIBRARY_DIRS 丢失同根因）。
2. **soname 注入**: CMAKE_SHARED_LINKER_FLAGS 追加
   `-Wl,-soname,libayatana-indicator3.so.7`；package() 内复制
   `libayatana-indicator3.so` → `libayatana-indicator3.so.7`（HMDFS 软链
   不可靠，用复制；同 ayatana-ido 先例）。
3. **gio-unix-2.0.pc**: glib 配方无 gio-unix-2.0 组件，PkgConfigDeps 不生
   成该文件 → 复制 glib 包内原始 .pc 改写 prefix（同 accountsservice /
   libayatana-indicator 0.9.5 模式）。
4. **glib-2.0.pc -lintl**: 依赖链共享库引用 g_libintl_ngettext 而
   PkgConfigDeps 生成的 glib-2.0.pc 无 -lintl → 追加（gtk/ayatana-ido
   先例同根因）。
5. **glib-mkenums / glib-genmarshal**: find_program 会命中 CI runner
   /data/service/hnp/bin 下断链符号链接 → 显式注入 glib 包 bin 内真实
   路径 + PATH 前置。
6. **static 不支持**: 上游 add_library 硬编码 SHARED（无 BUILD_SHARED_LIBS
   分支）；核心 API indicator_object_new_from_file() 运行时 g_module_open
   dlopen 指示器插件 → validate() 拒绝 shared=False（不伪造支持）。

## 状态

- [x] conandata.yml / conanfile.py / manifest.yaml / notes.md
- [x] test_package（Task #4: 6 个消费者 g_test + 1 项 HarmonyOS ELF 专项）
- [x] ohos-aarch64 conan create shared=True（Task #5: rc=0,
      package_id 2ac3f268672507aadbbd31130c0dee0a810fff47,
      rrev 48f7679ae83670b0d7b106ac121f5afa）
- [x] 上游测试分类与执行（Task #6, 见下节）
- [x] 知识库决策（路径 A, 无新增; 见下节）

## 上游测试真实执行结果（Task #6, 2026-09-18）

在 `.tmp-src/upstream-tests-build` 用包构建同款环境（conan_toolchain +
conanbuild/conanrun env, ENABLE_TESTS=ON, FLAVOUR_GTK3=ON, ENABLE_IDO=ON）
独立构建上游 tests 目标后真实执行:

- **test-desktop-shortcuts: 4/4 PASS**（GDK_BACKEND=broadway + broadwayd :7
  无头显示, 直接执行测试二进制; 上游 tester 脚本里的 gtester 包装不可用
  —— conan 缓存中 gtester 无执行权限(共享 worker 文件系统 noexec 挂载),
  gtester 只是 TAP 包装器, 不影响测试本体语义）
- **test-loader: 11/11 PASS**（同上无头方案; 首跑 2 用例因 6 个
  dummy-indicator-*.so 测试插件未构建而 assert 失败——构建
  dummy-indicator-{blank,entry-func,null,signaler,simple,visible} 后
  11/11 全通过, 这是构建步骤问题非上游缺陷）
- **test-indicator-ng: 3 用例不可执行**——g_test_dbus 机制需 spawn
  `dbus-daemon` 二进制: `Failed to spawn child process "dbus-daemon"
  (No such file or directory)`。环境无 dbus-daemon（PATH / conan dbus
  1.14.10 包均无 daemon 二进制, libdbus 库包不含系统组件）,
  上游 tester 还叠加需要 dbus-test-runner。真实环境依赖缺失, 不伪造。
- **6 个 service-* tester: 不可执行**——需要 dbus-test-runner +
  dbus-daemon + /usr/share/dbus-test-runner/session.conf; 单独运行
  service-shutdown-timeout 等可执行本体 g_error: "Unable to get a
  connection to the session DBus ... Cannot spawn a message bus without
  a machine-id: Failed to open /var/lib/dbus/machine-id"。
  真实环境依赖缺失, 不伪造。

汇总: **24 个正式逻辑测试中 15 个真实通过, 9 个因 D-Bus 测试环境缺失
无法执行, 0 个执行失败**（11 loader + 4 desktop-shortcuts 通过;
3 indicator-ng 因 dbus-daemon 缺失 + 6 service-* 因
dbus-test-runner/dbus-daemon/machine-id 缺失未执行）。

适配后统计（逻辑测试用例统一口径）:
- 新增测试 7 个（6 consumer g_test + 1 HarmonyOS ELF 专项）, **7/7 PASS**
- 适配后逻辑测试总数 = 24 上游 + 7 新增 = **31**
- 实际 PASS = 15 上游 + 6 consumer + 1 OHOS = **22**
- 环境限制未执行 = **9**, 失败 = **0**

## test_package 消费者测试（6 个 g_test, Task #4/#5 已全 PASS）

覆盖（全部离线纯逻辑, 无需桌面 session/DBus/Xvfb/真实插件）:
1. `object-type-registered` — 4 个类型宏注册 + g_type_name 精确匹配
2. `object-lifecycle` — 类型元数据/class vtable（get_entries/get_location
   偏移）+ GObject ref_count 语义
3. `desktop-shortcuts-parse` — fixture 正向解析: nick 计数/has_open/
   has_save/Name="Open" 精确值/弱指针析构
4. `desktop-shortcuts-missing-file` — 失败路径: g_test_expect_message(NULL)
   捕获上游 g_warning, 对象构造成功 + get_nicks 安全返回空列表
5. `service-manager-construct` — 构造/connected()=FALSE/set_refresh/析构
   （无 main loop → 无 DBus 往来）
6. `service-type-only` — g_type_class_ref 触发 class_init 后
   g_signal_lookup("shutdown") 成功

测试设计经验（0.9.4 API 语义, 已逐行核实源码）:
- **裸 IndicatorObject 基类不可直接实例化**: indicator-object.c:118 是
  G_DEFINE_TYPE_WITH_PRIVATE（**非 abstract**）, constructed() 里 g_error
  "does not create an image or a label" → 实例化裸基类必 fatal（SIGTRAP）。
  测试改为类型元数据 + class vtable 验证, 不实例化。
- **0.9.4 nick_get_name 对非法 nick 是 g_return_val_if_fail(is_valid_nick)
  CRITICAL-by-design**（0.9.5 才加 NULL 检查）: 非法 nick 属编程错误路径,
  不是可断言的正常失败路径, 测试中不查询非法 nick。
- **上游 g_warning 用 NULL log domain**（库未定义 G_LOG_DOMAIN）:
  g_test_expect_message 第一个参数必须传 NULL, 传 G_LOG_DOMAIN 匹配不上
  → fatal。
- **g_signal_lookup 前必须 g_type_class_ref 触发 class_init**:
  信号注册发生在 class_init 的 g_signal_new, 只查类型不 ref class 时
  lookup 返回 NULL。
- **broadwayd 无头 GTK**: gtk 包 bin/broadwayd + GDK_BACKEND=broadway +
  BROADWAY_DISPLAY=:N, 供 gtk_init 无 X11/Wayland 环境（同时用于上游
  test-loader/test-desktop-shortcuts 真实执行）。

## conan create 结果（Task #5, shared=True）

- rc=0; 6 个消费者 g_test 全 PASS; CTest 1/1 PASS
- OHOS ELF 专项（test_package::test 内 3 处显式 self.run 真实执行）:
  库 ELF64 / Little-Endian / AArch64, SONAME libayatana-indicator3.so.7,
  无 RPATH/RUNPATH; NEEDED 34 项（gtk-3/gdk-3/gio-2.0/glib-2.0/
  ayatana-ido3-0.4/cairo/pango/harfbuzz/libc++_shared/libintl.so.8 等）
- 消费者 ELF64 Little-Endian AArch64(e_machine 183),
  NEEDED 含 libayatana-indicator3.so.7, 无 RPATH/RUNPATH 宿主路径
- **shared=False 未执行**: recipe validate() 明确拒绝——上游 0.9.4
  add_library 硬编码 SHARED 且核心 API 运行时 dlopen 插件, 设计为
  shared-only, 不为统计强行支持 static
- 本轮 **未新增任何源码 patch**

## 开发环境备注（非 OHOS 适配根因）

- 本机 `ci/conan/profiles/ohos-aarch64` 的
  `tools.build:compiler_executables` 硬编码 `/data/service/hnp/bin/clang`,
  当前机器该路径不存在（真实 clang 在 `/storage/Users/currentUser/
  usr/local/bin/`）。属**开发环境迁移问题**, 非 HarmonyOS 包适配根因:
  本次验证用 Conan 命令行 `-c tools.build:compiler_executables={...}`
  覆盖（命令行 conf 优先级高于 profile, CI 文件未改动, recipe 未写入
  任何机器路径）。CI 正式环境路径存在时无需此参数。
- conan 缓存 `/storage/Users/currentUser/.conan2/p/` 为共享 worker
  文件系统: 缓存内可执行文件（gtester 等）可能因挂载策略无执行权限,
  环境另有并行任务构建, 均与包适配无关。

## 知识库决策: 路径 A（无新增 DRAFT）

逐项判定本轮发现:

| 发现 | 判定 | 理由 |
|---|---|---|
| profile clang 路径不存在 | 环境, 不入库 | 开发机迁移问题, 非 OHOS 适配根因 |
| test.c 全角标点/`*/` 注释截断 | 测试代码问题, 不入库 | 自身笔误, 无跨包复用性 |
| 裸基类实例化 fatal | 上游 API 语义, 不入库 | 0.9.4 设计如此, 版本特定 |
| nick CRITICAL-by-design | 上游 API 语义, 不入库 | 0.9.4/0.9.5 版本差异 |
| NULL log domain 匹配 | 上游行为, 不入库 | 库未定义 G_LOG_DOMAIN |
| class_init 前信号不可查 | GObject 通用语义, 不入库 | 标准 GLib 行为 |
| broadwayd 无头 GTK | 已有方案, 不新建 | 与 ayatana-ido/0.9.5 同一手法复用 |
| gtester 缓存 noexec | 环境, 不入库 | 共享 worker 挂载策略 |
| dbus-daemon 缺失致 ng/service 测试不可跑 | 环境缺失, 不入库 | 非平台根因, 已如实记录 |

无新的 HarmonyOS 平台性、可跨包复用根因 → **路径 A**, 不创建 DRAFT。
（与 0.9.5 相同根因的 -L 注入/soname 复制/gio-unix-2.0.pc/-lintl/
glib-mkenums 五项已在 recipe 内处理并经本次真实构建验证, 归属既有
知识, 未重复造 draft。）
