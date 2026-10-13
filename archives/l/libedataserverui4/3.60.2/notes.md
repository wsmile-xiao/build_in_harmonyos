# libedataserverui4 3.60.2 适配笔记

## 定位
`libedataserverui4` **不是独立源码包**：它是 evolution-data-server 源码树
`src/libedataserverui` 的 GTK4 UI 便捷库（CMake target `edataserverui4`，
安装产物 `libedataserverui4-1.0.so`，头文件装到
`include/evolution-data-server/libedataserverui4/`）。上游没有单独的
libedataserverui4 tarball，因此源码取官方 evolution-data-server release
（R39）。

该库链接**同源码树内的内部库** `camel` / `ecal` / `edataserver` /
`edbus-private`；这些内部库在 ohpcd 中并未单独发布，所以配方构建整棵树，
把 UI 库与它所依赖的私有共享库一起打包。

## 编译环境
- 构建系统: cmake（顶层 CMakeLists.txt）
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 平台: HarmonyOS PC (OHOS aarch64)；构建机与目标机同架构，configure 期
  的 CHECK_C_SOURCE_RUNS 探针真实执行
- 状态: built

## 编译步骤
```
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing
```
只产出 GTK4 形态：`ENABLE_GTK4=ON` / `ENABLE_GTK=OFF`。WebKitGTK OAuth2、
libgweather、libcanberra 依赖在 ohpcd 未发布，全部关闭（见 manifest
configure_options）。

## 依赖图关键点（实测）
- `gtk4/4.22.4` 用 `override=True` 把全图 glib 钉到 `2.84.0.1.1`、zlib 钉到
  `1.3.1.1`。配方若用**普通** require 声明 glib，会与 pango/1.56.4 的
  `glib/2.84.0.1` 冲突（`Conflict originates from pango/1.56.4`）→ 必须也写
  `override=True`。
- `libsoup3/3.6.5-r3`（**不是 r1/r2**）：r1/r2 的 `libsoup-3.0.so` 把
  glib2/2.88.0 的 GObject 静态内嵌进去并导出符号（NEEDED 无 libgobject），
  与 gtk4 链的共享 glib 在同一进程加载即双份类型系统：
  `GLib-GObject-CRITICAL: cannot register existing type 'gchar'` → SIGABRT。
  r3 改为依赖共享 `glib/2.84.0.1.1`，是本图可用的唯一形态。
- `sqlite3/3.49.1`：必须与 libsoup3 发布的二进制所用版本一致（否则
  libsoup3 package_id 变化 → 触发源码重建）。
- `json-glib/1.10.6.1`：其远程二进制与本图 package_id 匹配；1.10.8 的二进制
  是按 glib 2.88 构建的，会落到源码重建。
- `libical3/3.0.20`（**不是 libical/4.0.1**）：libecal 需要 libical 的
  GObject 绑定 `libical-glib`，而 ohpcd 的 libical/4.0.1 是
  `LIBICAL_GLIB=OFF`（包内无 libical-glib.pc / 头文件），只有 libical3/3.0.20
  是 `ICAL_GLIB=ON`。
