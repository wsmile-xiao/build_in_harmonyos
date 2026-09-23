# DRAFT-nls-off-incomplete-i18n-stub-undefined-shlib-symbol — 非 NLS 分支 i18n 回退宏集不全，共享库残留未定义符号

## 现象 (What happened)

对 libexif-gtk 0.5.0（GTK3 变体）做 OHOS PC 原生构建时：

1. `configure` / `make -j1` 的**库本体编译全部通过**，`libexif-gtk3.so.5.1.0` 正常产出；
2. 继续构建**上游唯一示例程序** `tests/test-libexif-gtk` 时链接失败：

```
ld.lld: error: undefined reference due to --no-allow-shlib-undefined: bind_textdomain_codeset
>>> referenced by ../libexif-gtk/.libs/libexif-gtk3.so
clang-15: error: linker command failed with exit code 1
make[2]: *** [Makefile:402: test-libexif-gtk] Error 1
```

3. 直接检查共享库符号表，确认未定义符号来自库本体：

```
$ llvm-nm -D --undefined-only libexif-gtk/.libs/libexif-gtk3.so.5.1.0 | grep -i textdomain
                 U bind_textdomain_codeset
```

4. `configure` 当时已判定 `checking whether to use NLS... no`（OHOS 无 libc libintl：
   `GNU gettext in libc… no` / `in libintl… no`）。

## 根因 (Root cause)

上游每个源文件都带同一段 i18n 宏回退块，其**非 NLS 分支的宏集与调用点全集不一致**：

```c
#ifdef ENABLE_NLS
#  include <libintl.h>
#  define _(String) dgettext (GETTEXT_PACKAGE, String)
#else
#  define textdomain(String) (String)
#  define gettext(String) (String)
#  define dgettext(Domain,Message) (Message)
#  define dcgettext(Domain,Message,Type) (Message)
#  define bindtextdomain(Domain,Directory) (Domain)
/* ← 缺 bind_textdomain_codeset */
#endif
...
	bindtextdomain (GETTEXT_PACKAGE, LOCALEDIR);          /* 被宏吃掉 → no-op */
	bind_textdomain_codeset (GETTEXT_PACKAGE, "UTF-8");   /* 无宏 → 真实函数调用 */
```

三方条件共同构成“潜伏缺陷”：

| 条件 | 作用 |
|---|---|
| 调用点写在 `#ifdef ENABLE_NLS` **之外** | NLS 关闭时调用仍在编译 |
| 非 NLS 分支**漏** `bind_textdomain_codeset` | 该调用不被 no-op 宏吃掉 |
| 平台**无 libc libintl**（OHOS/musl），且库用 `-shared` 链接 | 声明来自系统头但**无实现**，`-shared` 允许未定义符号 → 潜伏进 UND 符号表 |
| 消费者是 C 可执行文件 + lld | 默认 `--no-allow-shlib-undefined` → 在**消费者链接阶段**报错 |

> **隐蔽点**：失败不在库的构建阶段，而在消费者（上游示例 / test_package / 下游应用）链接阶段；
> 只检查 `make` 成功会漏判。同类第二条路径：若 NLS 打开，glib 的 proxy-libintl 头会把
> `bindtextdomain` 等重定向到 `g_libintl_*`（实现在 glib 包自带 `libintl.so`），而上游
> `Makefile.am` 的 `LIBADD` 并未包含 `$(INTLLIBS)` → `.so` 同样留下 UND 符号。

## 解法 (Fix)

**首选**：补齐非 NLS 分支的桩宏（与既有 5 个风格一致），并**显式** `--disable-nls`。

```python
# 遍历所有带该宏块的源文件，各补一行（libexif-gtk 实测 14 个文件；其中 12 个实际调用）
anchor = "#  define bindtextdomain(Domain,Directory) (Domain)\n"
add    = "#  define bind_textdomain_codeset(Domain,Codeset) (Domain)\n"
```

配方侧：`AutotoolsToolchain.configure_args += ["--disable-nls"]`（确定性 + 不走 proxy-libintl 分支）。

