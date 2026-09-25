# 用 conan postgresql 包跑 pg_regress 时需显式设置 LD_LIBRARY_PATH

> 草稿（DRAFT）。与同目录 `tdigest-1.4.4-pg-regress-runpath-libpq-not-found.kv` 成对。

## 适用场景

用 conan `postgresql` 包提供 PostgreSQL 运行环境，并用 PGXS 的 `make installcheck`
（或直接调用 `pg_regress`）执行扩展的上游回归套件。

## 现象

```bash
$ make PG_CONFIG=<PGROOT>/bin/pg_config installcheck
Error loading shared library libpq.so.5: (needed by .../pgxs/src/test/regress/pg_regress)
Error relocating .../pg_regress: PQpingParams: symbol not found
make: *** [pgxs.mk:433: installcheck] Error 127       # exit=2
```

## 根因

PostgreSQL 以 `--enable-rpath --prefix=/` 构建，可执行文件 RUNPATH = `//lib:$ORIGIN/../lib`：

| 程序 | 位置 | `$ORIGIN/../lib` 解析为 | 结果 |
|---|---|---|---|
| `psql` / `initdb` … | `<prefix>/bin/` | `<prefix>/lib/` | ✅ 找到 `libpq.so.5` |
| `pg_regress` | `<prefix>/lib/postgresql/pgxs/src/test/regress/` | `<prefix>/lib/postgresql/pgxs/src/test/lib`（不存在） | ❌ 加载失败 |

```bash
$ readelf -d <PGROOT>/lib/postgresql/pgxs/src/test/regress/pg_regress | grep -E "RUNPATH|NEEDED"
 0x000000000000001d (RUNPATH)  Library runpath: [//lib:$ORIGIN/../lib]
 0x0000000000000001 (NEEDED)   Shared library: [libpq.so.5]
```

## 推荐方案

测试脚本里为 pg_regress 显式导出加载器搜索路径（不改动 conan 包内容）：

```bash
export LD_LIBRARY_PATH="$PGROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
( cd "$TESTDIR" && "$PGROOT/lib/postgresql/pgxs/src/test/regress/pg_regress" \
    --inputdir="$TESTDIR" --outputdir="$TESTDIR" --bindir="$PGROOT/bin" \
    --dbname=contrib_regression $REGRESS )
```

被测扩展模块本身不受影响：它的 `DT_NEEDED` 只有 `libc.so`，PostgreSQL 符号由 postgres 进程解析。

## 禁止

| 写法 | 原因 |
|---|---|
| 改 conan 缓存里的 postgresql 包 / 后处理 pg_regress | 破坏只读基线，本地与 CI 不一致，且并发任务互相污染 |
| 用系统 pg_regress 或直接跳过 `installcheck` | 系统无 OHOS 版 PostgreSQL；跳过等于未执行上游测试（R51 硬性不通过） |

## 证据（tdigest 1.4.4 @ OHOS PC aarch64）

| 步骤 | 结果 |
|---|---|
| `make installcheck`（未设 LD_LIBRARY_PATH） | `Error loading shared library libpq.so.5` → make Error 127，退出码 2 |
| 加 `LD_LIBRARY_PATH=<PGROOT>/lib` 后 | 进入用例执行：`ok 1 …`（首轮 9/10，唯一失败为 `/tmp` 只读，见同批草稿） |
| 修完 `/tmp` 项后 | `# All 10 tests passed.`（exit=0，10/10） |

## 关联

- 同批草稿：`tdigest-1.4.4-upstream-pg-test-hardcoded-tmp-readonly`、
  `tdigest-1.4.4-pgxs-module-rpath-build-machine-path`
- 规则：R51（上游测试三步法）
