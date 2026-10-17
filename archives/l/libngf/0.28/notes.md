# libngf 0.28 适配笔记

## 编译环境

- 构建系统: 上游 autotools（configure.ac + Makefile.am，GitHub tag 归档），配方侧 direct-cc 直编（绕过自举，见问题 7）
- 上游仓库: https://github.com/sailfishos/libngf（tag 0.28，commit 05ea200943795ae343bad5748ae125431b3b9837）
- 源码包: https://github.com/sailfishos/libngf/archive/refs/tags/0.28.tar.gz（27770 字节，sha256 见 conandata.yml）
- 编译日期: 2026-09-19
- 编译器: clang/clang++（真机 /data/service/hnp 工具链，conanbuild env 注入）
- 状态: built（待 HMBS 真机预检回填实测证据后由后端统一提交）

## 上游审计（适配前清点）

- 构建入口: `configure.ac`（AC_INIT libngf/ngf.h，AM_INIT_AUTOMAKE，PKG_CHECK_MODULES 依次检查 `dbus-1`、`glib-2.0 dbus-glib-1`、`check`）+ 顶层 `Makefile.am`（SUBDIRS = libngf examples tests）。
- 归档内无 generated `configure`（git 快照包的固有形态，上游本需 `autoreconf` 自举；本配方因问题 7 改直编）；`m4/` 目录同样缺失（直编不需要）。
- 库本体: `libngf/`（client.c、proplist.c，对外 libngf0，public 头 ngf.h/proplist.h/client.h，仅链接 `dbus-1`）。
- 可执行物: `examples/ngf-client.c`（交互式 stdin 调试客户端，`dbus_bus_get(DBUS_BUS_SYSTEM)` 强依赖活总线；仅随 `make install` 安装，不作为交付 CLI 打包）。
- 上游测试（`tests/Makefile.am`: TESTS = test-proplist test-client，libcheck 框架）:
  - `tests/test-proplist.c`: 7 个 START_TEST（test_set_get、test_parse_values、test_limits、test_foreach、test_foreach_extended、test_copy、test_get_keys），纯内存逻辑，约 60 个 fail_unless 断言，无总线依赖。
  - `tests/test-client.c`: 6 个 START_TEST（test_create_client、test_failed_create_client、test_play_event_NULL、test_play_client_NULL、test_play、test_callback），其中 3 个（create、play NULL event、play sms）调用 `dbus_bus_get(DBUS_BUS_SYSTEM)`，约 10 个断言。
  - 合计 13 个 libcheck 用例（7 + 6），来源目录 `tests/`。
- 依赖链（configure 时全部 PKG_CHECK_MODULES，缺一不可）: dbus、glib、dbus-glib、check；版本钉死 dbus-glib/0.114 的已有闭包（dbus/1.14.10、glib/2.88.0）以避免钻石冲突，check 取 check/0.15.2。

## 编译步骤（direct-cc，不跑 autoreconf/configure/make）

