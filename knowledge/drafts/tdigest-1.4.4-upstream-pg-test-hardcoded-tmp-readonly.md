# PostgreSQL 扩展上游回归测试的 `/tmp` 硬编码与 `\i` 相对包含（OHOS 适配）

> 草稿（DRAFT）。与同目录 `tdigest-1.4.4-upstream-pg-test-hardcoded-tmp-readonly.kv` 成对。

## 适用场景

用 `pg_regress` 执行 PostgreSQL 扩展的上游回归套件（`make installcheck`），
且该套件包含 COPY 导出/导入类用例或把扩展 SQL 用 `\i` 相对引入。

## 两处约束（互相独立，都会让套件"假失败"）

### ① `/tmp` 硬编码 vs OHOS 只读 `/tmp`

```sql
COPY tdigest_src TO '/tmp/tdigest_copy_text.out';
```

```
ERROR:  could not open file "/tmp/tdigest_copy_text.out" for writing: Read-only file system
ERROR:  could not open file "/tmp/tdigest_copy_text.out" for reading: No such file or directory
HINT:   COPY FROM instructs the PostgreSQL server process to read a file...
```

平台事实：`mount` → `/dev/block/dm-0 on /tmp type erofs (ro,...)`；`touch /tmp/x` → `Read-only file system`（E002）。
影响：**该用例 100% 失败**，其余用例不受影响（tdigest 首轮 9/10）。

### ② `\i` 相对包含要求 cwd 含扩展 SQL

```sql
\set ECHO none
SET client_min_messages = 'WARNING';
\i tdigest--1.0.0.sql
```

`pg_regress` 的 psql 子进程 cwd 不是 `--inputdir`；若 cwd 内没有这些脚本：

```
basic.sql: ... tdigest--1.0.0.sql: No such file or directory
```

影响：**一次性让多个用例失败**（实测 10/10 全红，极易误判为配方/平台问题）。

## 推荐做法

**归档中的上游测试文件保持逐字节不变**，在测试运行时做两件事：

```bash
mkdir -p "$TESTDIR/sql" "$TESTDIR/expected" "$TESTDIR/tmp"
cp "$TESTS_DIR/sql/"*.sql "$TESTDIR/sql/"
cp "$TESTS_DIR/expected/"*.out "$TESTDIR/expected/"
cp "$SHAREDIR/extension/"tdigest--*.sql "$TESTDIR/"                 # ② 满足 \i 相对包含
sed -i "s#/tmp/#$TESTDIR/tmp/#g" "$TESTDIR/sql/copy.sql" "$TESTDIR/expected/copy.out"   # ① 路径重写
( cd "$TESTDIR" && "$PG_REGRESS" --inputdir="$TESTDIR" --outputdir="$TESTDIR" \
    --bindir="$PGROOT/bin" --dbname=contrib_regression $REGRESS )
```

要点：`/tmp` 替换必须**同时**作用于 `.sql` 与对应的 `.out`（pg_regress 会回显 SQL，
两侧不同步则 diff 必然失败，且失败原因具误导性）。

## 禁止

| 写法 | 原因/后果 |
|---|---|
| 只改 `.sql` 或只改 `.out` | 回显不一致 → 用例恒失败，误判为功能缺陷 |
| 跳过该用例或标 skip 不说明 | 上游用例数与清点不符（R51 评审口径 → 硬性不通过） |
| 指望 `TMPDIR` 改变 COPY 的绝对路径语义 | COPY 绝对路径不受 TMPDIR 影响，问题依旧 |

## 证据（tdigest 1.4.4 @ OHOS PC aarch64）

| 阶段 | 结果 |
|---|---|
| 首轮 `make installcheck`（未适配） | 9/10，唯一失败 `copy`（`/tmp` 只读，`regression.diffs` 见上） |
| cwd 不含 `tdigest--*.sql` 时运行 pg_regress | 10/10 失败（`No such file or directory`） |
| 采用上述运行时适配后 | `# All 10 tests passed.`（10/10，exit=0） |
| 归档一致性 | `diff -r` 上游 `test/sql`、`test/expected` vs `test_package/{sql,expected}` → 完全一致 |

## 关联

- 同批草稿：`tdigest-1.4.4-pg-regress-runpath-libpq-not-found`、
  `tdigest-1.4.4-pgxs-module-rpath-build-machine-path`
- 知识库条目：E002（`/tmp` 只读 erofs）、E168（PGXS 扩展无 configure）
- 规则：R51（上游测试三步法：清点 → 实跑 → 如实回填）
