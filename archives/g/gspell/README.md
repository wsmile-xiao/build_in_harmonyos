# gspell

`gspell` 是 GTK 3 应用的拼写检查控件库：它把 Enchant 的词典/语言抽象
（`GspellChecker`、`GspellLanguage`）包装成 GTK 风格的对象，并把拼写检查
直接挂到 `GtkEntry` / `GtkTextBuffer` / `GtkTextView` 上做内联标记与右键
建议。应用只需要 attach 一次，剩下的高亮、上下文菜单、语言选择对话框都由
库负责。

## 功能概述

- **`GspellChecker`**：对词做检查（`gspell_checker_check_word`）与取建议
  （`gspell_checker_get_suggestions`），底层通过 Enchant broker 访问词典。
- **`GspellLanguage`**：语言枚举与查找（`gspell_language_get_available` /
  `gspell_language_lookup`），语言名与显示名由 ICU 数据本地化。
- **内联拼写检查**：`GspellTextBuffer` / `GspellTextView` / `GspellEntry`
  三个 attach 型包装，把检查器绑定到 GTK 控件上并驱动
  `GspellInlineCheckerTextBuffer` 打错误标记。
- **`GspellNavigatorTextView`**：在错误之间前后跳转。
- **`GspellLanguageChooser`**：语言选择控件。

交付边界是**纯库**：`libgspell-1.so.3` + `include/gspell-1/gspell/*.h` +
`gspell-1.pc`。上游另有一个演示程序 `gspell-app`（`-Dgspell_app=true`），
本包按库的定位关掉它，`bin/` 为空。

## OHOS 适配

| 要点 | 说明 |
|------|------|
| 只交付库 | `-Dgspell_app=false`，避免 `library` 类型的包里混进可执行程序 |
| 公共依赖链 | 安装出去的 `gspell-1.pc` 的 `Requires:` 只有 `gio-2.0 gtk+-3.0 enchant-2`（上游 `PKG_CONFIG.generate(libraries: GSPELL_PUBLIC_DEPS)`），消费方无需直接依赖 icu4c |
| ICU 版本必须钉 `icu4c/77` | `icu4c/78` 的 recipe 既无 `fPIC` 选项、也未 `set_property("pkg_config_name","icu-uc")`，PkgConfigDeps 只生成 `icu4c.pc`，上游 `dependency('icu-uc')` 直接配置失败；77 才是可用的那个 |
| 静态 ICU 需要 `-lc++` | `icu4c/77` 默认 `shared=False`，是静态 C++ 归档；gspell 是纯 C 工程，链入后带进 `__gxx_personality_v0` / `__cxa_begin_catch`，所有 C 链接都要补 `-lc++` |
| Conan glib 的 `.pc` 缺 `-lintl` | `libglib-2.0.so` 依赖 `g_libintl_*`，但 Conan 生成的 `glib-2.0.pc` 的 `Libs:` 里没有 `-lintl` → `generate()` 补上（同 gtk/3.24.43、vte/0.74.2） |
| meson 的 gnome 模块要工具变量 | `GNOME.mkenums_simple` 要 `glib_mkenums`（在 `glib-2.0.pc`）、`GNOME.compile_resources` 要 `glib_compile_resources`（在 `gio-2.0.pc`），PkgConfigDeps 都不生成 → `generate()` 注入；同时把 glib 包 `bin/` 下的构建期工具做 OHOS ELF 签名 |
| headless 测试 | 上游 unit-tests 的 6 个二进制都经 `gtk_test_init()` 取显示后端；ohpcd 无 X/Wayland，gtk 是 broadway-only，构建期起 `<gtk>/bin/broadwayd :5` + `GDK_BACKEND=broadway` 即可跑 |
| 词典能力取决于 enchant | ohpcd 的 `enchant/2.8.2` 编译时关掉了全部 provider（`--without-aspell/hspell/hunspell/nuspell/voikko/zemberek`），包内无 `lib/enchant-2/*.so`、无词典 → 上游 23 个用例里有 15 个会在 `g_assert_true(lang != NULL)` 处 abort，构建期按 provider 个数判定并显式标注跳过 |

**已知行为差异**：无词典时 `gspell_language_lookup("en_US")` 返回 `NULL`，
`gspell_checker_check_word()` 回落到返回 `TRUE`（放行），
`gspell_checker_get_suggestions()` 返回 `NULL`。这是上游的降级语义，不是
OHOS 特有缺陷；本包的消费者测试专门断言了这组语义。

**为什么不影响下游**：GUI 程序 attach 拼写检查后仍能正常运行，只是没有
红波浪线。要真正查词需要重新发布一个带 provider 的 enchant（如
`--with-hunspell`）并另装词典数据（见 `archives/h/hunspell-en`）。

## 依赖关系

编译期 / 运行期（安装后由 `gspell-1.pc` 表达）：

- **gtk+ 3.0**（`>= 3.20`）：控件集成与内联检查器；本仓库 `gtk/3.24.43` 同时提供 headless 测试用的 `bin/broadwayd`
- **gio-2.0**（`>= 2.44`）：GTK/GObject 运行时
- **enchant-2**（`>= 2.2`）：拼写检查后端抽象与词典 broker

私有依赖（仅编译期，静态链入 `libgspell-1.so.3`）：

- **icu-uc**：语言代码 ↔ 语言显示名的本地化（`_gspell_icu_*`）

## 为什么值得收进知识库

在 gspell 归档之前，ohpcd 上有三个 GUI 程序因为**找不到 gspell** 而把整个
拼写检查功能砍掉了：

| 下游包 | 当时的选择 |
|--------|-----------|
| evince 48.4 | `-Dgspell=disabled` |
| pan 0.165 | `WANT_GSPELL=OFF`（上游默认 ON） |
| yad | html / spell / sourceview 一律关闭 |

补上这一个库，这三处的功能缺口就同时具备恢复条件。除了下游价值，本包还
沉淀了两类可复用知识：

1. **「依赖包的 `.pc` 名 ≠ Conan 包名」导致的上游依赖解析失败**——`icu4c`
   必须选 77 而不是 78，差别只在 recipe 有没有 `set_property("pkg_config_name","icu-uc")`。
   这类问题在 meson 工程里报的是 `Dependency "icu-uc" not found`，很容易
   被误判为网络/远程问题。
2. **上游测试集的执行边界应由依赖图在构建期推导，而不是硬编码**——
   `_enchant_provider_count()` 数 `lib/enchant-2/*.so`；为 0 时只跑 8 个
   环境无关用例，并把 provider 计数与跳过原因写进
   `HMBS_UPSTREAM_TEST_RESULT`。enchant 侧补齐 provider 后，同一份配方
   自动把剩下 15 个用例纳入执行，不需要改配方。

## 参考资料

- 上游仓库：<https://gitlab.gnome.org/GNOME/gspell>
- 镜像：<https://github.com/GNOME/gspell>
- 源码包：`https://github.com/GNOME/gspell/archive/refs/tags/1.14.4.tar.gz`
- API 文档：<https://gnome.pages.gitlab.gnome.org/gspell/>
- 底层拼写后端：Enchant（<https://rrthomas.github.io/enchant/>）
- 同仓库同族包：`archives/e/enchant`、`archives/h/hunspell-en`、`archives/g/gtkspell3`
