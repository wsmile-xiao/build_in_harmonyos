# libpq 18.6.1 Conan 配方适配笔记（18.6 的打包修订）

## 概况

- **版本**：18.6.1 = 上游 18.6（tarball 与 sha256 与 `libpq/18.6` 完全相同）+ 打包修订后缀（R37：
  `libpq/18.6` 已发布在制品仓，改 conanfile 必须另起版本目录，18.6 一字不动）
- **配方**：整体沿用 `archives/l/libpq/18.6/`（零补丁、tool_requires bison/flex/perl、in-source
  configure + `make -C src/interfaces/libpq`、umask 放松、HMDFS 软链实体化、postgres_ext.h 补装），
  只增两件事：**打包 `bin/pg_config`**、**补齐客户端头闭包**
- **交付**：`bin/pg_config` + libpq.so.5.18 / libpq.so.5 / libpq.so / libpq.a + libpq.pc +
  客户端头 8 个 + `postgresql/internal/` 内部头 8 个
- **真机验证**：772（3QC0124C20000772），`conan create -pr:h ohos-ci -pr:b ohos-ci -r ohpcd --update`
  rc=0（2m53s），test_package 16/16；`ohos-ci` 是仓内 `ci/conan/profiles/ohos-aarch64` 的逐字拷贝

## 为什么要修：libpq/18.6 让 psycopg2 / psycopg-c 第一步就停

psycopg2 的 `setup.py`、psycopg-c（`psycopg-binary` 的源码包）的 `psycopg_build_ext.py` 都在
`get_requires_for_build_wheel` 阶段先跑 `pg_config --includedir` / `--libdir` /（psycopg2 还有
`--version` `--includedir-server` `--pkgincludedir`）来定位 libpq，**没有 pg_config 就退出**：

```
Error: pg_config executable not found.
pg_config is required to build psycopg2 from source. ...
ERROR Backend subprocess exited when trying to invoke get_requires_for_build_wheel
```

MigBot-Air 在真机 772 上迁 psycopg2 2.9.12（2026-09-17，`psycopg2-smd-r1`）：agent 按
`--supply-missing-dep libpq` 补装了 `libpq/18.6`，重编报同一个错，台账判 fail、原因写明
「libpq/18.6 conan 制品不完整：缺 bin/pg_config、缺 libpq/libpq-fs.h」。仓内 `asterisk-pgsql/22.10.1`
的配方也为同一件事手写了一个 `pg_config` shell shim（`_ensure_pg_config_shim`）。

实查制品仓 `libpq/18.6` 的 conanmanifest：只有 `include/` 6 个头 + `lib/` 4 个文件 + `.pc` +
`share/`，**无 `bin/`**。即使 pg_config 过了，psycopg2 还要 `#include <pg_config.h>`
（psycopg/psycopg.h:30）和 `#include <libpq/libpq-fs.h>`（psycopg/lobject.h:30），
psycopg_c 要 `#include "pg_config.h"`（pq.c / types/numutils.c）——18.6 一个都没装。

## 改法（相对 18.6 的全部差异）

| 项 | 18.6 | 18.6.1 |
|---|---|---|
| build() | `make -C src/interfaces/libpq` | 同 + `make -C src/bin/pg_config`（只依赖上一步 submake 建好的 libpgport/libpgcommon） |
| package() | libpq 子目录 install + 手拷 postgres_ext.h | 同 + `src/bin/pg_config install` + `_install_client_headers()` + `_check_pg_config_installed()` |
| 头集合 | libpq-fe.h / libpq-events.h / postgres_ext.h + internal 3 个 | 对齐 `src/include/Makefile` install 前两段（= Debian libpq-dev）：再加 pg_config.h / pg_config_os.h / pg_config_manual.h / libpq/libpq-fs.h + internal c.h / port.h / postgres_fe.h / libpq/pqcomm.h / libpq/protocol.h |
| package_info | libs=["pq"] | 同 + `bindirs=["bin"]`（R38：软件级 `commands.json` 登记 pg_config） |
| test_package | cpp_info 直接喂 -I/-L | **只用 pg_config 答出的 -I/-L** 编译（与 psycopg 做法逐字相同），build() 核对 pg_config 五条答案，test() 再真 exec 一次 |

**刻意不做**：
- 不跑整个 `make -C src/include install`——那会把几百个服务端头（`include/postgresql/server/`）
  拖进一个客户端库包；psycopg2 虽把 `--includedir-server` 加进 -I，但不从那里取任何头，
  路径存在与否无影响（pg_config 照常答出该路径）。要服务端头的用 `postgresql/18.3`。
- 不改 18.6 的 10 个下游 `requires`（sqlclient / address-standardizer / asterisk-pgsql / osm2pgsql /
  mapnik / virtualpg / bacula-pgsql / kea-hook-pgsql / libpqxx / pgimportdoc）：`libpq.so.5.18`
  与 `libpq.a` 与 18.6 **逐字节相同**（真机 sha256 `55ebca84…` / `a6a51959…` 两边一致），
  它们没有理由重发；新消费方（psycopg 系）用 18.6.1。
- 不显式重签：pg_config 由 hnp clang/lld 直链，`INSTALL_SCRIPT` 是纯拷贝不重链，链接器自签
  有效——判据不是 `.codesign` 段在不在，而是真机 **exec 成功**（test() 里 `pg_config --version`
  真跑一次，见下）。

