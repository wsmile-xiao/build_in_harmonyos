/* test_package 消费者验证：通过 iowow 已安装公开头文件调用真实公开 API。
 * R34：必须调用被测包 API 并验证可观察结果，禁止空壳打印。
 * 覆盖 iwkv 持久化键值数据库全生命周期：
 *   创建 → 写入 → 读取 → 覆盖更新 → IWKV_NO_OVERWRITE 语义 →
 *   IWKV_SYNC 落盘 → 游标有序遍历 → 删除 → 关闭重开持久化校验。
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <iowow/iowow.h>
#include <iowow/iwkv.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                     \
  do {                                                       \
    checks++;                                                \
    if (!(cond)) {                                           \
      fprintf(stderr, "FAIL: %s\n", msg);                    \
      failures++;                                            \
    } else {                                                 \
      printf("PASS: %s\n", msg);                             \
    }                                                        \
  } while (0)

static const char *DB_PATH = "test_iowow_kv.db";

static IWKV_val kv(const char *s) {
  IWKV_val v = { 0 };
  v.data = (void *)s;
  v.size = strlen(s);
  return v;
}

/* 读取 key 并与期望值逐字节比对（iwkv_get 返回的 value 不保证 NUL 结尾）。
 * 返回：1 匹配；0 找到但不匹配；-1 未找到（IWKV_ERROR_NOTFOUND）。 */
static int get_matches(IWDB db, const char *k, const char *exp) {
  IWKV_val key = kv(k), val = { 0 };
  if (iwkv_get(db, &key, &val) != 0) return -1;
  int ok = (val.size == strlen(exp)) && (memcmp(val.data, exp, val.size) == 0);
  iwkv_val_dispose(&val);
  return ok ? 1 : 0;
}

/* 游标遍历全库返回记录数；firstkey_out（可为 NULL）收录首键。
 * iowow 1.4.18 块链语义：AFTER_LAST + PREV 为升序遍历（与上游
 * iwkv_test1.c 一致）；BEFORE_FIRST + NEXT 实际为降序遍历。 */
static int cursor_count(IWDB db, char *firstkey_out, size_t outsz) {
  IWKV_cursor cur = 0;
  int n = 0;
  iwrc rc = iwkv_cursor_open(db, &cur, IWKV_CURSOR_AFTER_LAST, 0);
  if (rc != 0) return -1;
  while ((rc = iwkv_cursor_to(cur, IWKV_CURSOR_PREV)) == 0) {
    IWKV_val k = { 0 }, v = { 0 };
    if (iwkv_cursor_get(cur, &k, &v) == 0) {
      if (n == 0 && firstkey_out && k.size < outsz) {
        memcpy(firstkey_out, k.data, k.size);
        firstkey_out[k.size] = '\0';
      }
      iwkv_kv_dispose(&k, &v);
    }
    n++;
  }
  iwkv_cursor_close(&cur);
  return (rc == IWKV_ERROR_NOTFOUND) ? n : -1;
}

