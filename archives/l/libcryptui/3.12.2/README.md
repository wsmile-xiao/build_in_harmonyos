# libcryptui 3.12.2 — HarmonyOS PC 适配说明

## 1. 软件简介

[libcryptui](https://gitlab.gnome.org/Archive/libcryptui) 是 GNOME Seahorse（密码与密钥
管理器）拆出的**密钥选择/加密 UI 库**：向第三方应用提供"选择收件人/签名密钥"对话框
（`CryptUIKeyChooser`）、可嵌入的密钥列表与下拉控件（`CryptUIKeyList`/`CryptUIKeyCombo`），
以及基于 `GtkTreeModelSort` 的密钥模型（`CryptUIKeyStore`）。

- 上游版本：**3.12.2**（上游末次发布，2014 年后停更；无适配后缀，首次适配按 R37 直接用上游版本号）
- 上游源码：`https://download.gnome.org/sources/libcryptui/3.12/libcryptui-3.12.2.tar.xz`
- 源码 sha256：`71ead1a7b496f07f6c5102ae79945dd2515b7b9342c6edefe58b47318be20866`
- 开源许可：**LGPL-2.0-or-later**（`libcryptui/*.h`、`*.c` 共 14 个文件头声明
  "GNU Lesser General Public License ... version 2 ... or (at your option) any later
  version"；tarball 顶层 `COPYING` 为 GPL-2.0 文本，系上游打包遗留。制品内随包分发
  `licenses/COPYING`）
- 构建系统：**autotools**（`configure` 由 autoconf 2.69 生成）
- 上游现状：GNOME 3.x 时代的 GTK3 库，`cryptui-0.0.pc` 声明
  `Requires: gtk+-3.0 gio-2.0 dbus-glib-1`

## 2. 适配范围（打包口径）

- 取**官方源码包**构建（无 fork、无镜像改写；镜像 fallback 均为 GNOME 官方镜像）。
- `SUBDIRS` 裁剪为 **`libcryptui`（库本体）+ `data`（gsettings schema）**：
  - `daemon/`：Seahorse 的 D-Bus 守护进程，吃 `gnome-keyring-1` + `gpgme` + MIME 数据库；
  - `libegg/`：内嵌的 `eggsmclient`，吃 `libSM`/`libICE`（OHOS 均无此二者）；
  - `reference/`（gtk-doc）、`po/`（intltool）、`pixmaps/`：与库本体无关。
  以上四条支线是**重依赖面的唯一消费者**，裁掉后库本体只剩 gtk + dbus-glib。
- 产物为库文件，**不含命令行可执行文件** → 按 R38 不声明 `commands.json`。
- 补丁 **6 个**（见 §3）。
- 依赖：`gtk/3.24.43`、`dbus-glib/0.114.1`；expat 版本分叉由消费侧 `override=True`
  对齐到 `expat/2.8.2.1`（gtk 链已 pin 该版本，dbus 链请求 `2.8.2`，否则依赖图不可解）。

## 3. 构建要点

```bash
conan create archives/l/libcryptui/3.12.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

| 补丁 | 目标文件 | 作用 |
|---|---|---|
| `0001-config.guess.patch` | `config.guess` | 补 HarmonyOS/HongMeng 内核识别（musl libc） |
| `0002-config.sub.patch` | `config.sub` | 接受 `aarch64-unknown-linux-ohos` 三元组 |
| `0003-configure.patch` | `configure` | intltool 版本硬闸豁免、`ac_pwd` 回退、SM/ICE 硬依赖降级、`mktemp -d` 目录权限（HMDFS SGID） |
| `0004-subdirs.patch` | `Makefile.am`、`Makefile.in` | `SUBDIRS` 裁为 `libcryptui data` |
| `0005-configure-intltool-perl.patch` | `configure` | perl 存在性 / `perl >= 5.8.1` / `XML::Parser perl module is required` 三处 `as_fn_error` 降级为 `:`（`po/` 已裁，intltool 无消费者） |
| `0006-configure-glib-compile-schemas.patch` | `configure` | `glib-compile-schemas` 探测：非交叉分支取 `$PKG_CONFIG --variable glib_compile_schemas gio-2.0` 为空时回退 PATH 查找（conan 生成的 `gio-2.0.pc` 无该变量） |

补丁均以 `a/`、`b/` 前缀生成 → `conandata.yml` 中显式 `strip: 1`（conan patch 默认 strip=0）。
6 个补丁已在**纯净上游副本**上按序 `patch -p1` 全量演练（6/6 干净命中）。

构建期的两处平台适配不在补丁内，而在配方 `generate()/build()`：

- `_fix_dependency_la_metadata()`：依赖包 `.la` 的 `libdir='//lib'`（conan 以 `--prefix=/`
  构建所致）会让 libtool 链接 `libcryptui.la` 时报
  `grep: //lib/libpcre2-8.la: No such file` / `'//lib/libpcre2-8.la' is not a valid
  libtool archive`；构建前就地改写依赖 `.la` 的 `libdir`/`dependency_libs` 为真实路径
  （E236，libgsf 1.14.5 先例）。
- `_pin_generated_marshallers()`：tarball 自带 `cryptui-marshal.c/.h`（2014）比
  `cryptui-marshal.list`（2011）新 → 触摸产物即让 make 判定 Up-to-date，绕开 OHOS 上
  conan 包内未签名 `glib-genmarshal` 无法 exec 的问题。
- `package()` 内 `_sign_installed_elfs()`：产物经 OHOS `binary-sign-tool` 自签名，动态
  加载器方可加载。

## 4. 验证结果

| 项 | 结果 |
|---|---|
| 编译（`aarch64-linux-ohos` clang 15.0.4，OHOS SDK 26.0.0.18，CI 同款 profile） | **通过**（`conan create` EXIT=0，G0–G4 全 PASS） |
| 产物：`lib/libcryptui.so.0.0.0`（soname `libcryptui.so.0`） | 存在，797,056 B，**已签名**（含 `.codesign`） |
| 产物：`include/libcryptui/*.h` | 6 个公共头（`cryptui.h`、`cryptui-keyset.h`、`cryptui-key-store.h`、`cryptui-key-combo.h`、`cryptui-key-list.h`、`cryptui-key-chooser.h`） |
| 产物：`lib/pkgconfig/cryptui-0.0.pc` | 存在（`Requires: gtk+-3.0 gio-2.0 dbus-glib-1`） |
| 产物：`share/glib-2.0/schemas/org.gnome.seahorse.recipients.gschema.xml` | 存在（+ best-effort `gschemas.compiled`） |
| 上游测试（`libcryptui/tests/` 文件数 N=3 = `Makefile.am` + `Makefile.in` + `cryptui-test-ui.c`；可执行用例 1） | 可 headless 运行 **1/1**：`cryptui-test-ui.c` 以 keyset 模式（无 UI 对话框）经 `dbus-run-session` + `broadwayd`（`GDK_BACKEND=broadway`，`XDG_RUNTIME_DIR` 指向构建目录）真实执行，GTK/broadway/DBus 栈全链路初始化后 exit 0（证据：test_package `upstream-test.log`） |
| **鸿蒙消费者测试**（`test_package/test_libcryptui.c`，16 项 TAP 断言，真实链接 `libcryptui.so` 并调用库内逻辑） | **通过 16/16**（本机 `conan create` 实测 16 `ok` / 0 `not ok`）：ABI 常量 6 项 + `cryptui_key_get_base()` 5 种输入 + GObject 类型注册 3 项 + 模型列布局 2 项 |
| W4 Pre-PR 审计 | 见 `reports/`（PR 阶段执行，P0/P1 清零） |

## 5. 已知限制

1. **上游 UI 用例不可运行**：唯一用例依赖 GTK 显示，OHOS PC 无窗口系统；配方在
   `build()` 中对 `make check` 做非致命尝试（日志留痕），绝不把未执行计为通过。
2. **`CryptUIKeyStore` 的 settings 后端需消费者配合**：需把 `share/glib-2.0/schemas`
   并入 `GSETTINGS_SCHEMA_DIR`（或系统 schema 目录）后 `g_settings_new` 才能成功。
3. **`cryptui_prompt_*` 系列依赖 GTK 对话框 + DBus 会话总线**，无窗口/无会话总线的
   环境不可用（平台限制，非配方缺陷）。
4. **`dbus-glib` 在本图谱解析为静态归档**（包内仅 `libdbus-glib-1.a`；实测产物
   `libcryptui.so` 的 `NEEDED` 无 `libdbus-glib-1.so.2`），符号静态并入被测库，
   运行期不额外依赖该 `.so`。
5. 产物未 strip，调试字符串内含构建目录绝对路径。
6. 包内**不含 `.la` 归档**（E236：其 `libdir` 指向 conan 缓存绝对路径，会污染下游链接）。

## 6. 目录说明

```
3.12.2/
├── conanfile.py            # Conan 配方（CI 输入）
├── conandata.yml           # 源码地址 + 镜像 fallback + sha256 + 6 个补丁声明（CI 输入）
├── patches/                # 6 个补丁（CI 输入）
├── test_package/           # Conan L1 消费者测试（CI 输入，16 项 TAP 断言）
├── manifest.yaml           # 编译元数据
├── notes.md                # 适配笔记（10 项坑位 + 补丁 + 测试口径）
└── reports/                # W3 本地 CI 日志、conan-verify 报告、W4 审计结果、PR 正文
```
