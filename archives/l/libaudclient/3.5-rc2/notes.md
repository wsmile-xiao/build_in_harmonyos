# libaudclient 3.5-rc2 适配笔记

## 编译环境

- 构建系统: audacious 自研 buildsys.mk（非 automake；发布 tarball 自带预生成 configure）
- 编译日期: 2026-09-02（设备验证见下）
- 编译器: clang（/data/service/hnp/bin），三元组 aarch64-unknown-linux-ohos
- 依赖: dbus-glib/0.114、dbus/1.14.10（传递 glib/2.88.0、expat/2.8.2、pcre2/10.45、zlib/1.3.1）
- 源码: https://distfiles.audacious-media-player.org/libaudclient-3.5-rc2.tar.bz2
  sha256 57b59936adee309308bebe6d37709ea7e833e53529164cca0720a337c17f175a（本地校验 2026-09-02）

## 上游源码勘察（本地静态证据）

- 官方发布 tarball（非 GitHub tag 归档）才带预生成 `configure` 与 `src/audacious/dbus-client-bindings.h`；tag 归档只有 configure.ac/objects.xml，需要 autotools 工具链。CI 矩阵无 autotools 保证，故采用官方 tarball。
- `configure.ac:59` `PKG_CHECK_MODULES([DBUS], [dbus-1 >= 0.60 dbus-glib-1 >= 0.60])`；生成的 configure 里另有独立的 `checking for GLIB ... "glib-2.0 >= 2.28"` 模块检查（预置判定 `if test -n "$GLIB_CFLAGS"`，configure 行 4861 附近）。
- `configure.ac:61-63`: `AC_PATH_PROG([DBUS_BINDING_TOOL], [dbus-binding-tool], [no])` + `AC_MSG_ERROR`。
- `configure.ac:48-55`: GCC 分支加 `-fvisibility=hidden`，`EXPORT=__attribute__((visibility("default")))` → audctrl.c 全部 71 个函数定义带 EXPORT（grep 实测），dlsym 全量导出检查有实义。
- `m4/buildsys.m4` GNU 分支: `LIB_LDFLAGS='-shared -Wl,-soname=${SHARED_LIB}.${LIB_MAJOR}'`（soname=libaudclient.so.2）、`INSTALL_LIB` 安装 `libaudclient.so.2.0.0` + `.so.2`/`.so` 符号链接（标准 Linux 布局）。
- `buildsys.mk.in:205` 链接规则 `${LD} -o $@ $$objs ${LIB_LDFLAGS} ${LDFLAGS} ${LIBS}`：LIBS 全部位于目标对象之后，GNU ld 单遍左到右解析。
- `src/libaudclient/Makefile:23-24`: `LIBS += ${GLIB_LIBS}\${DBUS_LIBS}`（上游顺序 glib 在前 → 静态链无法解析，见问题 #1）。
- `all → subdirs → depend → 库目标`；`depend: pre-depend ${SRCS}` 每轮 make 都触发 pre-depend，进入 `src/audacious` 执行 `${MAKE} dbus-client-bindings.h`；该规则的前置 `DBUS_BINDINGS_SOURCES` 从未被 AC_SUBST（展开为空），tarball 自带头文件存在即永不重建 → dbus-binding-tool 只被 configure 的存在性门禁要求，make 阶段不实际调用。
- `buildsys.mk.in` 无 check 目标；四个 Makefile 与 configure.ac 均无 TESTS/check_PROGRAMS/check-local/测试宏；无 tests/ 目录 → 上游无自动化测试（审计 grep 在配方 build() 内执行，conan create 日志留痕）。
- 上游不一致：`audctrl.h` 声明 `audacious_set_session_uri` / `audacious_get_session_uri` / `audacious_set_session_type`（Audacious 1.2 注记），但 `audctrl.c` 无实现（grep 0 命中）。消费者引用会链接失败；导出测试清单按实现侧 71 符号。

