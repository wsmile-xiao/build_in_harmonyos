# libaudclient 3.5-rc2.1 适配笔记（上游 3.5-rc2 的配方修订版）

## 编译环境

- 构建系统: audacious 自研 buildsys.mk（非 automake；发布 tarball 自带预生成 configure）
- 编译日期: 2026-09-02 首版；2026-10-11 修订（依赖版本对齐 + shared glib 适配，见问题 #12）
- 编译器: clang（/data/service/hnp/bin），三元组 aarch64-unknown-linux-ohos
- 依赖: dbus-glib/0.114.1、dbus/1.14.10（传递 glib/2.84.0.1(shared)、expat/2.8.2.1(shared)、pcre2/10.45(static)、zlib/1.3.1.1(static)、libffi/3.4.4(static)）
- 源码: https://distfiles.audacious-media-player.org/libaudclient-3.5-rc2.tar.bz2
  sha256 57b59936adee309308bebe6d37709ea7e833e53529164cca0720a337c17f175a（2026-09-02 与 2026-10-11 两次本地校验一致）

## 原位修订说明（3.5-rc2 → 3.5-rc2.1）

- 本版本为 **R37 原位修订**：制品仓已存在 `libaudclient/3.5-rc2`（原始配方，PR e897103a48 发布），cnb.cool 制品仓不支持同版本多 revision 并存（409 Conflict），配方修复须递增版本号后缀（CI L0j 实测，Build #85464）。
- 上游源码**仍为 3.5-rc2 官方 tarball**，sha256 逐字节同源（`57b59936…`，与 3.5-rc2 conandata 一致）；版本号位移=配方修订，非上游新版本。先例：glib/2.84.0.1「原位修订：上游源码仍为 2.84.0 tarball」、libgsf/1.14.58.1（PR !5333「按 R37 版本递增」）。
- 相对 3.5-rc2 配方的实质修订：依赖版本对齐（glib/2.84.0.1 + dbus-glib/0.114.1）、glib 家族由内联改为真实共享依赖（DT_NEEDED 布局）、test_package 改为 71 导出符号 dlsym 全量验证 + OHOS soname closure 加载测试。详见下文问题 #12 与验证记录。

## 上游源码勘察（本地静态证据）

- 官方发布 tarball（非 GitHub tag 归档）才带预生成 `configure` 与 `src/audacious/dbus-client-bindings.h`；tag 归档只有 configure.ac/objects.xml，需要 autotools 工具链。CI 矩阵无 autotools 保证，故采用官方 tarball。
- `configure.ac:59` `PKG_CHECK_MODULES([DBUS], [dbus-1 >= 0.60 dbus-glib-1 >= 0.60])`；生成的 configure 里另有独立的 `checking for GLIB ... "glib-2.0 >= 2.28"` 模块检查（预置判定 `if test -n "$GLIB_CFLAGS"`，configure 行 4861 附近）。
- `configure.ac:61-63`: `AC_PATH_PROG([DBUS_BINDING_TOOL], [dbus-binding-tool], [no])` + `AC_MSG_ERROR`。
- `configure.ac:48-55`: GCC 分支加 `-fvisibility=hidden`，`EXPORT=__attribute__((visibility("default")))` → audctrl.c 全部 71 个函数定义带 EXPORT（grep 实测），dlsym 全量导出检查有实义。
- `m4/buildsys.m4` GNU 分支: `LIB_LDFLAGS='-shared -Wl,-soname=${SHARED_LIB}.${LIB_MAJOR}'`（soname=libaudclient.so.2）、`INSTALL_LIB` 安装 `libaudclient.so.2.0.0` + `.so.2`/`.so` 符号链接（标准 Linux 布局）。
- `buildsys.mk.in:205` 链接规则 `${LD} -o $@ $$objs ${LIB_LDFLAGS} ${LDFLAGS} ${LIBS}`：LIBS 全部位于目标对象之后，GNU ld 单遍左到右解析。
- `src/libaudclient/Makefile:23-24`: `LIBS += ${GLIB_LIBS}\${DBUS_LIBS}`（上游顺序 glib 在前 → dbus-glib 静态归档的 g_* 引用无法闭合，见问题 #1）。
- `all → subdirs → depend → 库目标`；`depend: pre-depend ${SRCS}` 每轮 make 都触发 pre-depend，进入 `src/audacious` 执行 `${MAKE} dbus-client-bindings.h`；该规则的前置 `DBUS_BINDINGS_SOURCES` 从未被 AC_SUBST（展开为空），tarball 自带头文件存在即永不重建 → dbus-binding-tool 只被 configure 的存在性门禁要求，make 阶段不实际调用。
- `buildsys.mk.in` 无 check 目标；四个 Makefile 与 configure.ac 均无 TESTS/check_PROGRAMS/check-local/测试宏；无 tests/ 目录 → 上游无自动化测试（审计 grep 在配方 build() 内执行，conan create 日志留痕）。
- 上游不一致：`audctrl.h` 声明 `audacious_set_session_uri` / `audacious_get_session_uri` / `audacious_set_session_type`（Audacious 1.2 注记），但 `audctrl.c` 无实现（grep 0 命中）。消费者引用会链接失败；导出测试清单按实现侧 71 符号。

