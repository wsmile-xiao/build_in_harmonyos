/*
 * HarmonyOS 专项测试 — unqlite 1.2.1 磁盘文件持久化语义。
 *
 * 与 test_unqlite.c（消费者用例，使用 :mem: 内存库）不同，本测试针对
 * OHOS 平台上真实文件系统路径验证库的持久化能力：
 *   1) 在可写路径创建文件型数据库（UNQLITE_OPEN_CREATE）；
 *   2) 写入 KV 记录并 unqlite_commit() 落盘；
 *   3) 关闭数据库；
 *   4) 重新打开同一文件，验证记录持久化（跨句柄、跨进程级重开）；
 *   5) 删除记录并 commit 后，重开验证删除已持久化；
 *   6) 清理测试文件。
 * 全程使用公开头文件与公开 API（unqlite_open/kv_store/kv_fetch/kv_delete/
 * commit/close），为 OHOS 文件系统上的真实业务语义（持久存储、事务提交）
 * 提供可观测断言。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "unqlite.h"

static int failures = 0;

static void check(int cond, const char* what)
{
	if(cond)
		printf("PASS: %s\n", what);
	else
	{
		printf("FAIL: %s\n", what);
		failures++;
	}
}

int main(void)
{
	char dbpath[512];
	const char *tmpdir = getenv("TMPDIR");
	const char key[] = "persist-key";
	const char val[] = "durable-value-on-ohos";
	unqlite_int64 len = 0;
	char buf[128];
	unqlite *pDb = NULL;
	int rc;

	/* 使用 OHOS 环境实际可写临时目录；未设置时回退到相对当前目录。 */
	if(tmpdir == NULL || tmpdir[0] == 0)
		tmpdir = ".";
	snprintf(dbpath, sizeof(dbpath), "%s/unqlite_ohos_persist_%ld.db",
		tmpdir, (long)getpid());

	/* 1) 创建文件型数据库 */
	rc = unqlite_open(&pDb, dbpath, UNQLITE_OPEN_CREATE);
	check(rc == UNQLITE_OK, "create file-backed database");
	if(rc != UNQLITE_OK)
	{
		printf("%d check(s) FAILED\n", failures);
		return 1;
	}

	/* 2) 写入并 commit 落盘 */
	rc = unqlite_kv_store(pDb, key, -1, val, (unqlite_int64)strlen(val));
	check(rc == UNQLITE_OK, "kv_store into file-backed db");
	rc = unqlite_commit(pDb);
	check(rc == UNQLITE_OK, "unqlite_commit persists to disk");

	/* 3) 关闭 */
	rc = unqlite_close(pDb);
	check(rc == UNQLITE_OK, "close database");
	pDb = NULL;

	/* 4) 重开同一文件，验证持久化 */
	rc = unqlite_open(&pDb, dbpath, UNQLITE_OPEN_READONLY);
	check(rc == UNQLITE_OK, "reopen persisted database file");
	/* pBufLen 是 in|out：先以 NULL 查询长度，再带缓冲取回 */
	len = 0;
	rc = unqlite_kv_fetch(pDb, key, -1, NULL, &len);
	check(rc == UNQLITE_OK && len == (unqlite_int64)strlen(val),
		"persisted record length survives reopen");
	memset(buf, 0, sizeof(buf));
	rc = unqlite_kv_fetch(pDb, key, -1, buf, &len);
	check(rc == UNQLITE_OK
		&& strcmp(buf, val) == 0,
		"persisted record value survives reopen");
	unqlite_close(pDb);
	pDb = NULL;

	/* 5) 删除并 commit，重开验证删除已持久化 */
	rc = unqlite_open(&pDb, dbpath, UNQLITE_OPEN_CREATE);
	check(rc == UNQLITE_OK, "reopen for deletion");
	rc = unqlite_kv_delete(pDb, key, -1);
	check(rc == UNQLITE_OK, "kv_delete removes persisted record");
	rc = unqlite_commit(pDb);
	check(rc == UNQLITE_OK, "commit deletion");
	unqlite_close(pDb);
	pDb = NULL;

	rc = unqlite_open(&pDb, dbpath, UNQLITE_OPEN_READONLY);
	check(rc == UNQLITE_OK, "reopen after deletion commit");
	len = 0;
	rc = unqlite_kv_fetch(pDb, key, -1, NULL, &len);
	check(rc == UNQLITE_NOTFOUND, "deleted record stays gone after reopen");
	unqlite_close(pDb);
	pDb = NULL;

	/* 6) 清理 */
	remove(dbpath);

	if(failures != 0)
	{
		printf("%d check(s) FAILED\n", failures);
		return 1;
	}
	printf("all unqlite 1.2.1 OHOS persistence checks passed\n");
	return 0;
}
