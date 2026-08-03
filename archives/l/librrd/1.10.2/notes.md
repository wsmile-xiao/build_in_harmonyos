# 适配笔记 — librrd 1.10.2（RRDtool 时间序列数据库 C 库）

## 2026-08-01 适配

### 库信息
- **软件**: librrd (RRDtool)
- **版本**: 1.10.2
- **构建系统**: autotools
- **许可证**: GPL-2.0-only
- **上游**: https://github.com/oetiker/rrdtool-1.x
- **功能**: 时间序列 Round Robin 数据库 C 库

### 构建说明
- 使用官方 release tarball（`releases/download/v1.10.2/rrdtool-1.10.2.tar.gz`），**已含预生成 configure**，无需 automake/autoreconf
- 通过 `--disable-*` 选项禁用图形/脚本绑定/文档特性
- 仅构建 librrd 库（`make -C src librrd.la`），不构建 rrdtool 二进制（其依赖被禁用的 rrd_graph 等）

### 依赖
- **构建依赖**: pcre/8.45（rrd_create.c 的正则支持；无 glib 时走 pcre 分支）
- **运行时**: 仅系统 libm、libpthread、libdl

### 适配变更（7 个补丁）
| 补丁 | 说明 |
|------|------|
| 0001-config.guess-ohos | config.guess: 添加 aarch64 OHOS/HarmonyOS 平台识别 |
| 0002-config.sub-ohos | config.sub: 添加 ohos-linux 三元组识别 |
| 0003-configure-no-glib-pcre | configure: glib/pcre 硬性检查降级为警告 + umask 077→022（OHOS 沙箱可写临时目录） |
| 0004-rrd-create-no-glib | rrd_create.c: 条件包含 glib.h + 无 glib 时最小 GList 替代实现 |
| 0005-rrd-config-pcre | rrd_config.h: HAVE_PCRE_COMPILE + 取消 ENABLE_NLS/HAVE_G_REGEX_NEW/STRERROR_R_CHAR_P/HAVE__NL_TIME_WEEK_1STDAY |
| 0006-rrd-utils-no-glib | rrd_utils.c: glib.h 条件包含 + g_thread_init 守卫 |
| 0007-rrd-update-no-glib | rrd_update.c: glib.h 条件包含 + GTree 缓存条件化 |

### 本地验证记录（实测）
| 检查项 | 结果 |
|--------|------|
| conan export | ✅ 成功 |
| SHA256（官方 tarball） | ✅ 9787114551ee9b5db7c72722736388dcc54bf00ded51b5dd47feed11fb179fe4 |
| configure（OHOS aarch64） | ✅ 通过 |
| make -C src librrd.la | ✅ 编译成功 |
| test_package — rrd_strversion() | ✅ 输出 "1.10.2" |
| test_package — rrd_version() | ✅ 输出 "1.10" |
| test_package 总通过 | ✅ 2/2 |

