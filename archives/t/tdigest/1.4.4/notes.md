# tdigest 1.4.4 编译笔记

## 编译状态

**状态**: built（真实构建 + 上游回归测试 10/10 + 鸿蒙断言 4/4 全部通过）
权威状态以 `manifest.yaml` 为准。

## 软件信息

- 名称: tdigest（上游 META.json 里的 name 为 `t-digest`）
- 版本: 1.4.4（PGXN 发布日 2026-07-08，tag `v1.4.4` → commit `31f375c4f5437530a3d359d0eed01338cfde806a`）
- 构建系统: PGXS（PostgreSQL Extension Building Infrastructure，make + pg_config）
- 上游仓库: https://github.com/tvondra/tdigest
- 构建环境: OHOS PC aarch64 / clang 15.0.4 / OHOS musl sysroot / conan 2.29.1（OHOS 适配版）
- 依赖: `postgresql/18.3`（conan 包，提供 PGXS + 服务端头 + 可重定位 pg_config + 可运行服务端）

## 来源与版本核验

| 项 | 命令 | 关键输出 | 退出码 |
|---|---|---|---|
| tag → commit | `curl api.github.com/repos/tvondra/tdigest/git/refs/tags/v1.4.4` | `"sha": "31f375c4f5437530a3d359d0eed01338cfde806a"` | 0 |
| 源码 tarball | `sha256sum tdigest-1.4.4.tar.gz` | `cdaf21af212138a2d608c3864b45004e6b6c0197637052ad921d74ae525bf764`（与 `conandata.yml` 一致） | 0 |
| 版本（控制文件） | `tdigest.control` | `default_version = '1.4.4'` | — |
| 依赖声明 | `META.json:11-16` | `"prereqs": {"runtime": {"requires": {"PostgreSQL": "13.0.0"}}}` | — |

## 依赖检查（W0 / R36）

```
$ conan download postgresql/18.3 -r=ohpcd --only-recipe        # exit 0
$ conan install --requires=postgresql/18.3 -pr:h=<ohos-aarch64> -r=ohpcd --build=never
postgresql/18.3: Package installed 01d92cf349a0dd98ff915f4bd99a04430171517f
Install finished successfully                                  # exit 0
```

负向对照 `zzzz-control-nonexistent/1.0.0` → exit 1，证明探测口径有效。缺口数 = 0。

## 编译过程

### 1. 无 configure 步骤

上游 `Makefile:22-24`：

```make
PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
```

`MODULE_big = tdigest` / `OBJS = tdigest.o`（`Makefile:8-9`），只编译 `tdigest.c`。
`CFLAGS=\`pg_config --includedir-server\``（`Makefile:17`）→ 需要 PostgreSQL **服务端**头文件
（`tdigest.c:15-20` 硬包含 `postgres.h`、`libpq/pqformat.h`、`utils/array.h`、
`utils/builtins.h`、`utils/lsyscache.h`、`catalog/pg_type.h`）。

### 2. 构建命令与真实输出

```bash
$ make PG_CONFIG=<conan postgresql>/bin/pg_config rpath= -j1
/data/service/hnp/bin/clang ... -I<pg>/include/postgresql/server \
    -I<pg>/include/postgresql/internal ... -c -o tdigest.o tdigest.c
/data/service/hnp/bin/clang ... -shared -o tdigest.so tdigest.o -L<pg>/lib ...
# exit 0，零 warning / 零 error
```

产物：`tdigest.so`（59712 字节，ELF64 AArch64，`DT_NEEDED = libc.so`）。

**首个错误：无。** 上游 1.4.4 在 OHOS 上**一次编译通过**，未修改任何上游源码，
因此本版本没有 `patches/` 目录（R1/R8 意义上最干净的情形）。

### 3. `rpath=` 的原因（唯一构建侧调整，非源码修改）

PGXS 链接共享模块时使用 PG 的 `Makefile.global`：`rpathdir = $(libdir)`，
于是链接行里带上了 `-Wl,-rpath,'<conan 缓存>/lib'`，把构建机绝对路径写进了 `.so`：

```
# 默认（未加 rpath=）：
RUNPATH: /storage/Users/currentUser/.conan2/p/postgfee07d5886c8f/p/lib
# 加 rpath= 后：
（无 RUNPATH）
```

服务端扩展模块由 postgres 进程 dlopen，所有 PostgreSQL 符号都在该进程内解析，
rpath 没有任何作用，却会让产物随构建机路径变化（破坏可复现性与 L5 基线稳定性）。
`rpath=` 只清掉 PGXS 生成的链接标志，不触碰上游源码。

### 4. 上游测试（真实执行，10/10）

上游测试入口 = `make installcheck`（`Makefile:19` REGRESS 列表 + `Makefile:20`
`REGRESS_OPTS = --inputdir=test`），由 `pg_regress` 驱动，需运行中的 PostgreSQL 实例。

环境准备：把 conan `postgresql/18.3` 包（bin/lib/share）复制到私有目录
（保持 conan 缓存干净、可重复），`initdb` 新集群，TCP 端口随机（OHOS 版 PG 无
unix socket），`make install` 把扩展装进该私有安装。