## 遇到的问题与解决方案（全部经设备实测定位并复核）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `libdbus-glib-1.a` 的 `g_*` 引用无法闭合 | 上游 Makefile `LIBS += ${GLIB_LIBS} ${DBUS_LIBS}` 把 glib 库放在静态消费者 libdbus-glib-1.a 之前；GNU ld 单遍左到右 | 补丁 0003 交换追加顺序（DBUS_LIBS 先、GLIB_LIBS 后），拆分为两条依赖序链接线 |
| 2 | 空串预置变量导致 configure 走 pkg-config 并中止 | pkg.m4 预置判定为 `test -n "$VAR"`，空串不算预置；独立的 GLIB 模块检查同样受影响 | DBUS_CFLAGS/DBUS_LIBS/GLIB_CFLAGS/GLIB_LIBS 四个预置变量全部非空（与 dbus-glib/0.114 已验证配方一致） |
| 3 | 依赖 .la 的 libdir 过期（E236） | conan 包内 .la 的 `libdir='//lib'` 不可迁移 | E236 la-free 方案：build() 只把依赖 `*.a` 静态归档复制到构建私有目录（现为 libdbus-1.a/libdbus-glib-1.a 等），configure 只经预置变量解析；不改动 conan 缓存。共享依赖（glib/expat）改走各自包目录 `-L` 直引，详见 #4 |
| 4 | 依赖制品变体不齐一（原判"全 static-only"已过时） | 制品仓实际状态：dbus/dbus-glib 仅 static（dbus-glib fPIC=True）；**glib/2.84.0.1 只发布 shared=True binary**（libglib-2.0.so 与 soname 副本为同内容重复真实文件 + libintl.so，无 .a）；expat 只发布 shared object | la-free 目录只镜像 `.a`；`GLIB_LIBS` 增加 `-L<glib 包>/lib`（旧的 `-lffi/-lpcre2-8/-lpcre2-posix/-lz` 全部删去——它们在 shared glib 中已静态内嵌，其中 `-lffi` 更会直接报 unable to find library）；`DBUS_LIBS` 增加 `-L<expat 包>/lib`（expat 的 libexpat.so 是 libexpat.so→.so.1→.so.1.12.2 符号链接链，扁平复制无法忠实还原，故不镜像）。两目录都不含 .la，E236 的 libtool .la 前提不成立 |
| 5 | configure 无 dbus-binding-tool 即中止 | AC_PATH_PROG 硬性门禁 | 预置 `DBUS_BINDING_TOOL=<dbus-glib 包>/bin/dbus-binding-tool`（arm64 原生二进制，设备上 host==build 可直接执行） |
| 6 | config.guess/sub 不识别 HarmonyOS/linux-ohos | E007：设备 uname -s 输出 HarmonyOS；2014 年代脚本 | 补丁 0001（HarmonyOS 分支 → aarch64-unknown-linux-ohos）+ 0002（config.sub 白名单 + OS 表加 -linux-ohos*） |
| 7 | configure 报 `working directory cannot be determined` 并伴随 getcwd errno 风暴 | profile 的 CONFIG_SHELL 指向 hnp bash 5.3；autoconf 2.69 生成 configure 在 CONFIG_SHELL 非空时无条件 `exec $CONFIG_SHELL` 重执行自身，而该 bash 启动 getcwd 在 HMDFS 上对继承的过期 PWD 失败（toybox /bin/sh 不受影响；dbus-glib 0.114 为 2.71 生成无重执行块） | 配方 build() 内 `unset CONFIG_SHELL` 后手工调用 configure（load_toolchain_args 取 configure_args），仅对 configure 进程生效 |
| 8 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | configure 行 6132/6137 以 `(umask 077 && mktemp -d/mkdir)` 创建临时目录；HMDFS 拒绝在 077 目录内自写（libcsv/3.0.3、dbus-glib/0.114 先例） | 补丁 0004：两处 `umask 077` → `umask 022` |
| 9 | make 报 `make: -c: No such file or directory`（Error 127，buildsys.mk:111 all） | 首次修复 #7 用 `CONFIG_SHELL=`（空但已设置）：configure 前导 `SHELL=${CONFIG_SHELL-/bin/sh}` 对空值不回退，空 SHELL 经 AC_SUBST 写入 buildsys.mk，GNU make 以空 SHELL 拼接 `[-c, recipe]` 直接 exec `-c` 失败 | 改为 `unset CONFIG_SHELL`（未设置才触发 `/bin/sh` 回退），buildsys.mk 得到 `SHELL = /bin/sh`；basic_layout 的 out-of-source 构建也被顺带修复（audacious buildsys 无 VPATH，layout() 强制 in-source） |
| 10 | conan create 报 `settings.os.version value not defined` | 在配方目录内用相对路径 `ci/conan/profiles/ohos-aarch64` 调 conan，被解析为 ~/.conan2/profiles 下的同名默认 profile（无 os.version），而非仓库内 profile | 与 CI `ci/conan/build_and_test.sh` 一致：始终传仓库内 profile 的绝对路径 + `--build=missing` |
| 11 | test_package 消费者编译 `'glib.h' file not found` | Conan 2 `transform_downstream`：SHARED 包（本包）对依赖向下游强制 `headers=False` → 节点被标记 Skipped → PkgConfigDeps 把 glib 从生成的 .pc `Requires:` 链静默丢弃 | `self.requires("glib/2.84.0.1", transitive_headers=True)` 使 headers 传播存活；另将 glib 提为直接依赖以满足 cpp_info.requires 组件引用校验 |
| 12 | 下游 wmauda/0.9 消费图要求 libaudclient 的 **package_id `0e0a65f8885765a096196fc5d16928e30c5e97cf`**，而制品仓只有 glib/2.88.0 的 `d5b3d3fab…` → `--build=missing` 从源码重建，且在**链接期**报 `ld.lld: error: unable to find library -lgio-2.0/-lgobject-2.0/-lgthread-2.0/-lgmodule-2.0/-lglib-2.0/-lintl/-lffi`（上表 #4 的根因） | 单图只能有一个 glib：下游 GTK+2 栈（gtk2/2.24.33、pango/1.50.14.1.1、atk/2.38.0.1、gdk-pixbuf/2.44.6.1）全部 pin glib/2.84.0.1，而 libaudclient→dbus-glib/0.114→glib/2.88.0；消费者只能用 `override=True` 把 glib 拉到 2.84.0.1（实测移除 override 直接报 `Version conflict: Conflict between glib/2.88.0 and glib/2.84.0.1`）。此时依赖侧若仍 pin 2.88.0，package_id 必然与注册表失配 | 依赖侧同样对齐 `dbus-glib/0.114.1` + `glib/2.84.0.1`（**不加 override=True**——自包内 override-only 需求会让该依赖从 `self.dependencies` 消失，取 package_folder 时 KeyError），package_id 即与消费者图一致而复用已发布 binary |