## 遇到的问题与解决方案（全部经设备实测定位并复核）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 静态链下 `libdbus-glib-1.a` 的 `g_*` 引用无法闭合 | 上游 Makefile `LIBS += ${GLIB_LIBS} ${DBUS_LIBS}` 把 glib 归档放在消费者之前；GNU ld 单遍左到右 | 补丁 0003 交换追加顺序（DBUS_LIBS 先、GLIB_LIBS 后），拆分为两条依赖序链接线 |
| 2 | 空串预置变量导致 configure 走 pkg-config 并中止 | pkg.m4 预置判定为 `test -n "$VAR"`，空串不算预置；独立的 GLIB 模块检查同样受影响 | DBUS_CFLAGS/DBUS_LIBS/GLIB_CFLAGS/GLIB_LIBS 四个预置变量全部非空（与 dbus-glib/0.114 已验证配方一致） |
| 3 | 依赖 .la 的 libdir 过期（E236） | conan 包内 .la 的 `libdir='//lib'` 不可迁移 | E236 la-free 方案：build() 复制依赖 .a 到构建私有目录，configure 只经预置变量解析；不改动 conan 缓存 |
| 4 | OHOS 制品 static-only | glib/dbus/dbus-glib 注册表无 shared 预编译 | libaudclient.so 内联整条静态链；DT_NEEDED 仅 libexpat.so（expat 只有 .so，作为运行时依赖复制进 la-free 目录） |
| 5 | configure 无 dbus-binding-tool 即中止 | AC_PATH_PROG 硬性门禁 | 预置 `DBUS_BINDING_TOOL=<dbus-glib 包>/bin/dbus-binding-tool`（arm64 原生二进制，设备上 host==build 可直接执行） |
| 6 | config.guess/sub 不识别 HarmonyOS/linux-ohos | E007：设备 uname -s 输出 HarmonyOS；2014 年代脚本 | 补丁 0001（HarmonyOS 分支 → aarch64-unknown-linux-ohos）+ 0002（config.sub 白名单 + OS 表加 -linux-ohos*） |
| 7 | configure 报 `working directory cannot be determined` 并伴随 getcwd errno 风暴 | profile 的 CONFIG_SHELL 指向 hnp bash 5.3；autoconf 2.69 生成 configure 在 CONFIG_SHELL 非空时无条件 `exec $CONFIG_SHELL` 重执行自身，而该 bash 启动 getcwd 在 HMDFS 上对继承的过期 PWD 失败（toybox /bin/sh 不受影响；dbus-glib 0.114 为 2.71 生成无重执行块） | 配方 build() 内 `unset CONFIG_SHELL` 后手工调用 configure（load_toolchain_args 取 configure_args），仅对 configure 进程生效 |
| 8 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | configure 行 6132/6137 以 `(umask 077 && mktemp -d/mkdir)` 创建临时目录；HMDFS 拒绝在 077 目录内自写（libcsv/3.0.3、dbus-glib/0.114 先例） | 补丁 0004：两处 `umask 077` → `umask 022` |
| 9 | make 报 `make: -c: No such file or directory`（Error 127，buildsys.mk:111 all） | 首次修复 #7 用 `CONFIG_SHELL=`（空但已设置）：configure 前导 `SHELL=${CONFIG_SHELL-/bin/sh}` 对空值不回退，空 SHELL 经 AC_SUBST 写入 buildsys.mk，GNU make 以空 SHELL 拼接 `[-c, recipe]` 直接 exec `-c` 失败 | 改为 `unset CONFIG_SHELL`（未设置才触发 `/bin/sh` 回退），buildsys.mk 得到 `SHELL = /bin/sh`；basic_layout 的 out-of-source 构建也被顺带修复（audacious buildsys 无 VPATH，layout() 强制 in-source） |
| 10 | conan create 报 `settings.os.version value not defined` | 在配方目录内用相对路径 `ci/conan/profiles/ohos-aarch64` 调 conan，被解析为 ~/.conan2/profiles 下的同名默认 profile（无 os.version），而非仓库内 profile | 与 CI `ci/conan/build_and_test.sh` 一致：始终传仓库内 profile 的绝对路径 + `--build=missing` |
| 11 | test_package 消费者编译 `'glib.h' file not found` | Conan 2 `transform_downstream`：SHARED 包（本包）的 STATIC 依赖（glib）传给下游强制 `headers=False, libs=False` → 节点 Skipped → PkgConfigDeps 把 glib 从生成的 .pc `Requires:` 链静默丢弃 | `self.requires("glib/2.88.0", transitive_headers=True)`：headers 传播存活、libs 保持 False（静态链已嵌入 .so）；另将 glib 提为直接依赖以满足 cpp_info.requires 组件引用校验 |

