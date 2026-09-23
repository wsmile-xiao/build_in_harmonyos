# DRAFT-libgtop-glib-libintl-link — autotools 消费者链 conan glib 的 g_libintl_ngettext 链接缺失与 rpath 注入

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-09
> **Severity**: 🔴 high | **Category**: linking / libintl / glib / autotools / OHOS / conan

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|---------|---------|--------|--------------------------|
| **E015**（argp-standalone） | 正式收录 | 链接期 libintl_dgettext/dgettext 缺失，`LIBS="-lintl"` 解决 | 非本题——E015 是普通 libintl 库缺失；本题符号为 glib 包内 proxy-libintl 命名的 g_libintl_ngettext |
| **E027**（-lintl） | 正式收录 | 链接期 `undefined symbol.*libintl_gettext` | 非本题——无 conan glib 包内置 libintl.so + rpath 注入先例 |
| **E107**（GLib static gettext） | 正式收录 | g_libintl / libintl.a 符号缺失，方案为建中间库 | 方案不同——本题用 LDFLAGS `-lintl -Wl,-rpath` 双注入，不建中间库 |
| **E123**（meson 静态库 libintl） | 正式收录 | meson build.ninja 链接期 g_libintl_* 缺失 | 构建系统不同——本题是 autotools（configure/Makefile） |
| **E142**（libbytesize gnulib） | 正式收录 | NLS 重命名符号链接缺失 | 非本题——本题由 glib 头文件宏映射触发 |

> index.tsv 查证（2026-09-09）：`g_libintl_ngettext` 命中 0 条、
> `libintl.so.8` 命中 0 条、`rpath` 命中 0 条——无正面撞车；既有 libintl
> 条目均为普通链接期，无 conan glib 内置 libintl.so + autotools rpath 组合。

## Scope（何时用）

在 OHOS 上以 **autotools** 构建、链接 **conan glib**（静态库）的软件，
若 include `glib/gi18n-lib.h` 且出现：

- 链接报 `ld.lld: error: undefined symbol: g_libintl_ngettext`（引用来自
  libgtop-2.0.a 等静态库内 read.c/write.c 的 ngettext 调用）；
- 或 LDFLAGS 已带 `-lintl` 后 configure 报
  `cannot run C compiled programs`（conftest 运行期找不到 libintl.so.8）。

## Symptom

```text
ld.lld: error: undefined symbol: g_libintl_ngettext
>>> referenced by read.c
>>>               read.o:(glibtop_read_l) in archive ../../lib/.libs/libgtop-2.0.a
# LDFLAGS=-L<glib>/lib -lintl 后：
configure: error: cannot run C compiled programs.
# config.log: Error loading shared library libintl.so.8: (needed by ./conftest)
```

## Root Cause

conan glib 包内 `include/libintl.h` 无条件
`#define ngettext g_libintl_ngettext`（glib 内嵌 proxy-libintl 命名），
且该符号由 glib 包自带 `lib/libintl.so` 导出（`nm -D` 可见
`T g_libintl_ngettext`）。OHOS libc 无 libintl。autotools 项目链接 glib
静态库时引用该符号必须显式 `-lintl`；而 glib 包 libdir 是 conan 缓存私有
路径，LDFLAGS 带 -lintl 后 configure conftest 与 daemon 运行期均无法按默认
搜索路径定位 libintl.so.8。

## Solution

配方 generate() 中（参考 archives/l/libgtop/2.41.3/conanfile.py）：

```python
tc.configure_args.append(
    "LDFLAGS=-L{} -lintl -Wl,-rpath,{}".format(glib_libdir, glib_libdir))
# package_info:
self.cpp_info.libs = ["gtop-2.0", "intl"]   # 让 libgtop-2.0.pc Libs 带 -lintl
```

要点：LDFLAGS 用 configure_args 传（写入 Makefile 链接行）；rpath 解决
conftest/daemon 运行期定位；package_info.libs 增补 intl 使消费者
pkg-config 链接自动带 -lintl。

## Verification

```bash
cd archives/l/libgtop/2.41.3
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# 全绿；test_package 消费者经 pkg-config 编译链接运行通过
```

## 适用边界 / 反例

- 若 glib 以 shared 方式链接，g_libintl_* 由 libglib-2.0.so 传递解析，
  无需 -lintl；
- 纯 CMake 消费者走 CMakeDeps 目标链时，组件 requires 已携带 libintl，
  无需手动 rpath；
- rpath 指向 conan 缓存路径，仅用于构建期可执行（conftest/daemon 自检），
  发布产物运行期依赖 conanrun 环境的 LD_LIBRARY_PATH。

## 关系字段

- similar_to: E015, E027, E107, E123, E142
- caused_by: glib 包 libintl.h 宏映射 + OHOS 无 libintl
- conflicts_with: 无