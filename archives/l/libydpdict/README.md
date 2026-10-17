# libydpdict

## 描述
ydpdict 词典支持库 —— 读取 SLOWNIK 格式词典文件（`.idx` 索引 + `.dat` 数据），并提供
windows-1250（含上标扩展）与音标编码到 UTF-8 的转换函数。

源码托管: https://github.com/wojtekka/libydpdict

## 主页
https://toxygen.net/ydpdict/

## 已编译版本
- 1.0.4 (2026-09-25)

## 依赖
无外部运行时依赖（libxml2 为可选，未启用；`configure` 探测结果为 `LIBXML2... no`）。

下游: `ydpdict` 终端词典程序通过 `PKG_CHECK_MODULES([YDPDICT],[libydpdict >= 0.99.3])`
硬依赖本库（无 fallback），故本库须先发布。

## 提供组件
- **lib/libydpdict.a** — 词典读取与字符集转换静态库（本包为系统同名库，按 R26 默认静态
  `shared=False`）
- **include/ydpdict/ydpdict.h** — 导出头：`YDPDICT_VERSION`、`windows1250_to_utf8`、
  `phonetic_to_utf8`、`windows1250_super_to_utf8`、`ydpdict_open`、`get_count`、
  `find_word`、`get_word`
- **lib/pkgconfig/libydpdict.pc** — pkg-config 元数据（供下游 `configure` 检测）

## 使用示例
```c
#include <ydpdict.h>

YdpdictDict *d = ydpdict_open("/path/slownik.idx", "/path/slownik.dat", NULL);
int n = get_count(d);
const YdpdictWord *w = get_word(d, 0);
```

## 编译备注
- 构建系统: autotools（`configure` + libtool，上游 tarball 自带 `configure`，无需 autoreconf）。
- **上游发布包 `ltmain.sh` 与其 `aclocal.m4` 声明的 libtool 版本错配**（2.2.6b vs 2.4），
  生成的 libtool 缺 9 个 `func_*` 内建函数导致链接期失败；配方 `source()` 用 GNU libtool 2.4
  官方发行包内 `ltmain.sh` 覆盖上游残缺件（详见 `1.0.4/notes.md`，知识草稿 E543）。
- profile `[buildenv]` 导出的 `SHELL`/`CONFIG_SHELL` 优先级高于配方环境，`build()` 以
  命令前缀把 configure → config.status → libtool → Makefile 整链统一到 `/bin/sh`。
- VPATH 构建下生成的 `include/ydpdict.h` 需经 `CPPFLAGS` 补入构建目录。
- config.guess/config.sub 补 HarmonyOS 分支（E007，`patches/` 内两个 portability 补丁）。