```bash
# 编译器来自 tools.build:compiler_executables（回退 PATH 上的 clang/cc）；
# 标志 = -O2 -D_GNU_SOURCE（上游 configure.ac 同款）+ 私有 values.h shim 目录
#   + host 依赖 cpp_info 聚合的 -I/-D/-L/-l（dbus+glib+dbus-glib+check 及其传递闭包），-lm 保底
cc -O2 -D_GNU_SOURCE -fPIC -I<src> -I<build>/hmbs_shim <dep-incs> <dep-defs> \
   -c libngf/proplist.c -o proplist.o
cc -O2 -D_GNU_SOURCE -fPIC -I<src> -I<build>/hmbs_shim <dep-incs> <dep-defs> \
   -c libngf/client.c -o client.o
ar rcs libngf0.a proplist.o client.o            # shared=True 时改为 cc -shared -o libngf0.so
cc <cflags> -c tests/test-proplist.c -o test-proplist.o
cc <cflags> test-proplist.o proplist.o -o test-proplist <dep-libdirs> <dep-libs> -lm
TMPDIR=<hmbs-writable> ./test-proplist > test-proplist.log 2>&1
# 安装：include/libngf-1.0/libngf/*.h、lib/libngf0.a(.so)、lib/pkgconfig/libngf0.pc（${pcfiledir} 相对前缀）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 归档无 `configure`，原计划 `autoreconf` 自举 | GitHub tag 归档为 git 快照，不含自举产物 | 已被问题 7 取代：不再自举，direct-cc 直编（下） |
| 2 | （原）config.guess 不识 OHOS | autotools 上游早于 OHOS（E007） | 不适用：不跑 configure，无需 --build 三元组 |
| 3 | （原）HMDFS 下 configure 私有 tmp 目录创建失败 | configure 内 `umask 077`（E011） | 不适用：不跑 configure；测试二进制直跑，仅需 TMPDIR 可写（hmbs 注入） |
| 7 | 真机 `autoreconf --force --install` exit 126：`.../p/bin/aclocal[8]: .../bin/.aclocal-real: No such file or directory` | 远端 automake/1.18 二进制包（autom3efab95d532f9）缺 `bin/.aclocal-real` 点文件（DRAFT-6051 类半残包，与 libnxml 0.18.5 同包哈希前缀）；与 DRAFT-6049 的 perl-XS 失配不同（本轮是文件缺失，无 handshake 报错）。配方侧无法重建远端工具包 | 弃用自举改 direct-cc 最小源集（librcc 0.2.13 先例）：删 m4/autoconf/automake/libtool tool_requires（仅留 pkgconf），build() 按 `libngf/Makefile.am`（库=proplist.c+client.c，仅链 dbus-1）与 `tests/Makefile.am`（test_proplist_SOURCES=test-proplist.c+../libngf/proplist.c，CHECK+BASE+GLIB 闭包）直接编译链接；全树 grep 确认无 `config.h`/`HAVE_CONFIG_H` 引用故不生成 config.h；`tests/test-proplist.c` 的 `<values.h>`（glibc 私有，musl 缺失）用配方私有 shim 目录兼容，测试源码零修改 |
| 4 | `test-client` 需活总线 | `dbus_bus_get(DBUS_BUS_SYSTEM)`；OHOS 设备/CI 无 system bus（dbus-glib 0.114 先例：同类总线测试 exit 127） | build() 仅跑 `make check TESTS="test-proplist"`（7/7），6 个 client 用例以 `total:13/excluded:6` 资源门控声明，不计入通过率 |
| 5 | `ngf-client` 是否触发 R38 commands.json | 上游 `Makefile.am` 默认构建并随 `make install` 安装 `bin/ngf-client` | 直编仅编译库源文件（proplist.c+client.c），`examples/ngf-client.c` 不构建不安装：该二进制为交互式调试客户端（stdin 循环 + 活总线），非交付 CLI；包保持纯 library，无 commands.json |
| 6 | 消费者侧 CMakeDeps 在 OHOS glib 二进制上 include 元数据为空（E216 类） | 已发布 glib 包的 CMake 元数据缺失 | test_package 走 PkgConfigDeps + `pkg-config --cflags --libs libngf0`（dbus-glib 0.114 先例） |
| 8 | 真机 build() 执行 `./test-proplist` 报 Error 127（conanbuild 单环境） | 测试二进制动态链接 host 共享库（check/dbus/glib 闭包），仅 `env="conanbuild"` 时 LD_LIBRARY_PATH 为空，loader 解析失败，sh 返回 127（DRAFT-332 同类）；且 generate() 未生成 VirtualRunEnv，conanrun 域为空 | generate() 增 VirtualBuildEnv/VirtualRunEnv；执行改 `env=["conanbuild","conanrun"]` 并用 Environment.prepend_path("LD_LIBRARY_PATH","/system/lib64") 包裹（DRAFT-13536 顺序要求）；失败仍先 emit 上游 marker 再抛，门禁不缺证据 |
| 9 | 上轮 conanrun 组合仍 Error 127：`Error loading shared library libcheck.so` + `suite_create/srunner_* symbol not found`（check 包 libdir 不在生成的 run 路径上） | VirtualRunEnv 未覆盖 check 的 libdir；继续调环境变量已证伪无效 | 换策略：测试二进制优先静态链接（`_test_link_args` 把 `-l<name>` 原位替换为各依赖包 `lib/lib<name>.a` 全路径，缺 .a 才保留 `-l`），并为全部依赖 libdir 内嵌 `-Wl,-rpath`；二进制不再依赖 loader 路径即可启动（本轮预检上游 7/7 通过证实） |
| 10 | test_package `build()` 的 `$(pkg-config ...)` 报 `/bin/sh: pkg-config: inaccessible or not found`，连带 `libngf/proplist.h` 找不到 | 测试 shell 内 pkg-config 二进制不可执行（沙盒/环境类）且 `$(...)` 另需 shell 临时文件；属消费者侧 R33 违规（主配方早已用 Python 聚合 cpp_info，不调 shell pkg-config） | test_package 新增 `_dep_flags` 在 Python 内聚合全部依赖 cpp_info 的 -I/-D/-L/-l，直传 cc；不再调用 pkg-config 二进制 |
| 11 | 本轮 test_package `./test_ngf` Error 127：`Error loading shared library libcheck.so`，`HMBS_TEST_PACKAGE_RESULT passed:false` 致 rule4 incomplete | 消费者 `_dep_flags` 聚合了 libngf 传递闭包（含 check 的 -lcheck/-lsubunit），二进制动态链接后 VirtualRunEnv 未覆盖 check libdir，loader 启动即失败（与主配方问题 9 同类；test.c 本身只用 proplist API 并不需要 check） | test_package 复用主配方已验证的 `_test_link_args`：`-l<name>` 原位替换为各依赖包 `lib/lib<name>.a` 全路径并内嵌全部 libdir `-Wl,-rpath`，`test()` 运行域改 `env=["conanbuild","conanrun"]` 并 prepend `/system/lib64`；不断言删减、不跳过，上游标记与计数口径不变 |

## 源码修改

无 `patches/`（测试源码零修改；musl 缺 `<values.h>` 由配方在 build 目录生成私有 shim 头解决，不进源码树。若真机报其他系统头或 HMDFS 细节问题，后续轮次按 `refresh-patch --auto` 增补并更新本节）。

## 依赖版本

- dbus/1.14.10、glib/2.88.0、dbus-glib/0.114、check/0.15.2（regular requires）
- pkgconf/3.0.6（tool_requires，仅供 test_package 的 pkg-config 消费者路径；主构建直调 cc 不依赖 autotools 链）
- 构建期不再引入 m4/autoconf/automake/libtool（问题 7），不引入 perl tool_require
  （配方不调用 perl；conan perl 为 OHOS 交叉构建，Cwd.so 在构建机无法 dlopen，burp2 先例）。

## 验证结果

```bash
# 以下由 HMBS 后台真机预检统一执行并回填，本轮不预估数字
conan create archives/l/libngf/0.28 --profile ohos-aarch64 --build=missing
# 预期门禁输出（真机实测为准，数字来自确定性日志源）:
# 上游标记: HMBS_UPSTREAM_TEST_RESULT={"status":"incomplete","framework":"check/direct-cc","command":"./test-proplist","discovered":13,"executed":7,"passed":7,"failed":0,"skipped":6,"gaps":[{"count":6,"category":"ohos_feature",...}]}
#   discovered=13 为审计总数（7 proplist + 6 client）；executed/passed/failed
#   唯一来源 build/test-proplist.log 的 "Checks: 7, Failures: 0, Errors: 0"；
#   skipped=6/discovered-executed 为资源门控的 client 用例数；
#   status 用 incomplete 而非 passed（rule4：executed!=discovered 时 passed
#   自相矛盾；libm2k/0.9.0 先例：gaps 存在时必须 incomplete）；
#   gaps 6 项为需 D-Bus system bus 的 client 用例（ohos_feature）。
# 新增标记: HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"./test_ngf","discovered":8,"passedCount":8}
#   唯一来源 test_ngf_output.txt 中 8 个 CHECK-OK 行与 ALL 8 CHECKS PASSED 行。
```

- 证伪预案（真机轮执行）: ① 确认 `test-proplist.log` 含 libcheck "Checks: 7, Failures: 0, Errors: 0" 行且为真实断言执行（非空 harness）；② 必要时将 `libngf/proplist.c` 换成返回失败的桩重跑，确认 harness 能抓到失败；③ 区分"通过"与"静默跳过"（client 6 用例计 excluded，不计 passed）。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libngf0.a（静态默认；shared=True 时为 .so） | 主库 |
| include/libngf-1.0/libngf/*.h | 公共头 |
| lib/pkgconfig/libngf0.pc | pkg-config 元数据 |
| res/hmbs_upstream.json | 上游证据（供 test_package 缓存命中轮重发） |

## 注意事项

- 本包默认静态（default_options shared=False），与 dbus-glib/0.114 的 OHOS 静态策略一致，避免把静态 glib 吞成第二份 GType 运行时。
- 申请人: zhangyuge147；队伍名称: 龙骑士。
- 在 HarmonyOS aarch64 环境实测（真机预检通过结论以 HMBS 日志与 CI 最终结果为准）。