int main(void) {
  iwrc rc = iw_init();
  CHECK(rc == 0, "iw_init() returns 0");

  remove(DB_PATH); /* 清理残留，保证可重复运行 */

  /* --- 创建数据库 --- */
  IWKV iwkv = 0;
  IWKV_OPTS opts = { .path = DB_PATH, .oflags = IWKV_TRUNC };
  rc = iwkv_open(&opts, &iwkv);
  CHECK(rc == 0, "iwkv_open(IWKV_TRUNC) creates database");
  CHECK(iwkv != 0, "iwkv storage handle allocated");

  IWDB db = 0;
  rc = iwkv_db(iwkv, 1, 0, &db);
  CHECK(rc == 0, "iwkv_db(1) returns 0");
  CHECK(db != 0, "database handle allocated");

  /* --- 写入 --- */
  IWKV_val k1 = kv("key-1"), k2 = kv("key-2"), k3 = kv("key-3"), k4 = kv("key-4");
  IWKV_val v1a = kv("value-1"), v1b = kv("value-1-updated");
  IWKV_val v2 = kv("value-2"), v3 = kv("value-3"), v4 = kv("value-4");
  rc = iwkv_put(db, &k1, &v1a, 0);
  CHECK(rc == 0, "iwkv_put key-1");
  rc = iwkv_put(db, &k2, &v2, 0);
  CHECK(rc == 0, "iwkv_put key-2");
  rc = iwkv_put(db, &k3, &v3, 0);
  CHECK(rc == 0, "iwkv_put key-3");

  /* --- 读取 --- */
  CHECK(get_matches(db, "key-1", "value-1") == 1, "iwkv_get key-1 roundtrip value-1");
  CHECK(get_matches(db, "key-2", "value-2") == 1, "iwkv_get key-2 roundtrip value-2");
  CHECK(get_matches(db, "key-3", "value-3") == 1, "iwkv_get key-3 roundtrip value-3");
  CHECK(get_matches(db, "missing-key", "x") == -1, "iwkv_get missing key returns IWKV_ERROR_NOTFOUND");

  /* --- 更新（覆盖写） --- */
  rc = iwkv_put(db, &k1, &v1b, 0);
  CHECK(rc == 0, "iwkv_put overwrites existing key-1");
  CHECK(get_matches(db, "key-1", "value-1-updated") == 1, "key-1 reads back updated value");

  /* --- IWKV_NO_OVERWRITE 语义 --- */
  rc = iwkv_put(db, &k1, &v1a, IWKV_NO_OVERWRITE);
  CHECK(rc == IWKV_ERROR_KEY_EXISTS, "IWKV_NO_OVERWRITE returns IWKV_ERROR_KEY_EXISTS");

  /* --- IWKV_SYNC 落盘写入 --- */
  rc = iwkv_put(db, &k4, &v4, IWKV_SYNC);
  CHECK(rc == 0, "iwkv_put key-4 with IWKV_SYNC (fsync)");

  /* --- 游标有序遍历（4 条） --- */
  char firstkey[64] = { 0 };
  int n = cursor_count(db, firstkey, sizeof(firstkey));
  CHECK(n == 4, "cursor visits all 4 records");
  CHECK(strcmp(firstkey, "key-1") == 0, "cursor starts at smallest key (sorted order)");

  /* --- 删除 --- */
  rc = iwkv_del(db, &k2, 0);
  CHECK(rc == 0, "iwkv_del key-2");
  CHECK(get_matches(db, "key-2", "x") == -1, "deleted key-2 no longer found");
  CHECK(cursor_count(db, 0, 0) == 3, "cursor visits 3 records after delete");

  /* --- 关闭 → 重开：持久化校验 --- */
  rc = iwkv_close(&iwkv);
  CHECK(rc == 0, "iwkv_close");

  IWKV_OPTS opts2 = { .path = DB_PATH };
  rc = iwkv_open(&opts2, &iwkv);
  CHECK(rc == 0, "iwkv_open reopens existing database file");
  IWDB db2 = 0;
  rc = iwkv_db(iwkv, 1, 0, &db2);
  CHECK(rc == 0, "iwkv_db(1) after reopen");

  CHECK(get_matches(db2, "key-1", "value-1-updated") == 1, "updated value persists after reopen");
  CHECK(get_matches(db2, "key-2", "x") == -1, "deletion persists after reopen");
  CHECK(get_matches(db2, "key-3", "value-3") == 1, "key-3 persists after reopen");
  CHECK(get_matches(db2, "key-4", "value-4") == 1, "IWKV_SYNC write persists after reopen");
  CHECK(cursor_count(db2, 0, 0) == 3, "3 records after reopen");

  rc = iwkv_close(&iwkv);
  CHECK(rc == 0, "iwkv_close after reopen");

  printf("test_iowow: %d/%d checks passed (iowow %s)\n",
         checks - failures, checks, iowow_version_full());
  if (failures > 0) {
    fprintf(stderr, "test_iowow: %d failure(s)\n", failures);
    return 1;
  }
  remove(DB_PATH);
  return 0;
}