## pg_config 的重定位（为什么 --prefix=/ 打出来的包放哪都能用）

pg_config 打印的路径是编译期 `pg_config_paths.h` 里的 `/include`、`/lib`（AutotoolsToolchain
默认 `--prefix=/`），运行时经 `src/port/path.c:make_relative_path()` 按**自身可执行文件所在的
bin/** 反推 prefix：`<X>/bin/pg_config` → `--includedir` 答 `<X>/include`。真机两处实测：

```
conan cache:  /storage/Users/currentUser/.conan2/p/b/libpqccd4587c26cc1/p/{include,lib,include/postgresql/server}
usr_local 摊平前缀: ~/Download/pq1861-prefix/{include,lib}
```

前提是 bin/ 与 include/ lib/ 在同一前缀下——conan cache 与 `usr_local` deployer 都满足。

## 真机验证记录（772，2026-09-22）

`conan create` rc=0；包内容：

```
bin/pg_config                                   ELF64 AArch64 PIE, NEEDED=libc.so, .codesign 在
lib/libpq.so.5.18  SONAME=libpq.so.5  NEEDED=libc.so   sha256 55ebca84… (== libpq/18.6)
lib/libpq.a                                       sha256 a6a51959… (== libpq/18.6)
include/{libpq-fe,libpq-events,postgres_ext,pg_config,pg_config_os,pg_config_manual}.h include/libpq/libpq-fs.h
include/postgresql/internal/{c,port,postgres_fe,libpq-int,fe-auth-sasl,pqexpbuffer}.h + libpq/{pqcomm,protocol}.h
```

pg_config 答案（conan cache 内）：`--version` = `PostgreSQL 18.6`；`--includedir/--libdir/--bindir`
= 包内对应目录；`--includedir-server` = `<pkg>/include/postgresql/server`；`--pkgincludedir` =
`<pkg>/include/postgresql`；`--libs` = `-lpgcommon -lpgport -lm`。

test_package：build() 五条 pg_config 查询全部通过核对；探针 16/16（新补头的 5 条 + 原 11 条）；
test() 真 exec `pg_config --version` → `PostgreSQL 18.6`。

### 端到端：psycopg2 / psycopg-c 从 sdist 编译

`conan install --requires=libpq/18.6.1 --deployer=usr_local --deployer-folder=~/Download/pq1861-prefix`
后 `PATH=<prefix>/bin:$PATH`，设备 python 3.12.9 venv：

| 库 | 结果 |
|---|---|
| psycopg2 2.9.12（sdist，`pip wheel --no-build-isolation`） | `psycopg2-2.9.12-cp312-cp312-ohos_aarch64.whl`；import 成功：`compiled against libpq 180006 / runtime 180006`，`extensions.lobject` 在（依赖 libpq-fs.h）；扩展 NEEDED = libpython3.12.so.1.0, libpq.so.5, libc.so |
| psycopg-c 3.3.6（sdist，同法） | `psycopg_c-3.3.6-cp312-cp312-ohos_aarch64.whl`；`import psycopg` → `impl c / runtime libpq 180006 / built against 180006` |

两个与 libpq 无关的设备事实，复现时要带上：① 设备 python 的 `subprocess` 不按 PATH 找裸名
（`_posixsubprocess` 缺失），故编译器须给绝对路径 `CC=/data/service/hnp/bin/clang`，psycopg_c
写死的裸名 `pg_config` 只能靠 cwd 下的同名软链解析（psycopg2 自己按 PATH 逐项 `os.path.exists`
找、不受影响）；② musl 无延迟绑定，扩展须显式 `LDFLAGS=-lpython3.12`（MigBot-Air build.sh 同法）。

## 上游测试（rule4 口径）

与 18.6 相同：上游 libpq 官方测试是 6 个 Perl TAP（需 PostgreSQL::Test 基座 + 服务端），沙箱不可跑；
pg_config 上游测试 `src/bin/pg_config/t/001_pg_config.pl` 只是 `program_help_ok / program_version_ok /
program_options_handling_ok` 三个通用探针，同样依赖 TAP 基座。test_package 对应地做了：pg_config
五条查询 + 答案核对 + `--version` 真 exec，覆盖 001_pg_config 的 version 探针语义；test.c 的 16 条
断言覆盖头闭包 + 版本契约 + URI 解析（001_uri）+ 失败路径。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| libpq TAP | 6 | t/*.pl，需 TAP 基座 + 服务端，沙箱不可运行 |
| pg_config TAP | 1 | t/001_pg_config.pl（help/version/options 探针） |
| 适配后 test_package | 1 + 1 | conanfile.py build()/test() 的 pg_config 消费面（5 查询 + 9 核对 + exec）；test.c 16 个 CHECK |

## 关键文件

- `archives/l/libpq/18.6.1/conanfile.py` — 在 18.6 基础上加 pg_config 构建/安装、客户端头闭包、bindirs
- `archives/l/libpq/18.6.1/test_package/{conanfile.py,test.c,MANIFEST.yml}` — 经 pg_config 消费的测试
- `archives/l/libpq/commands.json` — R38 登记 `pg_config`
- 先例：`archives/l/libpq/18.6/notes.md`（本配方的全部构建细节）
