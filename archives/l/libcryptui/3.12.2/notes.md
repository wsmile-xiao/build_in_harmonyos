# libcryptui 3.12.2 适配笔记

## 编译环境
- 构建系统: autotools（`configure` + `make`，上游 configure.ac 由 autoconf 2.69 生成）
- 编译日期: 2026-10-01（本机 `conan create` 实编通过）
- 编译器: clang/clang++（`/data/service/hnp/bin`，llvm 15.0.4 工具链，target `aarch64-unknown-linux-ohos`）
- 依赖: gtk/3.24.43（OHOS shared 发布二进制，传递 glib/pango/cairo/gdk-pixbuf/atk）、dbus-glib/0.114.1（依赖对齐版本，见 archives/d/dbus-glib/0.114.1/notes.md；本图谱解析为**静态归档**）
- 状态: **本机 `conan create` 实编通过**（2026-10-01，G0–G4 全 PASS，含 test_package
  16 项 TAP 断言实测 16/16）→ manifest `status: built`。制品上传由 CI release 流水线在
  合并到 main 后完成（不预支 published）。

## 背景

libcryptui 是 Seahorse（GNOME 密码与密钥管理器）拆出的**密钥选择/加密 UI 库**，
供第三方应用复用"选择收件人/签名密钥"的对话框与密钥模型。构建系统为 autotools，
上游自 2014 年（3.12.2）后未再发布，属 GNOME 3.x 时代的 GTK3 库。

本次按「依赖项」独立适配：almanah 0.12.4（主线）的 `meson.build` 把 `cryptui-0.0`
列为强制依赖，故先补齐本库。

库本体只依赖 `gtk+-3.0` 与 `dbus-glib-1`（见 `libcryptui/cryptui.pc.in` 的
`Requires: gtk+-3.0 gio-2.0 dbus-glib-1`）；`gnome-keyring-1`、`gpgme`、`libSM/libICE`、
`libnotify` 仅 `daemon/`、`libegg/` 使用，本归档已把这两条支线从构建中裁掉
（详见「源码修改」）。

## 上游测试（N 口径 + 逐项定性）

| 口径 | 数量 | 说明 |
|------|------|------|
| 源码包内 `test/`、`tests/` 文件数（N 口径） | 3 | `libcryptui/tests/`：`Makefile.am`、`Makefile.in`、`cryptui-test-ui.c` |
| 其中可执行用例源文件 | 1 | `libcryptui/tests/cryptui-test-ui.c`（138 行） |
| 可 headless 运行 | 1 | keyset 模式（dbus-run-session + broadwayd，见下） |
| 显示依赖限制 | 1 | `cryptui-test-ui.c:120` 首行即 `gtk_init(&argc, &argv)`（经 broadway 无头后端满足） |

**上游用例真实执行方案（rule4，2026-10-02 修复）**：唯一上游用例
`cryptui-test-ui.c` 的 `main()` 先 `gtk_init(&argc, &argv)`，其 `keyset` 模式
不弹对话框（遍历 keyset 后 return 0）。真实执行三前提全部在依赖图内解决：
① `GDK_BACKEND=broadway` + `broadwayd`（gtk 包 bin/ 自带无头后端守护进程）；
② **broadwayd 的 unix socket 落在 `$XDG_RUNTIME_DIR`**——此前「bind 被平台
拒绝」的真实根因是 E002（未设 XDG_RUNTIME_DIR 时 socket 落 /tmp，HMDFS 只读），
把 XDG_RUNTIME_DIR 指向构建目录后 bind 正常；③ `dbus-run-session
--config-file=<dbus 包>/share/dbus-1/session.conf`（dbus-daemon 编译期烘焙的
DATADIR 指向旧 conan 缓存，须显式传运行时解析的包内配置）。执行形态：
`dbus-run-session --config-file=... cryptui-test keyset` → GTK/broadway/DBus
栈全链路初始化 → exit 0（`upstream test case PASSED`）。配方 `package()` 把
构建树 `.libs/cryptui-test`（libtool 真 ELF，经 os.walk+魔数识别）收入包内
`tools/` 并随包签名（E489）；test_package `test()` 负责拉起 broadwayd/dbus
会话并执行。

| 上游用例 | 状态 | 证据 |
|----------|------|------|
| `libcryptui/tests/cryptui-test-ui.c`（keyset 模式） | **executed, exit 0** | test_package `upstream-test.log`（dbus-run-session + broadwayd + GDK_BACKEND=broadway） |

**消费者兜底**：`test_package/test_libcryptui.c` 共 **16 项 TAP 断言**，全部走非显示、
非 DBus 会话总线路径，真实消费被测产物：