| # | 用例 | 结果 | 耗时 |
|---|---|---|---|
| 1 | basic | ok | 6.4s |
| 2 | copy | ok | 0.4s |
| 3 | cast | ok | 0.1s |
| 4 | conversions | ok | 0.1s |
| 5 | incremental | ok | 0.5s |
| 6 | parallel_query | ok | 1.2s |
| 7 | value_count_api | ok | 4.2s |
| 8 | trimmed_aggregates | ok | 0.3s |
| 9 | combine_crash | ok | 0.2s |
| 10 | combine | ok | 5.5s |

`# All 10 tests passed.`（总数 10 / 通过 10 / 失败 0 / 跳过 0）

**测试过程中遇到的两个真实错误（均为环境/平台问题，非上游代码缺陷）：**

1. `make installcheck` → `Error loading shared library libpq.so.5 ... symbol not found`
   （exit 127）
   **根因**：PG 18.3 用 `--enable-rpath` 且 `--prefix=/` 构建，
   `pg_regress` 的 RUNPATH 是 `//lib:$ORIGIN/../lib`，只对 `bin/` 下的可执行文件有效；
   `pg_regress` 实际位于 `lib/postgresql/pgxs/src/test/regress/`。
   **修复**：测试脚本导出 `LD_LIBRARY_PATH=<pgrroot>/lib`。

2. `not ok 2 - copy`（首个失败用例）
   **根因**：上游 `test/sql/copy.sql` 把 `COPY ... TO '/tmp/tdigest_copy_*.out'` 写死到 `/tmp`，
   而 OHOS 上 `/tmp` 是只读 erofs 挂载（已知平台限制 E002）：
   `ERROR: could not open file "/tmp/tdigest_copy_text.out" for writing: Read-only file system`。
   **修复**：测试脚本在运行时把该路径字面量重写到工作目录下的可写 `tmp/`，
   并同时对 `expected/copy.out` 做同样替换（保证 psql 回显逐行仍匹配）。
   归档内保存的测试文件与上游**逐字节一致**（sha256 台账见 `test_package/MANIFEST.yml`），
   替换只发生在测试运行时。

**补充**：上游测试脚本用 `\i tdigest--*.sql` 相对包含扩展 SQL，因此 pg_regress 的
psql 子进程 cwd 必须包含这些脚本（否则 10 个用例一起报 `No such file or directory`）。

### 5. Conan 配方化

```bash
$ conan create . --version=1.4.4 -pr:h=ci/conan/profiles/ohos-aarch64 \
      -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
```

配方要点：
- `requirements()`: `postgresql/18.3`（PGXS + 服务端头 + pg_config + 测试用服务端）
- `build()`: `make PG_CONFIG=<pg_bindir>/pg_config rpath= -j1`
- `package()`: `tdigest.so → lib/`，`tdigest.control` + `tdigest--*.sql → share/extension/`，`LICENSE → licenses/`
- `test_package/`: 拉起真实 PostgreSQL 实例，`pg_regress` 重放上游 10 个用例 + 4 条鸿蒙断言
- 无 `commands.json`（产物只有共享模块与 SQL/控制文件，不含可执行文件，R38 不适用）

## 鸿蒙特有测试用例（≥1，实际 4）

| 编号 | 断言 | 说明 |
|---|---|---|
| OH-1 | `CREATE EXTENSION tdigest` 成功且 `pg_extension` 计数 = 1 | 证明包内 `.so` 能在 **OHOS 原生 postgres 进程**中 dlopen 并注册（OHOS ELF 加载路径/RPATH/签名机制均无阻塞） |
| OH-2 | 产物 ABI：ELF Machine = AArch64、`DT_NEEDED` 仅 `libc.so`、无 RUNPATH | 验证 OHOS 平台 ABI 合规且未把构建机路径写进产物 |
| OH-3 | `/tmp` 只读（E002）路径重定向后 text/binary COPY 往返 `5/10/0` | 验证 OHOS 平台约束下的可用性修复真实生效 |
| OH-4 | `tdigest_percentile(x,100,0.5)` ≈ 0.5（0..1 均匀数据） | 在 OHOS 运行时验证聚合函数数值正确性 |

## 文件清单

```
archives/t/tdigest/
├── README.md
├── manifest.yaml                     # 软件级
└── 1.4.4/
    ├── conanfile.py                  # PGXS 配方（无源码补丁）
    ├── conandata.yml                 # GitHub tag archive + sha256
    ├── manifest.yaml                 # 版本级
    ├── notes.md                      # 本文件
    ├── test_package/
    │   ├── conanfile.py              # 真实服务器测试入口
    │   ├── run_pg_test.sh            # 隔离集群 + pg_regress + 4 条鸿蒙断言
    │   ├── MANIFEST.yml              # 上游 10 用例台账（含 sha256）
    │   ├── sql/                      # 上游 10 个测试脚本（逐字节副本）
    │   └── expected/                 # 上游 25 个黄金输出（逐字节副本）
    └── reports/
```

## 后续注意

- 上游已有 1.4.5 / 1.4.6（PGXN 2026-09-08 / 2026-09-10），若要跟进新版本需重新核验
  `Changes` 与回归套件（新版可能改 `copy.sql` 的 /tmp 用法或增加用例数）。
- `postgresql` 依赖固定为 `18.3`；换用其它 PG 版本时需重跑 `make installcheck`
  （上游声明的下限是 13.0.0）。
---

**编译结束**: 2026-09-24 11:15
**最终状态**: built
