# lcmaps 1.6.7 — OHOS (aarch64/musl) 适配笔记

## Flavour 选择

默认 GSI 面在 configure 阶段三重硬失败：`AC_GLOBUS([GSSAPI_GSI])`、
`AC_GLOBUS([GSI_CREDENTIAL])`、`AC_CHECK_LIB([crypto])`（globus/voms 仓内无配方，
已实查 archives/g、archives/v）。采用上游原生支持的 `--disable-gsi-mode` 面：

- 产物：`liblcmaps_without_gsi.so`（核心引擎：evaluationmanager/pdl + pluginmanager
  + credential handling）+ `liblcmaps_return_poolindex_without_gsi.so` +
  `liblcmaps_gss_assist_gridmap_without_gsi.so`（LIBADD 核心库）。
- 头文件：`include/lcmaps/*.h`（26 个，含 nodist 生成头 lcmaps_version.h）。
- .pc：`lib/pkgconfig/lcmaps-without-gsi.pc`（链接面）与
  `lib/pkgconfig/lcmaps-basic-interface.pc`（纯头文件面，recipe 将上游装到
  share/pkgconfig 的 interface 面 .pc 归位到 lib/pkgconfig）。下游
  lcmaps-plugins-basic 以 `pkg-config lcmaps-basic-interface` 消费。

## 依赖闭包（libc-only）

- dl：configure `AC_CHECK_LIB([dl],[dlopen])` 硬检查在 OHOS 工具链实测可过
  （musl dl* 在 libc / -ldl 探针链接成功，知识 E013）。
- LEXLIB：tarball 自带预生成 `pdl_yacc.c`/`pdl_lex.c`，configure 在无 flex 时
  置 `LEXLIB=''`，无需 flex/bison。
- 不跑 autoreconf（E089：tarball 自带完整 configure/aclocal.m4）。

## 平台补丁（仅构建辅助脚本，无源码/平台条件宏）

- `0001-config-guess-harmonyos.patch`：2023-06-23 版 config.guess 不识别
  `uname -s` = "HarmonyOS"，落入编译回退路径且该路径在 OHOS 存储上失败
  （实测 `can't create .../dummy.c: Permission denied`）→ 在主 case 分支
  顶部加入 HarmonyOS 识别，返回 `aarch64-unknown-linux-ohos`。
  与 libmnl/1.0.5 patches/0001 同源同因（hunk 上下文不同故单独生成）。
- `0002-config-sub-ohos.patch`：config.sub（新版重写格式）识别
  `linux-ohos*` OS 与 `linux-ohos*` kernel-os 组合；实测
  `aarch64-unknown-linux-ohos` 校验通过。与 libmnl/1.0.5 patches/0002 同因
  （libmnl 版本 hunks 面向旧版 config.sub，不通用，故单独生成）。

## 路径宏

`LCMAPS_ETC_HOME=<prefix>/etc/lcmaps`、`LCMAPS_LIB_HOME=<prefix>/lib`、
`LCMAPS_MOD_HOME=<prefix>/lib/lcmaps` 编译期 -D 写死，全部由 prefix 推导，
Conan 包内自洽，无需 patch。

## 符号导出

without-gsi 三个库的 `*_la_LDFLAGS` 为空，无 `-export-symbols`/版本脚本，
默认导出全部公共符号（lcmaps_init/lcmaps_run/lcmaps_term、
lcmaps_return_poolindex_without_gsi 等），满足 dlsym(RTLD_DEFAULT) 消费面。
（注：1.6.7 源码中不存在 lcmods_get_*_version 符号——API 版本以安装头
lcmaps_version.h 的宏 LCMAPS_API_{MAJOR,MINOR,PATCH}_VERSION 表达。）

## 上游测试（NO_UPSTREAM_TESTS，discovery.status=EVIDENCE_COMPLETE）

- 已检查入口：顶层/src/examples/doc Makefile.am 均无 check 目标、TESTS、
  check_PROGRAMS；`src/lcmaps_test.c` 与 `src/evaluationmanager/pdl_test.c`
  仅列于 EXTRA_DIST（lcmaps_test.c 为手动 GSI 客户端）；examples 为演示插件。
- 证据路径：lcmaps-1.6.7.tar.gz 内 Makefile.am、src/Makefile.am、
  examples/Makefile.am、doc/Makefile.am、src/lcmaps_test.c。
- 结论：上游零自动化测试；产物验证以 test_package 的 OHOS 冒烟用例（dlopen/
  dlsym/版本宏/包内清单）真实执行代替。

## 知识检索记录

- E013（-ldl / musl dl 在 libc）：configure 硬检查与 LDFLAGS 均可自然解析。
- E075（C_INCLUDE_PATH 陷阱）：recipe generate() 显式 unset
  C_INCLUDE_PATH/CPLUS_INCLUDE_PATH/LIBRARY_PATH。
- E089（勿 autoreconf）：build() 仅 configure+make。
- E046（HMDFS 拒载未签名 ELF）：test_package 对 dlopen Permission-denied
  按 SKIP 处理（沿用 autofs 先例）。
- build-chain-pitfalls「共享库链接闭包」：本包 .so 无跨 conan 依赖闭包
  （libc-only），test_package 刻意不直链 .so、以 dlopen 绝对路径消费，
  规避运行期库搜索路径问题。