| 断言组 | 项数 | 覆盖内容 |
|--------|------|----------|
| ABI 常量 | 6 | `CryptUIEncType`/`CryptUIKeyFlags`/`CryptUILocation`/`CryptUIValidity` 的跨进程约定值（上游注释要求"Never ever change"） |
| 库内真实逻辑 | 5 | `cryptui_key_get_base()`：裸密钥、单冒号、双冒号截断、4 段以上、前导冒号 |
| GObject 类型系统 | 3 | `CRYPTUI_TYPE_KEY_STORE` 已注册；父类为 `GtkTreeModelSort`（gtk-3 链接完整性）；`G_TYPE_OBJECT` 派生 |
| 模型列布局 | 2 | `NAME == 0`/`KEY == 6` 列序、`NCOLS == 7` |

刻意避开的入口（平台限制，非配方缺陷）：`cryptui_prompt_*` 系列需 GTK 对话框，
`cryptui_key_get_enctype()` 与 `cryptui_key_store_new()` 分别会触发 DBus 会话总线
（`dbus_g_bus_get`）与 `g_settings_new`（需已编译的
`org.gnome.seahorse.recipients` schema）。测试二进制逐项打印 TAP 结果。

## 编译步骤

```bash
# 源码（download.gnome.org 官方发布站；sha256 见 conandata.yml）
curl -fL -o libcryptui-3.12.2.tar.xz \
  https://download.gnome.org/sources/libcryptui/3.12/libcryptui-3.12.2.tar.xz
# 71ead1a7b496f07f6c5102ae79945dd2515b7b9342c6edefe58b47318be20866

export PATH=~/.local/bin:/storage/Users/currentUser/usr/local/bin:/data/service/hnp/bin:$PATH
conan create archives/l/libcryptui/3.12.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 遇到的问题与解决方案

| # | 风险点 | 根因 | 本配方对策 |
|---|--------|------|-----------|
| 1 | `config.guess` 报 `unrecognized system` | 2013 年版 config.guess 不识别 `HarmonyOS` 内核（E007/E160） | `0001-config.guess.patch` 在 `UNAME_SYSTEM` 分支补 `HarmonyOS\|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl`，`0002-config.sub.patch` 补 `*-linux-ohos` 三元组 |
| 2 | `AC_PATH_PROG(intltool-update)` 报 `Perl module XML::Parser not found` | HMDFS 上 Perl 的 XS 模块不可加载；`po/` 已裁掉，intltool 无实际用途 | `0003` 硬编码 `INTLTOOL_APPLIED_VERSION=0.51.0` 并把版本过旧的 `as_fn_error` 改为 `:` |
| 3 | `config.status` 阶段 `confXXXXXX/subs1.awk: Permission denied` | HMDFS 的 SGID 语义把 `umask 077 && mktemp -d` 目录映射成 `drwx--S---`（E011） | `0003` 把内嵌模板的 `umask 077 && mktemp -d` 换成普通 `mktemp -d`（目录权限继承当前 umask） |
| 4 | `configure` 报 `working directory cannot be determined` | `ac_pwd=\`pwd\`` 在 HMDFS/FUSE 挂载上可能失败 | `0003` 加 `2>/dev/null \|\| ac_pwd=$PWD` 回退 |
| 5 | `Package requirements (sm ice) were not met` | OHOS 无 libSM/libICE，其唯一消费者 `libegg/eggsmclient` 已被裁掉，但 configure 仍把它当硬依赖 | `0003` 把该 `as_fn_error` 降级为提示（库本体不引用 SM/ICE 符号） |
| 6 | `daemon/` 需要 gnome-keyring + gpgme + MIME 数据库 | 库本体（`libcryptui/`）不需要；这两条支线让依赖面失控 | `0004-subdirs.patch` 把 `SUBDIRS` 裁为 `libcryptui data`，`Makefile.am`/`Makefile.in` 同步 |
| 7 | 构建期 `glib-genmarshal` 缺席 | marshaller 由 `$(GLIB_GENMARSHAL)` 生成；OHOS 上 conan 包内该 ELF 未签名、直接 exec 被 XPM 拒绝 | tarball 自带 `cryptui-marshal.c/.h`（2014）比 `cryptui-marshal.list`（2011）新 → `build()` 中 `_pin_generated_marshallers()` 触摸产物保证 make 判定 Up-to-date，不触发工具 |
| 8 | 安装期 `glib-compile-schemas` 无法从缓存路径 exec | 未签名 aarch64 ELF 直接执行被拒（E077） | `configure --disable-schemas-compile`；`package()` 内 `_compile_gsettings_schema()` 把工具拷到构建目录、按需重签后执行，失败仅告警 |
| 9 | `--no-allow-shlib-undefined` 拦下链接 | cmd-pkgs 的 gtk/cairo-gobject 等 `.so` 含未解析传递符号（`g_libintl_*`/`ffi_type_*`/`pcre2_*`） | `generate()` 注入 `-Wl,--allow-shlib-undefined`（gtkspell3 同款） |
| 10 | SDK lld 启动即缺 `libxml2.so.16` | CI shell 前置 `~/usr/local/lib` 遮蔽 ABI 匹配版本；`/tmp` 只读导致 `config.status` 临时目录失败（E002） | `generate()` 经 `buildenv_info`、`build()/package()` 经 `Environment` 双层注入：SDK `llvm/lib`（+ `aarch64-linux-ohos` 子目录）入 `LD_LIBRARY_PATH`，`TMPDIR/TMP/TEMP` 指向构建目录内 `tmp/` |
| 11 | configure 报 `XML::Parser perl module is required for intltool` | `0003` 只覆盖了 intltool 的版本硬闸（`INTLTOOL_APPLIED_VERSION`）与 `perl 5.8.1` 检查，**`XML::Parser` 模块检查是另一处 `as_fn_error`**；本机 perl 的 XS 模块在 HMDFS 上不可加载 | `0005-configure-intltool-perl.patch`：perl 存在性 / `perl >= 5.8.1` / `XML::Parser` 三处 `as_fn_error` 改为 `:`（`po/` 已裁，intltool 无消费者）。⚠️ **补丁必须按 conan 依序应用后的实际内容生成**（post-0001..0004），按 pristine 上下文生成会在 `apply_conandata_patches()` 抛 `Failed to apply patch` |
| 12 | configure 报 `glib-compile-schemas not found.` | 非交叉分支取 `GLIB_COMPILE_SCHEMAS=$PKG_CONFIG --variable glib_compile_schemas gio-2.0`，conan 生成的 `gio-2.0.pc` **无该变量** → 空值 → `as_fn_error`。**不是 PATH 查找**（故把依赖 `bin/` 前置进 PATH 无效）；`--disable-schemas-compile` 只管 install 期钩子，不豁免 configure 期探测 | `0006-configure-glib-compile-schemas.patch`：变量为空时回退 `command -v glib-compile-schemas`（构建期由 `_stage_build_tools()` 把依赖包工具拷贝+按需重签入构建目录并前置 PATH） |
| 13 | 链接 `libcryptui.la` 报 `'//lib/libpcre2-8.la' is not a valid libtool archive`（+ `library ... was moved`） | 依赖包 `.la` 的 `libdir='//lib'`（conan 以 `--prefix=/` 构建的拼接产物）；libtool 依 `libdir` 读依赖 `.la` 时命中不存在的 `//lib/...`。由 glib→pcre2 链触发（freetype/libpng/fribidi 同报 `was moved`）（E236） | `_fix_dependency_la_metadata()`：`build()` 中就地改写所有 host 依赖 `lib/**.la` 的 `libdir`/`dependency_libs` 为真实路径（libgsf 1.14.5 先例），不动依赖配方本体 |
| 14 | test_package 报 `GTK3/dbus-glib runtime libs missing ... ['libdbus-glib-1.so.2']` | dbus-glib 在本图谱解析为**静态归档**（包内仅 `libdbus-glib-1.a`）；实测产物 `libcryptui.so` 的 `NEEDED` 无 `libdbus-glib-1.so.2` → 该硬编码运行库存在性条目对静态依赖不成立 | `_provides_shared()` 条件校验：仅当依赖图确实提供 `libdbus-glib-1.so*` 时才要求该条目；其余 4 个 GTK3/glib 运行库照旧硬校验（保留"未真跑不得报 PASS"的口径） |

