# gspell 1.14.4 适配笔记

## 编译环境
- 构建系统: meson（上游 meson.build，meson_version >= 0.64）
- 编译日期: 2026-09-21
- 编译器: clang（来自 conan profile `tools.build:compiler_executables.c`，设备上为 Harmonybrew OHOS SDK clang）
- 目标平台: HarmonyOS PC / aarch64-linux-ohos（armv8）
- 状态: built

## 本包要解决什么

gspell 把 Enchant 的拼写检查能力包装成 GTK 控件：`GspellChecker`（词/建议）、
`GspellLanguage`（可用语言列表）、以及 `GtkEntry` / `GtkTextBuffer` / `GtkTextView`
三个内联拼写检查集成。它在 ohpcd 上**一直没有包**，于是三个已归档的 GUI 程序只能
把功能砍掉：

| 下游包 | 现状 | 出处 |
|--------|------|------|
| evince/48.4 | `-Dgspell=disabled` | `archives/e/evince/48.4/manifest.yaml` |
| pan/0.165 | `WANT_GSPELL=OFF`（上游默认 ON） | `archives/p/pan/0.165/notes.md` |
| yad | html/spell/sourceview 一律关闭 | `archives/y/yad/README.md` |

本包补上这块：交付 `libgspell-1.so.3` + `include/gspell-1/gspell/*.h` + `gspell-1.pc`。

## 上游审计（先于动手）

| 项 | 结论 | 证据 |
|----|------|------|
| 构建系统 | meson ≥ 0.64，`subdir('po'/'gspell'/'tests'/'gspell-app'/'docs')` | `meson.build:8`、`meson.build:132-150` |
| 交付边界 | 只需库：`gspell_app=false` 即可不构建 `gspell-app` | `meson_options.txt`、`gspell-app/meson.build` |
| 公共依赖 | `gio-2.0>=2.44`、`gtk+-3.0>=3.20`、`enchant-2>=2.2` | `meson.build:20-24` |
| 私有依赖 | `icu-uc`（无版本约束） | `meson.build:25-27` |
| 库/SONAME | `library('gspell-1', soversion: 3)` → `libgspell-1.so.3` | `gspell/meson.build:105-114` |
| 头文件 | `install_headers(..., includedir/gspell-1/gspell/)` → `#include <gspell/gspell.h>` | `gspell/meson.build:69-77` |
| .pc 名 | `gspell-1`，`Requires:` 只有三个公共依赖 | `gspell/meson.build:122-128` |
| 上游测试 | `tests/unit-tests/meson.build` 6 个二进制 / 23 个 `g_test_add_func`；`tests/interactive-tests` 只 `executable()`、**没有 `test()`**，不是上游测试目标 | `tests/unit-tests/meson.build`、`tests/interactive-tests/meson.build` |
| 测试驱动 | 6 个二进制全部 `gtk_test_init()` → 需要显示后端 | 各 `test-*.c` 的 `main()` |

## 编译步骤