> 桩展开为表达式会触发 clang `expression result unused` 警告——与上游既有 `bindtextdomain`
> 桩完全相同，属上游风格，不影响构建（libexif-gtk 实测 3 条此类警告，非错误）。

**备选**：保留 NLS 开启，把 `$(INTLLIBS)` 补进 `lib_LTLIBRARIES` 的 `LIBADD`，
让 glib 的 proxy-libintl 解析 `g_libintl_*`。代价是改上游链接行 + 引入 libintl 运行期依赖。

**禁止**：用 `#ifdef __OHOS__` 包住调用点（R8 禁止补丁平台宏；该缺陷与平台无关，
换平台同样复现），或对 `.so` 事后改符号表（OHOS 加载器拒绝被改写过的 ELF）。

## 验证 (Verification)

```
# 修复前
$ llvm-nm -D --undefined-only libexif-gtk/.libs/libexif-gtk3.so.5.1.0 | grep -i textdomain
                 U bind_textdomain_codeset
# 修复后
$ make -j1                      # exit 0（含示例程序链接）
$ llvm-nm -D --undefined-only … | grep -i textdomain      # 无输出
$ ./tests/test-libexif-gtk       # 可运行（进入上游自己的参数校验/主循环）
$ conan create …                 # test_package dlopen(RTLD_NOW) 断言通过
```

libexif-gtk 0.5.0 实测：`make` exit 0；UND 符号归零；`conan create` 的 test_package
第 3 条断言 `dlopen(libexif-gtk3.so.5, RTLD_NOW) resolves every symbol` PASS。

## 适用边界 (Applicability / Scope)

- 适用：源码自带 i18n 宏块（`#ifdef ENABLE_NLS … #else … #endif`）、且调用点未被 guard 包住的
  autotools 包；在 OHOS/musl 等无 libc libintl 平台上以 NLS 关闭构建；消费者链接使用 lld 默认设置。
- 不适用：调用点已被 `#ifdef ENABLE_NLS` 包住的代码（NLS 关闭时根本不编译，无 UND 符号）。
- 边界：**只看库自身 `make` 成功不足以下结论**——必须让消费者（示例程序/test_package）真实链接一次。

## 与既有条目查重差异 (Dedup / Delta vs Existing Entries)

| 既有条目 | 差异 |
|---|---|
| `DRAFT-13410-trueprint-libintl-stub-header` | 该条是 **sysroot 的 libintl.h 不含函数声明** → 隐式声明/gettext undefined（编译期，头文件侧） |
| `DRAFT-desktop-file-utils-0.28-libintl-header-prototype-inject` | 该条向 generators 注入最小 libintl.h 原型（补声明） |
| `DRAFT-glib-2.84.0.1-gettext-libintl-ld-library-path-shadow` | 该条是运行期 LD_LIBRARY_PATH 遮蔽 vendored proxy-libintl（环境陷阱） |
| `DRAFT-latino-1.4.4-musl-empty-libintl-bison-dgettext` | 该条是 musl `libintl.h` 空壳 + bison 生成代码在 `#ifdef __linux` 下映射 dgettext（编译期） |
| **本条** | 声明/头文件都正常，问题是**上游自己的非 NLS 宏集漏一个函数**，缺陷形态是**共享库 UND 符号**，失败暴露在**消费者链接阶段**（lld `--no-allow-shlib-undefined`）；解法是补桩 + 显式 `--disable-nls`，与上述四条互不覆盖 |

## 参考 (References)

- 上游代码：`libexif-gtk-0.5.0/libexif-gtk/gtk-exif-*.c`（14 个文件同款宏块）
- 本 PR 实证：`archives/l/libexif-gtk/0.5.0/patches/000{4..17}-*.patch`
  （`patch_description: i18n non-NLS fallback: add missing bind_textdomain_codeset no-op`）
- 同族条目：`E007`（平台三元组）、`E136`/`E114`（HMDFS 临时目录权限）