## 验证结果（2026-10-11 修订验证）

在 worktree `…/wt-libaudclient-fix/archives/l/libaudclient/3.5-rc2.1` 执行，profile 用仓库内绝对路径（与 `ci/conan/build_and_test.sh` 一致）：

```bash
conan create . \
  -pr:h=<repo>/ci/conan/profiles/ohos-aarch64 \
  -pr:b=<同> \
  --build=missing
```

结果 **EXIT=0**：

- 依赖解析全部命中已发布 binary，无需从源码构建任何依赖：`dbus-glib/0.114.1`、`dbus/1.14.10`、`expat/2.8.2.1`、`glib/2.84.0.1` 均为 Cache；`libffi/3.4.4`、`pcre2/10.45`、`zlib/1.3.1.1` 为 Skipped binaries。
- 上游测试审计 grep（配方 build() 内执行，日志留痕原样命令）：

  ```bash
  grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|check-local' Makefile src/*/Makefile buildsys.mk.in configure.ac
  ```

  日志结论：无任何命中/无 check 目标 —— 上游无自动化测试，`HMBS_UPSTREAM_TEST_RESULT` 标记 `status: no_tests`。
- `unset CONFIG_SHELL` + configure → `make -j1` → `make install DESTDIR` 全通，buildsys.mk 得到 `SHELL = /bin/sh`。
- la-free 目录实测内容：`['libdbus-1.a', 'libdbus-glib-1.a', 'libpcre2-8.a', 'libpcre2-posix.a']`（仅静态归档，无 .la）。
- 交付包：`libaudclient.so.2.0.0`（sha256 `f15947cd03db0be4a008c0a25573ceb55a752d50a4646956c013e3673d895bb5`）+ `libaudclient.so.2`/`libaudclient.so` 符号链接 + `include/audacious/{audctrl.h,dbus.h}` + `lib/pkgconfig/audclient.pc`；package_id `0e0a65f8885765a096196fc5d16928e30c5e97cf`（= wmauda 图所求）、rrev `37c2c37c9edb2301f8581c7371764315`。
- `llvm-readelf -d` 实测：SONAME `libaudclient.so.2`；DT_NEEDED = `libexpat.so.1` + `libgio-2.0.so.0` + `libgobject-2.0.so.0` + `libgthread-2.0.so.0` + `libgmodule-2.0.so.0` + `libglib-2.0.so.0` + `libintl.so.8` + `libc.so`（glib 家族由内联改为真实共享依赖）。
- test_package 消费者：clang 以 `$(pkg-config --cflags --libs audclient)` 编译链接通过；运行 `test_audclient` 全绿 `checks=82 failures=0`（9 链接期 API 地址 + 1 dlopen(soname) + 71 dlsym 全量导出 + 1 dladdr），`HMBS_TEST_PACKAGE_RESULT` 标记 `executed:true, passed:true`。