```bash
# build() 内（R9）：configure + ninja + 上游测试
meson setup _build -Dgspell_app=false -Dgobject_introspection=false \
                   -Dvapi=false -Dgtk_doc=false \
                   -Dtests=true -Dinstall_tests=false -Dwrap_mode=nodownload
ninja -C _build
# 上游测试：broadwayd :5 起 headless 后端后逐个二进制 --tap 运行
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `dependency('icu-uc')` 解析不到 | `icu4c/78` 的 recipe 既无 `fPIC` 选项、也未 `set_property("pkg_config_name","icu-uc")`，PkgConfigDeps 只会生成 `icu4c.pc` | 钉 `icu4c/77`（`pkg_config_name = "icu-uc"`、`fPIC=True`、`shared=False`）；`archives/i/icu4c/77/conanfile.py:138` |
| 2 | 共享库链接期 `undefined symbol: __gxx_personality_v0` / `__cxa_begin_catch` | icu4c/77 是**静态** C++ 归档，被纯 C 工程链入 | `MesonToolchain.c_link_args += ["-lc++"]`（同 cif-api/0.4.2） |
| 3 | 链接期 `undefined symbol: g_libintl_bindtextdomain` | `libglib-2.0.so` 依赖 libintl，而 Conan 的 `glib-2.0.pc` 的 `Libs:` 没有 `-lintl` | `generate()` 里往 `glib-2.0.pc` 的 Libs 行追加 `-lintl`（同 gtk/3.24.43:283、vte/0.74.2） |
| 4 | meson 配置报 `Could not get pkg-config variable` | `GNOME.mkenums_simple` 要 `glib_mkenums`（glib-2.0.pc），`GNOME.compile_resources` 要 `glib_compile_resources`（gio-2.0.pc），PkgConfigDeps 都不生成 | `generate()` 注入这些工具变量；`_inject_meson_archiver()` 同时把 `ar/ranlib` 与 glib 工具绝对路径写进 `conan_meson_native.ini [binaries]`，绕开 `/data/service/hnp/bin` 的坏软链 |
| 5 | glib 包 `bin/` 下的构建期工具在 OHOS 上 `Operation not permitted` | OHOS 要求 ELF 带有效 `.codesign` 段才允许 exec | `build()` 起始 `_sign_glib_tools()`：`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` → `chmod a+x`（E077 四步） |
| 6 | 上游测试二进制起不来（`test-icu` rc=-5，日志只有一行 `Gtk-WARNING: cannot open display:`） | 两个原因叠在一起：(a) 6 个二进制都调 `gtk_test_init()`，需要 GDK 后端，而 OHOS 侧无 X/Wayland；(b) `_broadway_env()` 把 `LD_LIBRARY_PATH` 只写进本地 `env` dict，`Popen` 时**漏了 `env=env`**，broadwayd 于是继承 CI 进程的环境，加载器找不到 `libgtk-3.so.0`/`libgio` 直接退 127（日志即 `broadwayd exited early (rc=127)`），配方退回「无 display」分支，用例随即崩溃 | 用 gtk 包自带的 `bin/broadwayd :5` + `GDK_BACKEND=broadway` + `BROADWAY_DISPLAY=:5`（同 ayatana-ido/0.10.4-v2），并把 `env=env` 显式传给 `Popen`；stderr/stdout 落 `broadwayd.log`，失败时回读尾部 800 字节写进 warning，避免再出现「只看到 rc 猜不出原因」 |
| 7 | 15/23 个上游用例执行即 abort | `enchant/2.8.2`（ohpcd）编译时传入 `--without-aspell --without-hspell --without-hunspell --without-nuspell --without-voikko --without-zemberek`，包内无 `lib/enchant-2/*.so` 提供者、无词典 → `gspell_language_lookup("en_US")` 恒 NULL，用例在 `g_assert_true(lang != NULL)` 处 abort | **不改上游测试**。`_enchant_provider_count()` 在构建期数 `lib/enchant-2/*.so`：为 0 时只跑 `test-icu`/`test-text-iter`/`test-utils`（8 个用例），跳过的 3 个二进制与 provider 计数一起写进 `HMBS_UPSTREAM_TEST_RESULT`；enchant 侧补齐提供者后同一份配方自动纳入 |
| 8 | 自动 strip 会破坏 HarmonyOS ELF 签名 | `llvm-strip` 改写 ELF 使签名失效 | 与 gnucobol/gtk 一致，OHOS 下 `environment().define("STRIP", ":")`；`package()` 末 `_sign_binaries()` 对交付的 `.so*` 补签 |
| 9 | 上游通过率看起来只有 34.8%（8/23） | 分母是上游全集，分子是**本平台可执行集** | 构建期按依赖图判定并如实标注跳过（技术原因见 #7），不虚报分母、也不虚报分子 |

## 源码修改

无。上表各项处理全部在配方层（构建期补 .pc / 注入工具变量 / 起 broadwayd / 依依赖图决定测试集），未改动上游任何文件，`patches_applied: []`。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| gtk | 3.24.43 | 公共依赖（`gtk+-3.0 >= 3.20`）；同时提供 headless 测试用的 `bin/broadwayd` |
| glib | 2.84.0.1 | 公共依赖（`gio-2.0 >= 2.44`）；提供 `glib-mkenums` / `glib-compile-resources` 等构建期工具 |
| enchant | 2.8.2 | 公共依赖（`enchant-2 >= 2.2`），拼写检查后端抽象 |
| icu4c | 77 | 私有依赖（`icu-uc`），语言名/显示名的本地化；静态链入 libgspell-1.so.3 |

以上均为 ohpcd 已发布的 OHOS armv8 binary（`conan list ... -r ohpcd` 核实）。

## 验证结果

```text
# 上游测试（tests/unit-tests，6 二进制 / 23 用例）
执行集：test-icu(2) + test-text-iter(3) + test-utils(3) = 8 用例，8/8 通过
未执行：test-checker(3) + test-entry(7) + test-inline-checker-text-buffer(5) = 15 用例
        原因：enchant/2.8.2 无任何 provider/词典（构建期实测 lib/enchant-2/*.so 个数 = 0），
              三个二进制在 g_assert_true(lang != NULL) 处 abort，属无词典环境的确定结果
标记：HMBS_UPSTREAM_TEST_RESULT 记录 discovered=23 executed=8 passed=8 skipped=15 enchant_providers=0

# test_package（pkg-config gspell-1 链接安装后的共享库，broadwayd 下真实运行）
1..13
ok 1  - gspell_checker_error_quark() is available from libgspell-1
ok 2  - gspell_language_get_available() yields describable GspellLanguage items (or an empty list)
ok 3  - with no Enchant provider installed, gspell_language_lookup("en_US") returns NULL
ok 4  - gspell_checker_new(NULL) builds a GspellChecker
ok 5  - gspell_checker_check_word() falls back to TRUE without raising an error when no dictionary is active
ok 6  - gspell_checker_get_suggestions() returns NULL when no dictionary is active
ok 7  - gspell_text_buffer_get_from_gtk_text_buffer() attaches a GspellTextBuffer to a GtkTextBuffer
ok 8  - gspell_text_buffer_get_buffer() round-trips to the same GtkTextBuffer
ok 9  - gspell_text_view_get_from_gtk_text_view() attaches a GspellTextView to a GtkTextView
ok 10 - gspell_text_view_get_view() round-trips to the same GtkTextView
ok 11 - gspell_navigator_text_view_new() builds a navigator for a GtkTextView
ok 12 - gspell_entry_get_from_gtk_entry() attaches a GspellEntry to a GtkEntry
ok 13 - the inline-spell-checking flag round-trips through GspellEntry
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libgspell-1.so.3(.x.y) | 运行时库本体（arm64 ELF 共享库，SONAME `libgspell-1.so.3`） |
| lib/libgspell-1.so | 链接期名字（`-lgspell-1`） |
| include/gspell-1/gspell/*.h | 公开 C API 头（含 `gspell.h` 伞头与 enum-types 生成头） |
| lib/pkgconfig/gspell-1.pc | pkg-config：`Requires: gio-2.0 gtk+-3.0 enchant-2` |

## 注意事项

- 包内**不含**可执行程序（`gspell_app=false`），`bin/` 为空，`package_type = "library"` 与内容一致。
- 词典能力取决于 **enchant 包**。ohpcd 的 `enchant/2.8.2` 无任何 provider，因此本包在当前平台上只能做"结构性"拼写检查（控件绑定、语言枚举、无词典降级语义）；要真正查词需重新发布一个带 provider（如 `--with-hunspell`）的 enchant，并另行安装词典数据（参考 `archives/h/hunspell-en`）。
- 本包只依赖 `gtk/3.24.43` 这一条 gtk 线；若与其它 gtk 版本共存需注意依赖图不要出现两份 glib/gtk。
- 本包无命令行产物，因此没有软件级 `commands.json`（R38 只针对可执行命令）。
