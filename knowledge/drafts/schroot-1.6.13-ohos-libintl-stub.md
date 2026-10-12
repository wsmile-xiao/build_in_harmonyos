# OHOS 的 `<libintl.h>` 是空壳、无 libintl：直接调用者须显式包含并链接 gettext 包

- **草稿 ID**: DRAFT-SCHROOT-1613-OHOS-LIBINTL-STUB
- **条目文件**: `knowledge/drafts/schroot-1.6.13-ohos-libintl-stub.kv`
- **来源事件**: schroot 1.6.13 make 阶段（2026-10-01）
- **严重程度**: 🔴 blocking

## 1. 现象

编译期/链接期两类报错，取决于源文件是否包含了头：

```
sbuild-auth-pam.cc:…: error: 'dgettext' was not declared in this scope
schroot-base-run.h:…: error: 'bindtextdomain' was not declared in this scope
auth-pam.cc: undefined reference to `dgettext'
```

## 2. 根因

glibc 把 gettext 的 `libintl` 并进了 `libc`——所以 GNU 平台下"用了 `dgettext()` 却没
`#include <libintl.h>`"这种历史写法也能编过（隐式声明 + libc 里有符号）。

OHOS 基于 musl，其 sysroot 里：

- `<libintl.h>` 是**空壳**（无实际声明）；
- **不提供 libintl**（没有 `libintl.so`，`libc` 里也没有这些符号）。

于是同一份源码在 OHOS 上有两层问题：

| 层面 | 表现 |
|------|------|
| 编译 | 未包含 `<libintl.h>` 的调用点 → `was not declared in this scope` |
| 链接 | 符号无定义 → `undefined reference to 'dgettext'` |

本仓制品仓的 **gettext 包**提供真实 `libintl.h` + `libintl.so`，是正确依赖来源。

## 3. 解决方案

1. **补 include**：给直接调用 gettext 家族的源文件补 `#include <libintl.h>`。
   优先补在**项目自带的 i18n 封装头**里（schroot 为 `sbuild/sbuild-i18n.h`）——
   一次覆盖全部使用者；传递式依赖（头里调用、源文件不含）也要顺藤补齐
   （schroot 另有 `schroot-base-run.h`、`sbuild-auth-pam.cc` 两处）。
2. **配方加依赖并链接**：`self.requires("gettext/0.22.5.1")`，并把
   `-L<gettext libdir>` 与 `-lintl` 注入链接（CMake 用 `extra_linkflags`）。

配方实测（schroot）：

```
CFG_OK=1   # 注入 gettext 目录 + -lintl 后 configure/make 通过
```

## 4. 注意区分：上游 NLS 特性位本身的 bug

schroot 还叠加了一个上游 bug：`CMakeLists.txt` 的 NLS 特性位误取自 `${pam}`，
导致 gettext 目标缺失（已用补丁 0002 修正）。**这与本模式是两个独立问题**，
排查时应分别定位：先确认是"缺 include/缺依赖"（本模式），还是"特性检测把 NLS 关掉了"（上游 bug）。

## 5. 备选：关闭 NLS

包本身不需要本地化时，可 `-Dnls=OFF` / `--disable-nls` 规避引入 libintl；
但须在 notes.md / manifest.yaml 如实写明取舍，避免被误读为"未适配"。

## 6. 禁止做法

- ❌ 用 `#define dgettext(...)` 或 `--wrap=dgettext` 伪造符号——掩盖缺依赖，运行时 i18n 静默失效。

## 7. 验证

```bash
# 头是否可用
printf '#include <libintl.h>\nint main(){dgettext("d","s");return 0;}\n' > t.c
clang -c t.c -o /dev/null && echo HEADER_OK

# 制品仓 gettext 包是否真有符号
nm -D <gettext pkg>/lib/libintl.so | grep -w dgettext
```
