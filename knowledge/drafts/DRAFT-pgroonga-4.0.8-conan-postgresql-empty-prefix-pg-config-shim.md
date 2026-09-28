# Conan 打包的 postgresql 前缀为空：`pg_config` 回 `//...` 坏路径，必须塞 `pg_config` shim

> DRAFT-pgroonga-4.0.8-conan-postgresql-empty-prefix-pg-config-shim
> （知识库扩展草稿，路径 B）与 pgroonga 4.0.8 归档同 PR 交付。

pgroonga（PostgreSQL 的 Groonga 全文检索扩展）是用 Meson 构建的，看起来和
"Conan 里怎么找 PostgreSQL"没什么关系。但上游 `meson.build` 的第一件事就是
**用 `pg_config` 反查 PostgreSQL 安装位置**——而 Conan 打的 postgresql 制品
恰好没法回答这个问题。

## 现象

在能拿到 `postgresql/18.3` 包目录的环境里直接问它的 `pg_config`：

| 查询 | 返回 |
|------|------|
| `pg_config --includedir-server` | `//include/postgresql/server` |
| `pg_config --includedir` | `//include` |
| `pg_config --pkglibdir` | `//lib/postgresql` |
| `pg_config --sharedir` | `//share/postgresql` |
| `pg_config --bindir` | `//bin` |
| `pg_config --libdir` | `//lib` |
| `pg_config --cppflags` | `-I//include/postgresql/server -I//include` |
| `pg_config --pgxs` | `//lib/postgresql/pgxs/src/makefiles/pgxs.mk` |

`//` 在 Linux 上等价于 `/`，所以这些路径**指向文件系统根，而不是包目录**。
上游拿着 `-I//include/postgresql/server` 去编译，`postgres.h` 自然找不到；
拿着 `//lib/postgresql` 去装 `.so`，要么权限拒绝，要么写到系统路径里。

## 根因

Conan 打的 postgresql 用 **DESTDIR 安装**、configure 的 `prefix` 留空，装出来的
树是可重定位的。二进制 `pg_config` 里记录的必然是那个**空前缀**，于是所有
路径类查询都以 `/` 起头、拼出 `//...`。

这不是「Conan 打错了」——可重定位正是 Conan 包应有的性质（包目录由 Conan
的 cache 位置决定，构建时不知道）。它只是意味着：**包内的 `pg_config` 不能
被当成安装位置的权威来源**。

## 影响面

凡是「编译期需要服务端头 / 链接安装期需要 pkglibdir / sharedir」的
PostgreSQL 扩展与客户端库，只要 PG 来自 Conan，就都会踩：

| 上游构建方式 | 踩法 |
|--------------|------|
| PGXS | `make USE_PGXS=1` → `$(shell $(PG_CONFIG) --pkglibdir)` |
| autotools | `./configure PG_CONFIG=...` → 写进 `Makefile` 的 `pkglibdir` |
| meson | `run_command(pg_config, '--includedir-server')` 或 `-Dpg_config=` |
| cmake | `find_package(PostgreSQL)`（这条走 FindPostgreSQL.cmake，**不走这里**，所以 CMake 项目反而常常没事） |

反向不适用：`postgresql-topn/2.7.0` 那种在 `build()` 里**从源码自举**一份 PG
树的配方不需要 shim（它自己知道自己是装在哪的）。

## 修法：只重定向「路径类」查询的 shim

在 `generate()` 里往 `<generators>/pgsql-bin/pg_config` 写一个包装脚本：

```sh
#!/bin/sh
REAL="<pg_pkg>/bin/pg_config"
case "$1" in
  --includedir)        echo "<pg_pkg>/include" ;;
  --includedir-server) echo "<pg_pkg>/include/postgresql/server" ;;
  --pkglibdir)         echo "<pg_pkg>/lib/postgresql" ;;
  --sharedir)          echo "<pg_pkg>/share/postgresql" ;;
  --bindir)            echo "<pg_pkg>/bin" ;;
  --libdir)            echo "<pg_pkg>/lib" ;;
  --pgxs)              echo "<pg_pkg>/lib/postgresql/pgxs/src/makefiles/pgxs.mk" ;;
  --cppflags)          echo "-I<pg_pkg>/include/postgresql/server -I<pg_pkg>/include" ;;
  --cflags_sl)         echo "-fPIC" ;;
  *)                   exec "$REAL" "$@" ;;
esac
```

三个容易写错的点：

1. **`--cppflags` 必须回两个 `-I`**：`-I<...>/include/postgresql/server` 与
   `-I<...>/include`。只给 server 目录，`#include "postgres.h"` 能过，但
   它里面的 `#include "utils/..."` 会断。
2. **`--cflags_sl` 回 `-fPIC`（而不是空）**：上游把它当「编共享库需要的额外
   flag」拼进编译命令；空字符串在多数构建系统里无害，但 PGXS 的
   `PG_CFLAGS` 语义下 `-fPIC` 更贴近真 pg_config 在 Linux 上的输出。
3. **`*)` 分支必须 `exec "$REAL" "$@"`**：`--version` / `--configure` / `--cc`
   这些**值类**查询上游会用来做版本比较与特性探测，返回写死的值会伪造出
   一个不存在的 PG 版本。

写好 `chmod +x`，然后把 shim 的路径交给上游（meson 的 `-Dpg_config=`、
autotools 的 `PG_CONFIG=`、PGXS 的 `make PG_CONFIG=`）。

## 反模式

- **绕过 pg_config、直接喂路径给 `cpp_info.includedirs`**：只解决"编译期找得到
  头"，上游后续仍会自己拿 `pg_config` 算 pkglibdir/sharedir，失败点从
  configure 期挪到 install 期，症状与根因脱钩。
- **给依赖包传 `--prefix` 重装**：那是在本配方里重编一份 PG，把「依赖」变成
  「本包产物」，违反 PR 原子性；真要自举请照 `postgresql-topn/2.7.0` 写成显式
  的 build 期自举。
- **就地改写包内 `bin/pg_config`**：Conan cache 只读，且改写内容不参与包指纹，
  跨 worker 会得到"有时改过有时没改"的抖动（属最难排查的一类）。

## 判定信号

```bash
"$PG_PKG/bin/pg_config" --includedir-server   # 回 //include/postgresql/server ?
"$PG_PKG/bin/pg_config" --cppflags            # 回 -I//include/postgresql/server ?
ls "$PG_PKG/include/postgresql/server/postgres.h"   # 真实路径存在 ?
```

前两条命中 `//`、第三条为真 → 直接上 shim，不要试图给依赖包动手术。

## 相关

- `DRAFT-pgroonga-4.0.8-pg-extension-relocatable-install-and-discovery`
  —— shim 解决「找得到 PG」，那份草稿解决「PG 找得到扩展」，是这一条的下游。
- `DRAFT-pgroonga-4.0.8-groonga-dep-baked-build-prefix-pc-and-plugins-dir`
  —— 同样是「依赖包里烘焙了构建机前缀」，但那份是 pkg-config / 运行期
  插件目录，修法完全不同（靠 Conan 重新生成 + 环境变量覆盖）。