- `harfbuzz/14.2.0.1` 是本图唯一缺二进制的依赖（gtk4/4.22.4 的二进制绑定
  glib/2.84.0.1.1 链下的 harfbuzz pid，上游未发布该 pid），CI 的
  `--build=missing` 会按 meson 源码构建；本机需先 `pip3 install meson`
  （环境缺 meson 时 `conan install` 报 `meson: inaccessible or not found`）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Version conflict: glib/2.84.0.1 vs 2.84.0.1.1`（Conflict originates from pango/1.56.4） | 根级普通 require glib 与 gtk4 的 override 交互 | `self.requires("glib/2.84.0.1.1", override=True)` |
| 2 | `Version conflict: sqlite3/3.49.1 vs 3.53.4` | libsoup3 钉 3.49.1，配方声明的 3.53.4 与之冲突 | 对齐 3.49.1（也避免 libsoup3 源码重建） |
| 3 | `Component 'glib::gobject' not found in 'glib' package requirement` | libical3 配方的 `cpp_info.requires` 用了 ohpc glib 未定义的组件名 | 消费侧改写为 `glib::glib-2.0` / `glib::gobject-2.0` |
| 4 | configure：`Cannot find glib-compile-schemas` | CMAKE_CROSSCOMPILING=false 时 GLibTools 用 `pkg_check_variable(gio-2.0 glib_compile_schemas)`，conan 生成的 .pc 无此变量 | conan 元数据注入该变量 + CMake cache 预置可执行的本机工具 |
| 5 | configure：`file failed to open ... oauth2-google-client-id` | data/CMakeLists 的 `CHECK_C_SOURCE_RUNS` 程序崩溃（见 #7）后 `file(READ)` 失败 | 随 #7 一并修复 |
| 6 | `gdbus-codegen: No such file or directory` / `glib-compile-resources: Error loading libffi.so.8` | hnp 的 gdbus-codegen/glib-mkenums 是 `/usr/bin/python3`、`/usr/bin/perl` shebang 的坏脚本；glib-compile-resources 缺 libffi.so.8；conan glib 包内的 ELF 工具未签名（loader 拒绝执行） | Python 系工具取 conan glib 包（`#!/usr/bin/env python3`），ELF 系工具取 hnp 并把 libffi 目录加进 LD_LIBRARY_PATH |
| 7 | `GLib-GObject-CRITICAL: cannot register existing type 'gchar'`（CHECK_C_SOURCE_RUNS 探针运行崩溃） | libsoup3 r1 静态内嵌 glib2 GObject（见依赖图关键点） | 换 `libsoup3/3.6.5-r3` |
| 8 | `ld.lld: error: undefined symbol: g_libintl_bindtextdomain` | glib 的 proxy-libintl 提供 `g_libintl_*`，conan 生成的 glib .pc 未列 `-lintl` | 消费侧给 glib 各组件 libs 追加 `intl` |
| 9 | `ld.lld: error: undefined symbol: CERT_GetDefaultCertDB / PK11_GetBestSlot` | nss 包 shared=False 时 cpp_info 给的是静态 coreconf 名（`-lnss` 等），静态归档不含 NSS API | 消费侧把 libs 换成 `nss3/ssl3/smime3/nssutil3/softokn3/freebl3/nssckbi/nssdbm3/sqlite3` |
| 10 | `camel-debug.c:1078: error: expected expression` | 标签 `try_next_frame:` 后紧跟声明，C99/C11 非法（GCC 仅作扩展接受） | 补丁 0002：声明上移到标签之前 |
| 11 | `ld.lld: error: undefined symbol: sqlite3_vfs_find` | nss 包内的 `libsqlite3.so` 是裁剪导出的 stub，按 -L 顺序先于独立 sqlite3 静态库被命中 | 补丁 0001：CAMEL 的 pkg_check_modules 把 sqlite3 提到 nss 之前 |
| 12 | `ld.lld: error: undefined symbol: __cxa_begin_catch / std::terminate()` | icu 是静态 C++ 构建，被 C-only 目标链接 | 消费侧给 icu cpp_info.libs 追加 `c++` |
| 13 | 产物无 SONAME，消费者 NEEDED 变成 `../../camel/libcamel-1.2.so` | CMake 无 `Platform/HarmonyOS.cmake`（System is unknown to cmake），Linux 平台变量缺失 | 配方注入 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG[-CXX]`；现 SONAME 为 `libcamel-1.2.so.67` 等 |
| 14 | 测试程序 `Error loading shared library ./libical-glib.so (needed by libecal-2.0.so)` | libical3 的共享库 SONAME 是相对路径 `./libical-glib.so`（该包为规避 HMDFS 上绝对 soname/$ORIGIN 不稳定而故意注入 `-Wl,-soname,./`），OHOS loader 按 CWD 解析 | 消费侧改为链接 libical3 的静态归档（libical-glib.a/libicalvcal.a/libicalss.a/libical.a），把 libical 实现并入 libecal-2.0.so，去掉破损的运行时依赖 |
| 15 | 测试程序 `Error loading shared library libnss3.so` | 测试包运行期需要全部依赖 libdir 在 LD_LIBRARY_PATH 上 | test_package 的 `test()` 显式按依赖图拼 LD_LIBRARY_PATH |

## 源码修改（patch）
- `patches/0001-CMakeLists.txt.patch`：调整 CAMEL 的 pkg_check_modules 顺序
  （sqlite3 先于 nss）。
- `patches/0002-src-camel-camel-debug.c.patch`：`backtrace_matches()` 标签后声明
  上移。

两个补丁都不含平台宏（R8），都是构建可移植性问题（patch_type=portability）。

## 依赖版本
- glib/2.84.0.1.1, gtk4/4.22.4, libsoup3/3.6.5-r3, json-glib/1.10.6.1,
  libsecret/0.21.7, libxml2/2.15.3.1, sqlite3/3.49.1, libical3/3.0.20,
  nss/3.118.1, nspr/4.37, uuid/2.40.1, icu/76.1, zlib/1.3.1.1
- 传递（构建期）：harfbuzz/14.2.0.1（源码构建）、pango/1.56.4、cairo/1.18.4、
  gdk-pixbuf/2.44.6、graphene/1.10.8、libpsl/0.21.5.1、libnghttp2/1.70.0、
  brotli/1.2.0.1、libgcrypt/1.11.0、libgpg-error/1.55

## 包内容
`lib/` 下 9 个 EDS 共享库（libedataserverui4-1.0 / libcamel-1.2 /
libecal-2.0 / libedataserver-1.2 / libebackend-1.2 / libebook-1.2 /
libebook-contacts-1.2 / libedata-book-1.2 / libedata-cal-2.0）+
`lib/evolution-data-server/libedbus-private.so` + 头文件
（`include/evolution-data-server/**`）+ pkgconfig。构建产物里的命令行工具
（src/tools、src/services）、camel provider/backend 模块、D-Bus service 文件、
GSettings schema、systemd unit 与约 100 份 gettext 目录在 package() 中清理
（库类型包不声明 commands.json，R38/PF8）。

## 上游测试台账（R51 三步法）
- **清点**：源码树 `tests/` 共 8 个子目录（book-migration / libebook /
  libebook-contacts / libecal / libedata-book / libedata-cal /
  libedataserver / test-server-utils），ctest 注册用例 13 个
  （`add_installable_test()` 8 + `build_only_installable_test()` 5）；
  测试源文件 82 个 .c。
- **可运行性**：**全部不可运行**，具体技术原因：EDS 上游测试是**服务端集成
  测试**，每个用例经 `tests/test-server-utils` 夹具启动私有 D-Bus 会话总线与
  `evolution-source-registry` / `evolution-addressbook-factory` /
  `evolution-calendar-factory` 等 D-Bus 服务，再通过 D-Bus 驱动进程外的
  libedataserver / libecal / libedata-* API。本适配交付的是**库**（不含这些
  服务进程与 dbus-daemon），OpenHarmony PC 运行时也不提供 session bus，
  因此这些用例在 CI 上运行必然全数 fail，而不是被跳过。配方以
  `ENABLE_TESTS=OFF` 构建（不为库包引入整套服务端测试链路）。
- **实测回填**：上游注册 13 / 可运行 0 / 豁免 13（原因如上）。功能覆盖由
  test_package 以消费者视角真实调用被测库 API 承担。

## 验证结果
```
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing
...
libedataserverui4/3.60.2: package(): Packaged 10 '.so' files
libedataserverui4/3.60.2: package(): Packaged 10 '.pc' files
libedataserverui4/3.60.2: package(): Packaged 343 '.h' files
libedataserverui4/3.60.2: Created package revision ...
======== Testing the package: Executing test ========
libedataserverui4/3.60.2 (test package): RUN: ./test_libedataserverui4
e_credentials_prompter type: ECredentialsPrompter
e_cell_renderer_color_new: ECellRendererColor
PASS: libedataserverui4 API calls succeeded
```
- 产物 SONAME：`libedataserverui4-1.0.so.0` / `libcamel-1.2.so.67` /
  `libecal-2.0.so.3` / `libedataserver-1.2.so.27` / `libedbus-private.so`
- test_package 通过（真实 API 调用，非空壳）

**编译结束**: 2026-10-09
**最终状态**: built
---

## 整改记录（2026-10-10）：上游测试真实执行 + libical 链接方式修正

### 1) 上游 13 个测试目标现在真实执行（此前 0/13）

`ENABLE_TESTS=ON`，`build()` 末尾调用 `_run_upstream_tests()` 用 ctest 实跑整套
上游测试。实测（HarmonyOS PC aarch64，conan create 内）：

- ctest 注册 **101** 个用例（13 个测试目标，GLib g_test 把内部 `/TestCase`
  逐条注册）；**101/101 全部真实执行**，**100 通过 / 1 失败 = 99.0%**，
  总耗时 205 s。
- 唯一失败：`test-book-client-photo-is-uri` —— 地址簿后端把内嵌照片转写为文件
  时被 HMDFS/SELinux 拒绝（`Error transforming contact ...: Permission denied`
  → `Cannot modify contacts: Permission denied`）。平台文件系统权限限制，非库缺陷；
  同一后端在其余 20 余个 `test-book-cache-*` 用例中全部通过。

让 D-Bus 集成测试在本平台跑起来需要三处适配（配方 `DBUS_WRAPPER` / `FAKEPW_C`）：

| 障碍 | 现象 | 处理 |
|------|------|------|
| `/tmp` 只读 | `dbus-daemon: Failed to bind socket "/tmp/dbus-XXXX": Read-only file system` | GTestDBus 在总线配置里硬编码 `<listen>unix:tmpdir=/tmp</listen>`；用 dbus-daemon 包装脚本改写该行到可写目录（`G_TEST_DBUS_DAEMON` 注入） |
| HMDFS 不允许 unix socket | `Failed to bind socket ...: Operation not permitted` | 目标目录改用 `/data/storage/el2/base/cache`（本机唯一允许 bind unix socket 的可写目录） |
| 无 uid 的 passwd 记录 | `getpwuid_r(): failed due to unknown user id (20020085)` → 总线连接被关闭 | 编译极小的 `getpwuid(_r)/getpwnam` 垫片，`LD_PRELOAD` 提供合成 passwd 条目 |

### 2) libical 改为“SONAME 修正后的共享库”（修正一处真实缺陷）

libical3/3.0.20 的共享库带**相对 SONAME** `./libical.so` / `./libical-glib.so`
（HMDFS 上绝对 soname/$ORIGIN 不稳定，该包故意注入 `-Wl,-soname,./`），OHOS
loader 把带 `/` 的 NEEDED 当作相对 CWD 的路径 → 消费者启动即
`Error loading shared library ./libical.so`。

此前绕法是改链 **静态归档**（`libical-glib.a` 等）。这在真正跑上游测试时暴露了
新问题：静态归档被同时并入 `libecal-2.0.so` **和**每个链接 libical 的测试/消费者
可执行文件，进程内出现两份 libical 的 GObject 实现，运行期
`GLib-GObject-FATAL-CRITICAL: cannot register existing type 'ICalValue'`
（5 个 `test-cal-*` 用例因此全灭）。

修正为：`_prepare_libical3()` 把 4 个共享库复制到 build 目录，**逐字节**把
`./libical*.so` 改写成纯文件名（新串更短，原位 NUL 填充，不动任何 ELF 结构），
再重新签名（改动会失效 HarmonyOS 的 `.codesign` 段），随后让 libecal 与
test_package 都链接这个**共享**版本；修正后的 4 个 `.so` 随本包一起打包，
`DT_NEEDED` 因此在运行期可解析。→ 单实例 GObject，5 个用例恢复通过。
---

**编译结束**: 2026-10-11 11:55
**最终状态**: built
