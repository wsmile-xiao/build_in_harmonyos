# cyrus-sasl-sql 2.1.28 HarmonyOS PC adaptation

## Upstream

- Repository: https://github.com/cyrusimap/cyrus-sasl
- Release: `cyrus-sasl-2.1.28.tar.gz` (same tarball as the `cyrus-sasl` package)
- License: BSD-Attribution-HPND-disclaimer
- Language: C
- Plugin: `plugins/sql.c` (1385 lines) — SQL auxiliary property backend

## Scope

This package enables the **SQL auxprop** plugin against **SQLite3**:

```
--enable-sql --with-sqlite3=<sqlite3 package root>
```

SQL is an *auxprop* (auxiliary property) plugin, not an authentication
mechanism. It backs `auxprop_plugin: sql`, letting a server resolve user
properties from a database instead of the sasldb file. The four upstream
backends are compile-time gated by `HAVE_MYSQL` / `HAVE_PGSQL` /
`HAVE_SQLITE` / `HAVE_SQLITE3`; only SQLite3 is enabled here because it is
embedded (no running database server), which makes real initialization
verifiable on the device. MySQL/PostgreSQL/SQLite(v2) stay off.

`configure` requires at least one of the four backends when `--enable-sql`
is given (`AC_MSG_ERROR([--enable-sql chosen but neither Postgres nor MySQL
nor SQLite nor SQLite3 found])`); SQLite3 satisfies that constraint.

## Static linking (unlike GS2)

Upstream provides static support for SQL: when `--enable-sql` and
`--enable-static` are both given, `configure.ac` appends
`$(top_srcdir)/plugins/sql.c` to `SASL_STATIC_SRCS` and defines
`STATIC_SQL`. `lib/staticopen.h` already registers it:

```c
#ifdef STATIC_SQL
extern SPECIFIC_AUXPROP_PLUG_INIT_PROTO( sql );
#endif
...
#ifdef STATIC_SQL
    SPECIFIC_AUXPROP_PLUG_INIT( sql, "SQL" ),
#endif
```

So the plugin ships **inside `libsasl2.a`** with no runtime plugin search
path needed. (Contrast: the sibling `cyrus-sasl-gs2` package must ship a
shared `libgs2.so` because upstream defines no `STATIC_GS2`.)

Note on linking: in a static build the SQL object joins
`SASL_STATIC_OBJS`, while `LIB_SQLITE3` is only wired into the *shared*
`libsql.la` module (`plugins/Makefile.am`). The `sqlite3/3.53.4` runtime
dependency is therefore declared as a normal requirement so consumers link
`-lsqlite3` alongside `libsasl2.a`.

### ⚠️ 但 `--with-staticsasl` 会同时强制 `enable_shared=yes`

上面「静态链入」只对 **`libsasl2.a`** 成立。`configure.ac:104-107`：

```sh
AC_ARG_WITH(staticsasl)
if test "$with_staticsasl" = yes; then
	enable_shared=yes      # ← 即使命令行传了 --disable-shared
	enable_static=yes
fi
```

所以包内**同时**有 `libsasl2.a` 与 `libsasl2.so`，而消费者（含 test_package）
默认链接到 **`.so`**。共享库是用 `DO_DLOPEN` 构建的，`_sasl_static_plugins`
静态注册表**根本不存在**：

| 产物 | `_sasl_static_plugins` | 引用 `sql_auxprop_plug_init` |
|------|----------------------|---------------------------|
| `libsasl2.a` | **1**（有静态表） | **1** |
| `libsasl2.so.3.0.0` | **0**（无静态表） | **0** |

（`dlopen.c:432-459` 的静态表循环被 `#ifndef PIC` 包住；`configure.ac:978-980`
在 `enable_shared=yes` 时 `AC_DEFINE(DO_DLOPEN)`。）

于是 `.so` 只能经 **dlopen 从搜索路径**加载插件。不设 `SASL_PATH` 时
auxprop 列表为空 —— 表现为**连 `auxprop_plugin="sql"` 都解析不到**：
正向断言失败，而阴性对照「未注册插件被拒」反而"通过"（因为列表整体为空，
任何名字都找不到）。这正是 PR #9810 首轮 CI 的唯一失败点。

**修法**：在 `package_info()` 里按编译期 plugin dir 导出 `SASL_PATH`：

```python
self.runenv_info.append_path(
    "SASL_PATH", os.path.join(self.package_folder, "lib", "sasl2"))
```

`SASL_PATH` 由 `lib/common.c` 读取（`SASL_PATH_ENV_VAR`），是上游既有的
插件搜索路径机制。实测：不设 → 8/9（正向 FAIL）；设后 → **9/9 全过**。

> 说明：不能改用「让 test_package 链接 `.a`」来规避 —— `.so` 是消费者默认
> 拿到的产物，若 `.so` 路径不通，真实下游（如 apt 经 `find_package(Udev)` 之外
> 的 SASL 使用者）同样会踩坑。导出 `SASL_PATH` 才是对消费者正确的约定。

## OHOS patches (inherited from the cyrus-sasl family)

| Patch | Purpose |
|-------|---------|
| `0001-configure-ohos-tempdir.patch` | Generated `configure` creates its scratch dir with `umask 077`; on HMDFS the subtree is then unwritable (`config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`). Relaxed to `umask 022`. |
| `0002-lib-Makefile.in-copy-linksrcs.patch` | `lib/Makefile` symlinks the static plugin sources into `lib/` (`ln -s .libs/$@ $@`); HMDFS does not serve those links, replaced with `cp -pR`. |
| `0003-testsuite-use-int-for-getopt.patch` | `utils/testsuite.c` stores `getopt()`'s return in a `char`, which cannot represent EOF(255>=0x80) on a platform where `char` is unsigned; changed to `int`. |

The recipe additionally pre-copies the static plugin sources
(`plugins/sql.c` → `lib/sql.c`, plus the baseline mechanisms and
`sasldb/db_none.c`), mirroring the `cyrus-sasl/2.1.28.1` approach.

## OHOS build details

- `CC_FOR_BUILD=clang` / `CPP_FOR_BUILD=clang -E` are passed explicitly:
  `AC_PROG_CC_FOR_BUILD` bare-searches `gcc`/`cc`, and OHOS ships only clang.
- `TMPDIR` is pointed inside the source tree; `CONFIG_SHELL`/`SHELL` are set
  to `/system/bin/sh`.
- OHOS has no coreutils `install`; the packaged `config/install-sh` is
  injected through `MKDIR_P` / `INSTALL` / `INSTALL_PROGRAM` / `INSTALL_DATA`.
- `--disable-staticdlopen` keeps the static library from attempting runtime
  plugin loading, so the statically registered SQL auxprop is what gets used.

## Upstream tests

`utils/testsuite.c` does **not** cover the SQL backend — the only relevant
occurrence is an `auxprop_plugin` option string. Upstream therefore offers
no automated SQL verification, and validation is carried by the consumer
test below.

## Consumer test

The `test_package` consumer links `libsasl2.a` plus `-lsqlite3` and
exercises the SQL auxprop path:

1. `sasl_server_init()` succeeds with a config that sets
   `auxprop_plugin: sql` and `sql_engine: sqlite3` (proves the statically
   registered "SQL" auxprop is present — without `STATIC_SQL` the plugin
   would not be found in a static build).
2. `sasl_auxprop_request()` for the SQL plugin does not fail with the
   "no auxprop" error.
3. Database access itself is not asserted: that needs a real table layout
   and application-side configuration, which is outside package-level
   verification.

Assertions are kept as one consumer integration boundary.
