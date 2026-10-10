/*-
 * db5.3 5.3.28 consumer test — uses ONLY the delivered artifacts
 * (include/db.h + libdb-5.3.so via CMakeDeps' db5_3::db5_3).
 *
 * 覆盖：事务型环境（DB_INIT_TXN/LOCK/LOG/MPOOL）→ 事务提交写入 → 读回逐条比对
 *      → 游标全量遍历（条数 + 键的字典序）→ 事务内删除 → 事务回滚（写入必须消失）。
 * 输出 [ok]/[FAIL] 与 "N 项检查，M 项失败"，用退出码表达结果（不用 assert 宏）。
 */
#include <db.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int checks = 0;
static int fails = 0;

static void
check(int ok, const char *label)
{
	checks++;
	if (!ok)
		fails++;
	printf("  [%s] %s\n", ok ? "ok" : "FAIL", label);
}

static void
dbt_user(char *buf, size_t len, DBT *dbt)
{
	memset(dbt, 0, sizeof(*dbt));
	dbt->data = buf;
	dbt->ulen = (u_int32_t)len;
	dbt->flags = DB_DBT_USERMEM;
}

static void
dbt_lit(const char *s, DBT *dbt)
{
	memset(dbt, 0, sizeof(*dbt));
	dbt->data = (void *)s;
	dbt->size = (u_int32_t)strlen(s);
}

static const char *PAIRS[5][2] = {
	{"alpha", "1"}, {"bravo", "2"}, {"charlie", "3"},
	{"delta", "4"}, {"echo", "5"}
};

int
main(void)
{
	const char *home = "./consumer_env";
	const char *expect[5] = {"alpha", "bravo", "charlie", "delta", "echo"};
	DB_ENV *envp = NULL;
	DB *dbp = NULL;
	DB_TXN *txn = NULL;
	DBC *dbc = NULL;
	DBT key, data;
	char kbuf[64], dbuf[64];
	char found[5][64];
	int found_n = 0;
	int ordered = 1;
	int ret, i;

	printf("db5.3 consumer (C API): %s\n", db_version(NULL, NULL, NULL));
	(void)mkdir(home, 0755);

	ret = db_env_create(&envp, 0);
	check(ret == 0, "db_env_create");
	if (ret != 0)
		return 1;
	ret = envp->open(envp, home, DB_CREATE | DB_INIT_MPOOL | DB_INIT_LOCK |
	    DB_INIT_LOG | DB_INIT_TXN | DB_RECOVER, 0);
	check(ret == 0, "env->open (txn + lock + log + mpool + recover)");
	if (ret != 0)
		return 1;
	ret = db_create(&dbp, envp, 0);
	check(ret == 0, "db_create (inside env)");
	if (ret != 0)
		return 1;

	/* ① 一个事务里写入 5 条 */
	ret = envp->txn_begin(envp, NULL, &txn, 0);
	check(ret == 0, "txn_begin");
	if (ret == 0) {
		ret = dbp->open(dbp, txn, "primary.db", "primary", DB_BTREE,
		    DB_CREATE, 0);
		check(ret == 0, "db->open (btree, inside transaction)");
	}
	if (ret == 0) {
		int put_rc = 0;
		for (i = 0; i < 5; i++) {
			dbt_lit(PAIRS[i][0], &key);
			dbt_lit(PAIRS[i][1], &data);
			if (dbp->put(dbp, txn, &key, &data, 0) != 0)
				put_rc = -1;
		}
		check(put_rc == 0, "5 x db->put inside one transaction");
		ret = txn->commit(txn, 0);
		txn = NULL;
		check(ret == 0, "txn->commit");
	}

	/* ② 读回逐条比对（DB_DBT_USERMEM 固定缓冲，结果可核对） */
	{
		int get_rc = 0;
		for (i = 0; i < 5; i++) {
			dbt_lit(PAIRS[i][0], &key);
			dbt_user(dbuf, sizeof(dbuf), &data);
			if (dbp->get(dbp, NULL, &key, &data, 0) != 0 ||
			    data.size != (u_int32_t)strlen(PAIRS[i][1]) ||
			    memcmp(data.data, PAIRS[i][1], data.size) != 0) {
				printf("      mismatch for key '%s'\n", PAIRS[i][0]);
				get_rc = -1;
			}
		}
		check(get_rc == 0, "db->get x5 returns exactly the values written");
	}

	/* ③ 游标全量遍历：条数 + 键的字典序 */
	ret = dbp->cursor(dbp, NULL, &dbc, 0);
	check(ret == 0, "db->cursor");
	if (ret == 0) {
		for (;;) {
			dbt_user(kbuf, sizeof(kbuf), &key);
			dbt_user(dbuf, sizeof(dbuf), &data);
			ret = dbc->get(dbc, &key, &data, DB_NEXT);
			if (ret != 0)
				break;
			if (found_n < 5) {
				kbuf[key.size < sizeof(kbuf) ? key.size
				    : sizeof(kbuf) - 1] = '\0';
				strncpy(found[found_n], kbuf, sizeof(found[0]) - 1);
				found[found_n][sizeof(found[0]) - 1] = '\0';
			}
			found_n++;
		}
		(void)dbc->close(dbc);
		dbc = NULL;
		check(ret == DB_NOTFOUND, "cursor DB_NEXT ends with DB_NOTFOUND");
	}
	check(found_n == 5, "cursor visits exactly 5 records");
	for (i = 0; i < 5 && i < found_n; i++)
		if (strcmp(found[i], expect[i]) != 0)
			ordered = 0;
	check(found_n == 5 && ordered, "cursor order = btree key order (alpha..echo)");

	/* ④ 事务内删除一条 */
	ret = envp->txn_begin(envp, NULL, &txn, 0);
	dbt_lit("charlie", &key);
	if (ret == 0)
		ret = dbp->del(dbp, txn, &key, 0);
	if (ret == 0)
		ret = txn->commit(txn, 0);
	else if (txn != NULL)
		(void)txn->abort(txn);
	txn = NULL;
	check(ret == 0, "txn: delete 'charlie' and commit");

	/* ⑤ 事务回滚：写入必须消失 */
	{
		int put_ok, gone = 0;
		ret = envp->txn_begin(envp, NULL, &txn, 0);
		dbt_lit("zulu", &key);
		dbt_lit("999", &data);
		put_ok = (ret == 0) && (dbp->put(dbp, txn, &key, &data, 0) == 0);
		if (ret == 0)
			(void)txn->abort(txn);
		txn = NULL;
		dbt_lit("zulu", &key);
		dbt_user(dbuf, sizeof(dbuf), &data);
		if (dbp->get(dbp, NULL, &key, &data, 0) == DB_NOTFOUND)
			gone = 1;
		check(put_ok && gone, "aborted transaction leaves no record behind");
	}

	(void)dbp->close(dbp, 0);
	(void)envp->close(envp, 0);

	printf("\n%d checks, %d failed\n", checks, fails);
	return fails == 0 ? 0 : 1;
}