## 源码修改

六处补丁（`patches/`，均以 `a/`、`b/` 前缀生成 → conandata 中显式 `strip: 1`）：

| 补丁 | 目标文件 | 变更 |
|------|----------|------|
| `0001-config.guess.patch` | `config.guess` | 补 HarmonyOS/HongMeng 内核识别（musl libc） |
| `0002-config.sub.patch` | `config.sub` | 接受 `aarch64-unknown-linux-ohos` 三元组 |
| `0003-configure.patch` | `configure` | intltool 版本硬闸豁免、`ac_pwd` 回退、SM/ICE 硬依赖降级、`mktemp -d` 目录权限（共 10 处 hunk） |
| `0004-subdirs.patch` | `Makefile.am`、`Makefile.in` | `SUBDIRS` 裁为 `libcryptui data`（去掉 `libegg libcryptui po data pixmaps daemon reference` 中的 daemon/libegg/reference/po/pixmaps） |
| `0005-configure-intltool-perl.patch` | `configure` | perl 存在性 / `perl >= 5.8.1` / `XML::Parser perl module is required` 三处 `as_fn_error` → `:`（`po/` 已裁，intltool 无消费者） |
| `0006-configure-glib-compile-schemas.patch` | `configure` | `$PKG_CONFIG --variable glib_compile_schemas gio-2.0` 为空时回退 `command -v glib-compile-schemas` |

