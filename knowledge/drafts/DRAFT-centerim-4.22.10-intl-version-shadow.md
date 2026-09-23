# Draft — gettext `intl/version` shadows libc++ `<version>` (+ 老 C++ 四连坑)

> DRAFT centerim 4.22.10 adaptation knowledge entry.
> Promote to `knowledge/graph/E0XX` + `knowledge/doc/E0XX.md` after review.

## 现象（conan create 失败链）

```
intl/version:1:1: error: unknown type name 'GNU'
no type named 'size_t' in namespace 'std'        (libc++ <new>/<cstddef> 级联)
cannot combine with previous 'bool' declaration specifier   (bool auto 参数)
no member named 'gettext' in the global namespace           (<libintl.h> 未命中)
undefined symbol: rindex                                      (链接期)
git-version.h.in: No such file or directory                   (git_version 规则)
```

## 根因

1. `AM_GNU_GETTEXT`（捆绑 intl）往 CPPFLAGS 加 `-I<srcdir>/intl`；该目录里有 gettext
   的 VERSION 标记文件 `intl/version`（内容 `GNU gettext library from gettext-0.14.6`）。
   clang 对 `<>` include 先查 -I 目录，故 libc++ 头内部的 `#include <version>` 命中
   `intl/version`，把 "GNU gettext..." 当代码解析 → std 命名空间被污染，级联出一串
   `no type named 'size_t'/'align_val_t'`。
2. 2009 老 C++ 把 `auto` 当参数名（`bool auto = false`），C++11 起 auto 为关键字。
3. 老代码用 POSIX 废弃 `rindex()`，OHOS libc 无此符号。
4. `git_version` 规则用裸 `git-version.h.in`，out-of-tree 构建下在构建目录找不到；
   且 conan 源码非 git 仓库，`git-version-gen` 失败。
5. 捆绑 gettext 的 `libintl.h` 由构建过程生成在 **BUILD** 目录，源码目录没有；
   include 路径只含源码 `intl/` 时 `<libintl.h>` 命中别处 → `gettext` 未声明。

## 修复（centerim 配方落点）

- `0003-intl-version-comment.patch`：把 `intl/version` 内容改为 C++ 注释（合法空头文件）。
- `-std=gnu++11 -fpermissive` + `0004-icqface-auto-param.patch`（`bool auto` → `auto_`）。
- `0006-libgadu-rindex-strrchr.patch`：`rindex()` → `strrchr()`。
- `0005-src-makefile-git-version-srcdir.patch`：git_version 规则用 `$(srcdir)`。
- `generate()` 追加 `-I<build>/intl`，让 `<libintl.h>` 命中生成的捆绑头并声明 `::gettext()`。

## 验证

`conan create . -pr:h=.../ohos-aarch64 -pr:b=.../ohos-aarch64` 完整通过；
test_package `centerim --version` / `--help` 冒烟 PASS。

## 可复用性

适用于"autotools + 捆绑 gettext (AM_GNU_GETTEXT) 的 C/C++ 老项目"在 libc++/clang
工具链上的 OHOS 适配；只要 `-I<srcdir>/intl` 内含 `version` 标记文件就会踩中。
"老 C++ 在 C++11+ 下的 auto/rindex" 覆盖所有 2009 前代码库。
