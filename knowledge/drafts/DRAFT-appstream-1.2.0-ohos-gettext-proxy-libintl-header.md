# DRAFT-appstream-1.2.0-ohos-gettext-proxy-libintl-header — OHOS sysroot libintl.h 空 stub 编译期补位

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: compilation / gettext / libintl / glib / ohos / portability
> **Audience**: 所有依赖 glib 家族且源码直接调用 gettext()/dgettext() 的 C 库 OHOS 适配者

## 触发（trigger）

- appstream 1.2.0 OHOS 适配：`src/as-category.c` 第 809 行直接调用 `gettext()`；
  `as-utils-private.h` 链上 gi18n-lib.h 无条件 `#include <libintl.h>`。

## 症状（symptom）

```
../src/as-category.c:809:35: error: call to undeclared function 'gettext';
ISO C99 and later do not support implicit function declarations [-Werror,-Wimplicit-function-declaration]
../src/as-category.c:809:35: error: incompatible integer to pointer conversion ...
```

上游开 `-Werror=implicit-function-declaration`，空 stub 头使 gettext 未声明 → 直接失败。

## 机制（root cause）

- OHOS sysroot 的 `libintl.h` 是空 stub（无 gettext/dgettext/textdomain 声明）；
- glib 头 `gi18n-lib.h` 无条件 include `<libintl.h>` 并按 `GETTEXT_PACKAGE` 使用
  gettext（`_(String)` → `g_dgettext(GETTEXT_PACKAGE, ...)`）；
- 源码若直接调用裸 `gettext()` 而非宏，需要 libintl.h 提供声明；
- glib 包内自带 proxy libintl.h：`#define gettext g_libintl_gettext` 等，把符号
  映射到 proxy-libintl（链接期提供 g_libintl_*）。

## 修复（rec）

复制 glib 包内 proxy libintl.h 到构建私有 include 目录，并前置到
MesonToolchain `extra_cflags -I` 最前（在 sysroot 空 stub 之前）：

```python
proxy_intl_dir = os.path.join(self.build_folder, "proxy-libintl-include")
os.makedirs(proxy_intl_dir, exist_ok=True)
shutil.copyfile(proxy_intl_src, os.path.join(proxy_intl_dir, "libintl.h"))
tc.extra_cflags.append(f"-I{proxy_intl_dir}")
```

（本机部分 glib 包未随包安装 libintl.h，从同 glib 版本其他包的缓存副本复制即可。
at-spi2-core 配方在 .pc 侧暴露 `${prefix}/include` 是同款手法的另一落点。）

## 验证（verification）

as-category.c 等编译通过，主库全量链接成功；未改上游源码、未改 sysroot。

## 适用边界 / 反例

- 适用：源码直接调用裸 gettext()/dgettext() 且 sysroot libintl.h 无声明；
- 反例：库只经 `_(String)` 宏使用（gi18n-lib.h 内部已处理）不触发；
- 反例：系统提供完整 libintl.h 声明的平台不适用。

## 关系

- `similar_to`: E015（libintl.h 检测后缺 gettext 链接依赖）、E027（NLS 关闭）、
  E107（glib 静态 g_libintl 链接）、E142（gnulib gettext 重命名链接）
- 差异：既有条目覆盖**链接期**符号/配置；本候选是**编译期声明缺失**的补位，
  且方案在构建私有目录内自包含。

## 证据

- 配方：`archives/a/appstream/1.2.0/conanfile.py`（generate() proxy-libintl-include 段）
- 台账：`archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md` 候选 4