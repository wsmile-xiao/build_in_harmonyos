# elfutils 0.195 编译笔记（HarmonyOS PC · Conan autotools）

## 产物
`libelf.so.1`、`libdw.so.1`、`libasm.so.1` 及 `eu-*` 工具（`--program-prefix=eu-`）。
SONAME 与上游一致（`libelf.so.1`），未做后缀改名。

## 关键适配

### 1. musl 缺 glibc 的 error.h（补丁 0001）
`lib/threadlib.h`（经 `eu-config.h`）无条件 `#include <error.h>`，musl 无此头。
改为条件包含：有 `error.h` 才用 `error()`，否则回落到 `fprintf(stderr)+exit`。

### 2. musl 有 libintl.h 但无实现符号（补丁 0002）
OHOS sysroot 的 `libintl.h` 是**空壳**：头在、`__dcgettext` 等符号不在。
`--disable-nls` 只关掉 NLS 构建，`eu-config.h` 里的 `_()`、`ngettext`、
`textdomain`、`bindtextdomain` 仍会展开成 gettext 调用。
补丁在 `eu-config.h` 里为这一族提供无操作宏。

> 教训：这个族**不能靠名字里含 "gettext" 去 grep**——`textdomain` /
> `bindtextdomain` 不含该子串，第一次扫漏了它俩，白跑一轮 339s 构建。
> 正确做法是按**功能**扫：`\b[a-z_]*(gettext|textdomain)[a-z_]*\s*\(`。

### 3. program_invocation_short_name 在 OHOS musl 上不存在（补丁 0002）
即使定义了 `_GNU_SOURCE` 也没有（真机探针实测证伪了"musl 在 _GNU_SOURCE 下提供它"的说法）。
改用传统 BSD 全局 `extern char *__progname`——同一探针确认可用。

### 4. configure 的 AC_CHECK_LIB 探测要吃到依赖路径
`--with-zstd` 会试链 `-lzstd`，不给路径直接 `configure: error: missing -lzstd`。
依赖的 include/lib 走 `os.environ` 的 `CPPFLAGS`/`LDFLAGS`/`LIBS` 注入
（实测 `AutotoolsToolchain.extra_*` 不一定落到 configure 环境），
并把依赖 libdir 加进构建期 `LD_LIBRARY_PATH` 供探测程序运行。

## 依赖
zlib、zstd、bzip2、musl-fts、musl-obstack、argp-standalone

## 状态
built —— 真机 `conan create` 通过，test_package 对 libelf 与 libdw 均做**真实断言**
（非仅链接成功）：打开 ELF 读节区、遍历 DWARF；并核对 SONAME == `libelf.so.1`。
