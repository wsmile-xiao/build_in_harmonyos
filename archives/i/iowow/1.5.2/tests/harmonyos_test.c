/* 鸿蒙专项测试：iowow iwkv 持久化 key/value 存储在 HarmonyOS 上的真实运行验证。
 *
 * 选型理由：iwkv 是 iowow 的核心存储引擎（skiplist + WAL + 文件映射），
 * 涉及真实文件创建、写入、fsync、mmap、读取与删除 —— 在 HarmonyOS 上
 * 依赖文件系统与运行时权限，是库中平台耦合最深、最值得专项验证的公开 API
 * 集合（上游 CUnit 测试同样覆盖，但本用例在 OHOS 工具链产物上独立运行，
 * 且走持久化往返，验证存储引擎在目标平台的完整生命周期）。
 *
 * 验证点：
 *   1. iwkv_init() 初始化
 *   2. iwkv_open 在可写目录创建存储文件（IWKV_TRUNC）
 *   3. iwkv_put / iwkv_get_copy 写入并读回（含 UTF-8 内容）
 *   4. iwkv_close 持久化落盘
 *   5. 重新 open（只读路径）验证数据真实持久化（非仅内存）
 *   6. 清理存储目录
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <iowow/iwkv.h>
#include <iowow/iwlog.h>

static int failures = 0;

#define CHECK(cond, msg)                                     \
  do {                                                       \
    if (!(cond)) {                                           \
      fprintf(stderr, "FAIL: %s\n", msg);                    \
      failures++;                                            \
    } else {                                                 \
      printf("PASS: %s\n", msg);                             \
    }                                                        \
  } while (0)

static char db_path[512];

int main(void) {
  /* 使用 TMPDIR（若为只读 /tmp 则回退用户主目录），保证目录可写 */
  const char *tmp = getenv("TMPDIR");
  const char *home = getenv("HOME");
  if (!tmp || access(tmp, W_OK) != 0) {
    tmp = home ? home : ".";
  }
  snprintf(db_path, sizeof(db_path), "%s/iowow-ohos-test-%ld.db", tmp, (long)getpid());

  iwrc rc = iwkv_init();
  CHECK(rc == 0, "iwkv_init() returns 0");

  struct iwkv_opts opts;
  memset(&opts, 0, sizeof(opts));
  opts.path = db_path;
  opts.oflags = IWKV_TRUNC;   /* 新建/截断 */

  struct iwkv *kv = NULL;
  rc = iwkv_open(&opts, &kv);
  CHECK(rc == 0 && kv != NULL, "iwkv_open creates store file");

  struct iwdb *db = NULL;
  rc = iwkv_db(kv, 1, 0, &db);
  CHECK(rc == 0 && db != NULL, "iwkv_db opens db 1");

  /* 写入一组 key/value（含 UTF-8 中文内容） */
  struct iwkv_val k1 = { .data = "hw:arch", .size = sizeof("hw:arch") - 1 };
  struct iwkv_val v1 = { .data = "aarch64-ohos", .size = sizeof("aarch64-ohos") - 1 };
  rc = iwkv_put(db, &k1, &v1, 0);
  CHECK(rc == 0, "iwkv_put writes key 1");

  struct iwkv_val k2 = { .data = "hw:greet", .size = sizeof("hw:greet") - 1 };
  struct iwkv_val v2 = { .data = "鸿蒙专项测试", .size = strlen("鸿蒙专项测试") };
  rc = iwkv_put(db, &k2, &v2, 0);
  CHECK(rc == 0, "iwkv_put writes UTF-8 key 2");

  /* 读回验证 */
  char buf[128];
  size_t vsz = 0;
  rc = iwkv_get_copy(db, &k1, buf, sizeof(buf), &vsz);
  CHECK(rc == 0 && vsz == sizeof("aarch64-ohos") - 1
        && memcmp(buf, "aarch64-ohos", vsz) == 0, "get_copy round-trips key 1");

  memset(buf, 0, sizeof(buf));
  vsz = 0;
  rc = iwkv_get_copy(db, &k2, buf, sizeof(buf), &vsz);
  CHECK(rc == 0 && vsz == strlen("鸿蒙专项测试")
        && memcmp(buf, "鸿蒙专项测试", vsz) == 0, "get_copy round-trips UTF-8 key 2");

  /* 关闭并重新打开（只读）验证持久化 */
  rc = iwkv_close(&kv);
  CHECK(rc == 0, "iwkv_close persists store");

  struct iwkv_opts ropts;
  memset(&ropts, 0, sizeof(ropts));
  ropts.path = db_path;
  ropts.oflags = IWKV_RDONLY;
  kv = NULL;
  rc = iwkv_open(&ropts, &kv);
  CHECK(rc == 0 && kv != NULL, "reopen store read-only");

  db = NULL;
  rc = iwkv_db(kv, 1, 0, &db);
  if (rc == 0 && db) {
    memset(buf, 0, sizeof(buf));
    vsz = 0;
    rc = iwkv_get_copy(db, &k1, buf, sizeof(buf), &vsz);
    CHECK(rc == 0 && vsz == sizeof("aarch64-ohos") - 1
          && memcmp(buf, "aarch64-ohos", vsz) == 0, "data persisted after reopen");
  } else {
    CHECK(0, "reopen db 1 readable");
  }
  iwkv_close(&kv);

  /* 清理测试目录 */
  unlink(db_path);
  char *wal = malloc(strlen(db_path) + 8);
  if (wal) {
    sprintf(wal, "%s-wal", db_path);
    unlink(wal);
    free(wal);
  }
  CHECK(access(db_path, F_OK) != 0, "test store file cleaned up");

  if (failures == 0) {
    printf("harmonyos_test: ALL PASS (iowow %s, TMPDIR=%s)\n",
           iowow_version_full(), tmp);
    return 0;
  }
  fprintf(stderr, "harmonyos_test: %d failure(s)\n", failures);
  return 1;
}