补丁已在**纯净上游副本**上按序 `patch -p1` 全量应用验证（**6/6 干净命中**），应用结果与
生成基准逐字节一致。⚠️ `0005`/`0006` 必须按 conan 依序应用后的实际内容
（post-0001..0004）生成，按 pristine 上下文生成会在 `apply_conandata_patches()` 抛
`Failed to apply patch`（本轮已实测踩中）。

## 数据/资源安装布局

- `lib/libcryptui.so.0.0.0`（soname `libcryptui.so.0`，`-version-info` 由 configure 定）
- `include/libcryptui/`（6 个公共头：`cryptui.h`、`cryptui-keyset.h`、`cryptui-key-store.h`、
  `cryptui-key-combo.h`、`cryptui-key-list.h`、`cryptui-key-chooser.h`）
- `lib/pkgconfig/cryptui-0.0.pc`（`Requires: gtk+-3.0 gio-2.0 dbus-glib-1`，
  `Cflags: -I${includedir}/libcryptui`）
- `share/glib-2.0/schemas/org.gnome.seahorse.recipients.gschema.xml`（+ best-effort
  `gschemas.compiled`；消费者需把该目录并入 `GSETTINGS_SCHEMA_DIR` 才能用
  `CryptUIKeyStore`）
- `share/GConf/gsettings/org.gnome.seahorse.recipients.convert`（上游 GConf 迁移描述）
- `.la` 归档文件已从包中移除（E236：其 `libdir` 指向 conan 缓存绝对路径，会污染下游链接）

消费者须知：`cryptui.h:27-29` 用 `#error` 强制定义 `LIBCRYPTUI_API_SUBJECT_TO_CHANGE`
（上游要求声明 API 稳定性认知）——本配方已通过 `cpp_info.defines` 自动提供给 CMakeDeps
消费者；纯 pkg-config 消费者需自行 `-DLIBCRYPTUI_API_SUBJECT_TO_CHANGE`。

## 知识库扩展立项评估结论（路径 B：**不立项**）

**结论：本次不立项知识库扩展**，仅提交库适配产物（配方/补丁/测试/元数据）+ 本笔记的坑位沉淀。

判据（用户口径：扩展须服务本库适配，且现成图谱撑不住时才做；单纯交扩展不算）：

| 本次坑位 | 现成图谱是否覆盖 | 条目 |
|---|---|---|
| 依赖包 `.la` 的 `libdir='//lib'` → `is not a valid libtool archive`（**真正解锁点**） | ✅ | **E236**（`scoped-la-free-static-archive-directory`） |
| `config.guess`/`config.sub` 不识别 HarmonyOS 内核 | ✅ | E007 / E160 |
| 未签名 ELF 直接 exec 被拒 | ✅ | E077 |
| `/tmp` 只读、HMDFS 目录权限 | ✅ | E002 / E011 |
| autotools 脚本可执行位（G0 预扫描命中，**非根因**） | ✅ | E490 |

→ 适配全程由既有条目支撑，未出现"图谱撑不住"的情形，故不满足立项条件。

**已识别的两类候选共性问题**（本次用单库补丁解决，判断未达立项门槛，仅在反馈报告与本节留档，**未建草稿**）：

1. `configure` 期 intltool/Perl 硬闸**多点分散**：`INTLTOOL_APPLIED_VERSION`、`perl >= 5.8.1`、
   `XML::Parser` 是三处独立 `as_fn_error`，降级一处后 configure 仍失败（本次 `0003` 覆盖前两处后
   仍需 `0005`）；规律是"改完必须重跑 configure 直到通过"。
2. `configure` 期 `GLIB_COMPILE_SCHEMAS` 取自 `$PKG_CONFIG --variable glib_compile_schemas gio-2.0`，
   conan 生成的 `gio-2.0.pc` 无该变量 → 空值硬失败；**与 PATH 无关**（前置依赖 `bin/` 无效，
   `--disable-schemas-compile` 只管 install 期钩子、不豁免 configure 期探测），须 `command -v` 回退（`0006`）。

若后续在**第二个库**上复现同类形态（同族跨库复现是立项判据的关键），可据此立项并补齐路径 B
全套产物（检测脚本 / 处理策略 / README / 样例库 / CI 干净复现）。两条候选的完整分析见
`feedback/SKILL_FEEDBACK_2abbe371.md` §知识图谱覆盖。
---

**编译结束**: 2026-10-01 16:33
**最终状态**: built
