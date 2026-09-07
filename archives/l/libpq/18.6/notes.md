# libpq 18.6 Conan 配方适配笔记（平台任务 6334）

## 概况

- **任务**：6334（activity「开源鸿蒙PC专项积分赛-依赖」），taskBranch `feat/libpq-18.6`
- **版本**：18.6（上游 tarball postgresql-18.6.tar.gz，sha256 983ee554…）
- **前置**：archives/l/libpq 只有旧 v2.0 格式（16/17.2/18.1：manifest.yaml+notes.md+patches，**无 conanfile.py/test_package**）→ 本版本从零写 Conan 配方
- **交付**：libpq.so.5.18 + libpq.so.5/libpq.so 别名 + libpq.a + libpq-fe.h/libpq-events.h/postgres_ext.h
- **类型**：原生 OHOS 构建（与 18.1 同源，非 CI 交叉管线）；libpng 原生 autotools 配方为模板
- **CI 教训（build #40761）**：`package_type="library"` 必须显式声明 `options={"shared":[True,False]}`，否则 conan create 依赖图阶段直接报 `Package type is 'library', but no 'shared' option declared`。PG libpq 默认同产 .so 与 .a，两种 shared 取值交付同一产物，default True。

## 为什么必须带 bison/flex/perl 三个 tool_requires

PG 18 的发布 tarball **不再携带任何预生成的 parser/catalog 头**（只有 gram.y/scan.l/
pg_*.dat），与旧版本（自带 gram.c/scan.c/pg_*_d.h）不同：

1. `configure` 无 bison 或 flex 在 PATH 上 → 无条件 `as_fn_error` 失败（`PGAC_PATH_BISON`/
   `PGAC_PATH_FLEX` 硬门禁）。
2. `make -C src/interfaces/libpq`（MAKELEVEL=0）→ `all`/`install` 先跑
   `submake-generated-headers` → `src/backend generated-headers`，需要：
   - bison 生成 `parser/gram.h`；
   - perl 跑 `genbki.pl`（catalog 头）与 `gen_keywordlist.pl`（src/common/kwlist_d.h，
     libpq 静态合并 pgcommon 时需要）。
3. `configure` 探测 perl 并把绝对路径烤进 `src/Makefile.global` 的 `PERL='@PERL@'`
   （configure.ac 调 `PGAC_PATH_PERL`）→ **perl 必须在 configure 时就在 PATH**，
   不能只留到 make 期。

配方侧：`build_requirements()` 声明 `bison/3.8.2`、`flex/2.6.4`、`perl/5.42.2`
（精确版本，L0i 规则），`generate()` 里 `VirtualBuildEnv(self).generate()` 把它们注入
conanbuild 的 PATH/LD_LIBRARY_PATH；configure/make/install 全程 `env="conanbuild"`。

## 零补丁的达成（对比 18.1 的 3 个补丁）

18.1 打了 0001 config.guess / 0002 config.sub / 0003 configure tmpdir。18.6 全部在配方内
解决，不动源码：

| 18.1 补丁 | 18.6 处理 |
|---|---|
| 0001 config.guess 认 HarmonyOS | 不跑 config.guess：显式 `--build=$(clang -dumpmachine)`（=aarch64-linux-ohos） |
| 0002 config.sub 补 ohos* | PG18 config.sub 已接受 linux-ohos*；host_os=linux-ohos 落 `linux*` → PORTNAME=linux |
| 0003 configure tmpdir + umask 000 | 配方里 TMPDIR 指向 build 目录 + configure 内 2 处 `umask 077` 程序化放松为 022（E129 模式，幂等：已放松则跳过） |

configure flags：`--without-readline --without-zlib --without-icu --disable-nls
--disable-rpath`（readline/zlib/icu 是默认会探测的项，显式关掉；nls/rpath 一并禁用保证
确定性；openssl/libxml/gssapi 为 opt-in，无需 --without）。

## 构建方式（in-source，同 18.1 真机验证路径）