> **本地沙箱说明（不影响 CI）**：本轮验证在 WorkBuddy 沙箱会话内完成。该会话的动态加载器不跟随符号链接，`libaudclient.so.2`/`libexpat.so.1` 这两个符号链接项在 `test()` 运行期无法解析（链接期 `ld.lld` 与同类包既有 CI 均正常；同一目录改用同名真实文件即全绿）。为取得完整运行证据，测试时以 `LD_LIBRARY_PATH` 追加一个"展平目录"——其中 `libaudclient.so.2` 是与制品**逐字节一致**（sha256 相同）的副本，expat/glib 同为包内真实文件副本；未改动配方、未改动 conan 缓存、未改动 test_package。CI worker 无此限制，`ci/conan/build_and_test.sh` 的常规路径即为权威判定。

未覆盖项：audctrl 方法调用路径（dbus_g_proxy_call 往返）——OHOS 无 D-Bus session bus（dbus 包无 dbus-daemon，设备无 Audacious 实例），属平台环境限制而非跳过；已在 #4/#12 场景内静态验证链接与导出面。原"消费者直接调用 glib API 会引入双 GType 运行时"的限制随 glib 转为共享依赖一并消除。

## 注意事项

- W2 原子性：本 PR 仅含 archives/l/libaudclient/**，不混入其他软件或框架改动。
- 禁止提交：scratch/ 研究目录、patch-verify/ 临时副本不入任何提交。
- 依赖发布顺序（R36/W0）：本包必须先发布 `0e0a65f8…` binary，下游 `wmauda/0.9` 才能复用；JC6 单软件原子性禁止把 libaudclient 与 wmauda 放进同一 PR。
- 知识候选（路径 B）：①buildsys/Makefile 的 LIBS 追加顺序 vs GNU ld 静态解析顺序（补丁 0003）；②pkg.m4 预置变量非空要求（configure 独立 GLIB 检查）；③audacious buildsys.mk 适配模式（无 check 目标、INSTALL_LIB 版本化布局、空前置 bindings 规则）；④autoconf 2.69 生成 configure 的 CONFIG_SHELL 无条件重执行块 × hnp bash 5.3 HMDFS getcwd 失败；⑤Conan 2 `transform_downstream` 导致 PkgConfigDeps 静默丢弃 `.pc Requires` 链（`transitive_headers=True` 修复）；⑥**依赖侧 package_id 与消费者图对齐**（单图单 glib；消费者 override 的版本必须同时成为依赖配方自身的 pin，否则触发源码重建；自包内 `override=True` 会让依赖从 `self.dependencies` 消失）；⑦共享/静态混合变体下 E236 la-free 目录的正确边界（只镜像 .a，共享依赖走 `-L` 直引）。E007/E236/E216/umask 077 复用现有图谱或既有先例条目。
---

**编译结束**: 2026-10-11 16:24
**最终状态**: built
