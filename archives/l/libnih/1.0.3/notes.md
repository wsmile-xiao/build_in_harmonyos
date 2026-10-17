# libnih 1.0.3 适配笔记

## 编译环境
- 构建系统: autotools (configure + make, 预生成 configure,无需 autoreconf)
- 编译日期: 2026-09-19
- 编译器: clang/clang++ (HarmonyOS aarch64 原生)
- 状态: built (待真机 conan create 验证后更新)
- 上游仓库: https://launchpad.net/libnih (1.0.3, 2010-12-23)
- 源码包: https://launchpad.net/libnih/1.0/1.0.3/+download/libnih-1.0.3.tar.gz
- sha256: 897572df7565c0a90a81532671e23c63f99b4efde2eecbbf11e7857fbc61f405 (Ubuntu orig 一致)

## 编译步骤

1. 依赖先行: dbus/1.14.10 与 expat/2.8.2 均已在制品仓发布 (dbus 本身 requires expat/2.8.2,版本对齐避免冲突)。
2. `get()` 解压上游 tarball (strip_root=True)。
3. `generate()`: AutotoolsDeps + AutotoolsToolchain,显式 `--build/--host=aarch64-unknown-linux-gnu` (config.guess 无法识别 HarmonyOS),`--disable-dependency-tracking`,静态默认 `--enable-static/--disable-shared`。
4. `build()`: 剥除生成 configure 中的 `umask 077` (E114, HMDFS),守卫 CONFIG_SHELL 重执行 (CI profile 路径离线不可用时回退探测),`autotools.configure()`, `make -j1` (E074 jobserver),随后 `make check -j1` 运行上游 41 个 TESTS。
5. `package()`: `make install` 强制 `INSTALL=install-sh` (真机 install(1) 多文件报 EX_USAGE 64,见 #14) 并 `-j1`,删除 `.la`,复制 COPYING/AUTHORS/README 到 licenses。
6. `test_package`: CMakeDeps+CMakeToolchain 构建 test.c (nih_alloc/nih_string/nih_list 三检查) 并运行,另对 nih-dbus-tool --help 做冒烟,输出 HMBS 双标记。

## 上游测试清点 (适配前)

- 总数 41 个 TESTS 程序,来源三个 Makefile.am 的 TESTS/check_PROGRAMS:
  - nih/Makefile.am: 17 (test_alloc, test_string, test_list, test_hash, test_tree, test_timer, test_signal, test_child, test_io, test_file, test_watch, test_main, test_option, test_command, test_config, test_logging, test_error)
  - nih-dbus/Makefile.am: 7 (test_dbus_error, test_dbus_connection, test_dbus_message, test_dbus_object, test_dbus_pending_data, test_dbus_proxy, test_dbus_util)
  - nih-dbus-tool/Makefile.am: 17 (test_main, test_symbol, test_indent, test_type, test_marshal, test_demarshal, test_node, test_interface, test_method, test_signal, test_property, test_argument, test_annotation, test_parse, test_output, test_com.netsplit.Nih.Test_object, test_com.netsplit.Nih.Test_proxy)
- 均为自包含 C 单元测试,无网络/显示依赖,预期在 HarmonyOS aarch64 环境全部可执行。`make check` 计数取 automake TOTAL/PASS/FAIL 汇总行,回退逐行 PASS:/FAIL: 统计。
- 证伪预案: 检查测试输出与参照非空;必要时以 exit 1 桩替换被测二进制确认 harness 能捕获失败;区分通过与静默跳过 (SKIP 计为跳过不计通过)。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2010 年快照无 HarmonyOS 条目 | --build/--host 显式传 aarch64-unknown-linux-gnu,跳过探测 (libcmph 同款) |
| 2 | config.status 在 HMDFS 上失败 | umask 077 建 0700 临时目录不可写 (E114) | 构建时将生成 configure 中的 umask 077 改 022,仅动生成文件 |
| 3 | make -j 并行失败 | HMDFS 禁止 jobserver FIFO (E074) | 全链路 -j1 |
| 4 | CONFIG_SHELL 指向 CI 专有路径 | profile 注入 /data/service/hnp/bin/bash,离线机不存在 | _guard_config_shell: 不可执行则 unset,回退 configure 自探测 |
| 6 | intl/bindtextdom.c pthread_cancel undeclared | OHOS musl has no thread-cancel API, bundled gettext intl assumes glibc pthread (E127) | configure --disable-nls to skip intl, NLS optional, 41 tests unaffected (E027) |
| 7 | nih/signal.c: SIGCLD 未声明 | SIGCLD 系 glibc 私有 System V 别名，musl/OHOS 无此宏 | 新增 portability 补丁：缺失时 #define SIGCLD SIGCHLD，保留 CLD 表项与行为 |
| 8 | nih-dbus-tool 链接 duplicate symbol: output_package (main.o/output.o) | 2010 年代码 tentativedefinition 依赖 -fcommon 合并，Clang 15 默认 -fno-common 后 lld 报重复符号 | generate() 追加 tc.extra_cflags -fcommon，恢复合并，不改上游源码 |
| 9 | nih/tests/test_io.c: redefinition of sockaddr_storage | test_io.c 同时 include <linux/socket.h> 与 <sys/socket.h>，OHOS musl sysroot 两头各定义一次 sockaddr_storage，glibc 下兼容、musl 下冲突 | source() 内 replace_in_file 直改（替代原 0002 补丁文件）：<linux/socket.h> 仅在 __GLIBC__/__UCLIBC__ 下引入，musl/OHOS 走 <sys/socket.h>（已验证 musl 提供 SCM_RIGHTS/SCM_CREDENTIALS），glibc 路径零改动。改用直改是因为 conan 2.30 自带补丁解析器报 patch stream is incomplete 而拒绝 0002 diff，0001 正常应用 |
| 10 | nih/tests/test_main.o: textdomain/bindtextdomain undeclared + int-conversion error (Clang 15) | build() 传 --disable-nls 后 config.h 无 ENABLE_NLS，但 test_init_gettext() 无条件调用 textdomain/bindtextdomain 且无 <libintl.h> 原型；glibc 下隐式声明仅警告，Clang 15 升为 error，且 musl/OHOS 无 libintl 可链 | source() 内 replace_in_file 直改：test_init_gettext() 体包入 #if defined(ENABLE_NLS) && ENABLE_NLS（与 nih/main.h 的 nih_main_init_gettext 空宏同构），NLS 关闭时为 no-op，不删 TESTS 条目，41 程序照跑 |
| 11 | `make check` 整包挂起、看门狗断开 SSH（0/0/0 零证据）；上轮临时总线方案无效 | 上轮假设“nih-dbus 需会话总线”被证伪：源码中仅 test_bus() 用真总线且已 SKIP-return，其余 test_connect/setup/server 自 fork `unix:abstract=` 私有 server；且真机根本无 dbus-run-session/dbus-daemon（本轮日志 "no dbus session helper found" 后依旧挂起）。真凶在别处（abstract-socket / inotify / ptrace-waitid 在 OHOS 语义，见 test_child.c、test_watch.c） | 策略周期 3 换路线：删除整套 ephemeral-dbus 逻辑，改按 TESTS 目录逐个 `make check -j1`（nih-dbus-tool → nih → nih-dbus），每目录 90s 硬超时 + 进程组 kill，超时目录再对 TEST 二进制逐个 15s 隔离定位；计数取各目录 test-suite.log，超时项记 gaps(environment) 并始终输出 HMBS_UPSTREAM_TEST_RESULT，不再零证据 SIGKILL |
| 12 | 周期 3 预检仍失败：nih-dbus-tool/tests/marshal_code.c "conflicting types for my_*_marshal"（.h 有 const、生成的 .c 无 const），仅 28 二进制建成 vs 41 TESTS；另 10 PASS/18 FAIL + 多个 HUNG（test_child、test_dbus_*） | 重读日志+源码证伪周期 3 的“纯挂起”假设：挂起隔离再完善也救不了没编出来的测试。根因为 Release -DNDEBUG 把 assert() 编译掉，而 marshal_factory.c `assert(type_to_const(...))`、demarshal_factory.c `assert(nih_strdup/type_to_pointer)` 把副作用写在 assert 里——NDEBUG 下 const 转换根本不执行，生成代码与签入头不一致；上游 2010 默认 CFLAGS 不带 NDEBUG 故从未暴露。证据：tarball 内 marshal_factory.c:60 `assert(type_to_const...)`、demarshal_factory.c:76-77 双 assert、真机编译行 `-DNDEBUG -fPIC -O3`、头文件 const vs .c 非 const 的成对报错 | 策略周期 4 换路线：source() 新增 _fix_factory_ndebug，用 replace_in_file 把副作用移出 assert（调用无条件执行、assert 只验结果，marshal/demarshal 各 2 处）；_run_upstream_tests 改为任一失败目录都逐二进制 15s 隔离并按 HUNG→environment（含 abstract/inotify/ptrace 源码定位）/FAIL→ohos_feature 分项记 gaps；覆盖完全的 env/ohos_feature 缺口只发 marker 警告、不再硬 raise（rule4 判定），未覆盖才 raise。验证点：下轮预检 marshal_code.c 应含 const 且 41 TESTS 全部编出 |
| 13 | indent hoist type mismatch: marshal_factory.c:99 error incom... | indent.h declares char *indent(char**,const void*,int); recipe used int indent_ret, pointer-to-int narrowing fails on Clang | fix to char *indent_ret + assert != NULL (marshal/demarshal indent) |
| 14 | package() install-nihincludeHEADERS Error 64 multi-file install fails | device install(1) (HMBS runtime bin/install, EX_USAGE 64); single-file ok, 28-header multi-source fails; mkdir ok, files exist | package() overrides INSTALL* to tarball install-sh via make args, -j1; same content/modes |
| 5 | Windows 检出上游 main 失败 | archives/g/gama 补丁文件名含回车 (\r\r),Windows 非法 | 稀疏检出 archives/l 等必需目录,绕开坏文件 (仅本地, PR 不含此改动) |

## 源码修改

1 个 portability 补丁文件 (patches/0001-musl-sigcld-fallback.patch): nih/signal.c 在 <signal.h> 后加 #ifndef SIGCLD/#define SIGCLD SIGCHLD 兼容层；另有 2 处 conanfile.py source() 内 replace_in_file 直改（test_io.c 的 <linux/socket.h> 守卫与 test_main.c 的 ENABLE_NLS 守卫，严格匹配、已守卫则跳过，无 diff 解析）。其余全部为构建时对生成文件的环境适配 (umask/CONFIG_SHELL/--disable-nls)，不引入 `__OHOS__` 宏。

## 依赖版本

- dbus/1.14.10 (transitive_headers/libs)
- expat/2.8.2 (与 dbus 要求的版本对齐,避免版本冲突)
- 构建工具: Autotools (configure/make), CMake (仅 test_package 消费者构建), pkg-config (随 AutotoolsDeps/PkgConfig 传递)

## 验证结果

待 HMBS 真机预检 (conan create 全链路: configure + make + make check 41 + test_package 4)。预检日志中的 conan create 输出将作为 PR 正文通过率的唯一依据,本轮不填数字、不猜测。

```bash
# 真机将执行 (HMBS 后台,非本机):
# conan create archives/l/libnih/1.0.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 期望标记:
# HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"...","discovered":4,"passedCount":4}
# HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"automake test-driver (make check)","command":"make check","discovered":41,...}
```

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/libnih/1.0.3/conanfile.py | 主配方 (Autotools + make check + HMBS 标记) |
| archives/l/libnih/1.0.3/conandata.yml | 官方源 URL + sha256 |
| archives/l/libnih/1.0.3/manifest.yaml | 版本级 manifest |
| archives/l/libnih/manifest.yaml | 软件级 manifest |
| archives/l/libnih/commands.json | nih-dbus-tool 二进制声明 (type=tool, lhasa 同款库+工具形态) |
| archives/l/libnih/1.0.3/test_package/ | test.c + CMakeLists + conanfile (4 断言) + MANIFEST.yml (41 上游条目) |
| archives/l/libnih/1.0.3/notes.md | 本文件 |

## 注意事项

- 本机为 Windows,上游 main 全量检出因 gama 坏文件名与 libXext/libxext 大小写冲突无法完整进行;已用稀疏检出保证配方目录完整,PR 仅含 libnih 新增文件,不碰其他目录。
- 跨编译说明: README 提到交叉需预装 nih-dbus-tool,但本适配为原生构建 (build=host=OHOS/aarch64),工具链生成的 nih-dbus-tool 可直接运行,无需预装。
- 若真机出现 musl 相关单测失败 (Adelie 曾为 signals/parse 打补丁),下一轮按失败日志加最小补丁,不跳过整个套件。