```
# 用可用 POSIX shell 解释 configure（HMDFS 上 #!/bin/sh 解释器缺失，不能直接 exec）
/system/bin/sh ./configure --build=aarch64-linux-ohos <flags>
make -C src/interfaces/libpq -j1        # 自动 submake src/port + src/common
make -C src/interfaces/libpq -j1 install DESTDIR=<package_folder>
```

- `--prefix=/`（AutotoolsToolchain 默认）→ 产物落在 `<package>/lib` 与 `<package>/include`。
- 共享库自包含：`SHLIB_LINK_INTERNAL=-lpgcommon_shlib -lpgport_shlib` 把 src/common +
  src/port 的对象静态并入 libpq.so → 运行时除 libc 外无额外 NEEDED。
- SONAME：`libpq.so.5`，真名 `libpq.so.5.18`（SO_MAJOR_VERSION=5，
  SO_MINOR_VERSION=MAJORVERSION=18）。

## 补装头（关键，沿用 18.1 教训）

`libpq-fe.h #include "postgres_ext.h"`。但 `make -C src/interfaces/libpq install` 只装
`libpq-fe.h` + `libpq-events.h`（还有 internal 头到 include/internal/），`postgres_ext.h`
在 `src/include/` 不随装 → 配方 package() 手动拷入 `include/`。（pg_config_ext.h 已在
18.x 移除，无需补。）

## HMDFS .so 软链

make install 产生 `libpq.so → libpq.so.5 → libpq.so.5.18` 软链；HMDFS 不跟随 .so 软链
（打包/消费方可能得到悬空）。package() 里把 `libpq.so.5`/`libpq.so` 解引用为
libpq.so.5.18 的真实副本，保证 `-lpq` 链接与运行期 `dlopen("libpq.so.5")` 都命中真实
ELF。

## 上游测试（rule4 口径）

上游 libpq 官方测试是 Perl TAP：`src/interfaces/libpq/t/` 下 6 个 `*.pl`
（001_uri/002_api/003_load_balance_host_list/004_load_balance_dns/
005_negotiate_encryption/006_service）。它们依赖 PostgreSQL::Test::Utils/Cluster +
IPC::Run（随服务端构建的测试基座）且多数需要一个真实 PostgreSQL 服务端实例
（002/003/004/005/006），OHOS 构建沙箱无法运行 → 配方 build() 不跑 `make check`。

test_package 用 C 消费方做**功能等价**验证（诚实回填 rule4）：
- `PQlibVersion() == 180006`（版本契约；`PG_VERSION_NUM`(18.6)=180006，与消费方
  psycopg-c 依赖 18.x 的 PQfullProtocolVersion 同源）；
- `PQconninfoParse` 解析 URI，断言 user/password/host/port/dbname/sslmode 六个字段
  —— 直接复现上游 `t/001_uri.pl`/`libpq_uri_regress.c` 覆盖的纯库内逻辑；
- `PQconnectdb("host=127.0.0.1 port=1 connect_timeout=2")` 干净返回
  `CONNECTION_BAD`（失败路径不崩，覆盖 socket/dlsym 初始化，无需服务端）。

## 测试用例对比速记

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------:|------|
| TAP 套件 | 6 | t/*.pl，需 TAP 基座 + PostgreSQL 服务端，OHOS 沙箱不可运行 |
| 适配后 C 消费测试 | 1 | test.c 11 个断言（版本契约/URI 解析/失败路径），等效覆盖 001_uri 逻辑 |

## 关键文件

- `archives/l/libpq/18.6/conanfile.py` — 配方（posix-shell 原生 configure，工具链注入）
- `archives/l/libpq/18.6/test_package/{conanfile.py,test.c,MANIFEST.yml}`
- 复用模板：`archives/l/libpq/18.1/notes.md`（先例）、`archives/l/libpng/1.6.58.2/`
  （原生 autotools + posix-shell + umask 放松 的 CI 验证模板）