## 验证结果（设备端，2026-09-02）

本地与远端在同一提交上验证：分支 feat/libaudclient-3.5-rc2，远端 `git pull --ff-only` 后 HEAD 与本地推送一致，`git status --short` 仅含已知 libXext 大小写碰撞伪改动（本文件与 manifest.yaml 不参与配方导出，rrev 不受其影响，文档提交后的复跑为缓存命中复验）。以下命令在远端鸿蒙设备 `$HOME/ws/wt-libaudclient-3.5-rc2/archives/l/libaudclient/3.5-rc2` 执行：

```bash
# conan create（profile 用仓库内绝对路径，与 ci/conan/build_and_test.sh 一致）
TMPDIR=$HOME/tmp/libaudclient-3.5-rc2/tmp \
conan create . \
  -pr:h=$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$HOME/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

结果（conan-create8.log，EXIT=0）：

- 构建链全部通过：`unset CONFIG_SHELL` + configure → `make -j1` → `make install DESTDIR`，包修订 `4ad3ae2632abbf73c7c7d800bf13218b`。
- 上游测试审计 grep（配方 build() 内执行，日志留痕原样命令）：

  ```bash
  grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|check-local' Makefile src/*/Makefile buildsys.mk.in configure.ac
  ```

  日志结论：无任何命中/无 check 目标 —— 上游无自动化测试，`HMBS_UPSTREAM_TEST_RESULT` 标记 `status: no_tests`。
- test_package 消费者：clang 以 `$(pkg-config --cflags --libs audclient)` 编译链接，运行 `test_audclient` 全绿：`ok 1 … ok 82`，`checks=82 failures=0`（9 链接期 API 地址 + 1 dlopen(soname) + 71 dlsym 全量导出 + 1 dladdr）。`HMBS_TEST_PACKAGE_RESULT` 标记 `executed:true, passed:true`。

未覆盖项：audctrl 方法调用路径（dbus_g_proxy_call 往返）——OHOS 无 D-Bus session bus（dbus 包无 dbus-daemon，设备无 Audacious 实例），属平台环境限制而非跳过；已在上表 #4 场景内静态验证链接与导出面。已知限制：消费者直接调用 glib API 会引入双 GType 运行时（glib static-only，E257 同类）。

## 注意事项

- W2 原子性：本 PR 仅含 archives/l/libaudclient/**，不混入其他软件或框架改动。
- 禁止提交：scratch/ 研究目录、patch-verify/ 临时副本不入任何提交。
- 知识候选（路径 B）：①buildsys/Makefile 的 LIBS 追加顺序 vs GNU ld 静态解析顺序（补丁 0003）；②pkg.m4 预置变量非空要求（configure 独立 GLIB 检查）；③audacious buildsys.mk 适配模式（无 check 目标、INSTALL_LIB 版本化布局、空前置 bindings 规则）；④autoconf 2.69 生成 configure 的 CONFIG_SHELL 无条件重执行块 × hnp bash 5.3 HMDFS getcwd 失败（新知：与 2.71 生成脚本行为不同，dbus-glib 未触发；绕过必须 unset 而非置空）；⑤Conan 2 `transform_downstream`：SHARED 包的 STATIC 依赖对下游强制 headers/libs=False 被 Skipped，PkgConfigDeps 会把 glib 从 .pc Requires 链静默丢弃，须以 `transitive_headers=True` 修复（本次 #11 首次实测）。E007/E236/E216/umask 077 复用现有图谱或既有先例条目。
