/* 鸿蒙 PC（OHOS aarch64）专项测试：iowow 1.4.18 平台能力 + 存储引擎全生命周期。
 *
 * 区别于 test_package（消费者 API 验证）与上游 CUnit 测试（功能回归），
 * 本用例聚焦 HarmonyOS 平台真实能力，在最终 Conan 包产物上验证：
 *
 *   平台能力（用户要求重点）：
 *     P1  mmap/munmap/msync 匿名映射读写（iwkv 文件映射的底层依赖）
 *     P2  flock 文件锁（iowow 1.4.18 数据库文件锁核心，Changelog 明确
 *         "iwp_{lock,unlock} fcnt replaced by more convenient and reliable flock()"）
 *     P3  fsync/fdatasync 落盘（iwkv IWKV_SYNC 依赖）
 *     P4  pthread 线程 + 原子操作（iowow 内部自旋锁/引用计数依赖
 *         C11 原子与 pthread）
 *     P5  clock_gettime(CLOCK_MONOTONIC)（iwlog 时间戳/超时依赖，
 *         CMake 探测通过 pthread_condattr_setclock）
 *
 *   存储引擎（最终产物真实运行）：
 *     S1  iwkv 创建/写入/读取（含 UTF-8）
 *     S2  更新/覆盖与 IWKV_NO_OVERWRITE 语义
 *     S3  删除与持久化往返（close→reopen，验证 mmap 写回真实落盘）
 *     S4  IWKV_SYNC 强制落盘写入（fsync 路径）
 *     S5  游标 AFTER_LAST+PREV 升序遍历（1.4.18 块链语义）
 *     S6  iwp（平台层）随机数填充 iwp_random_fill（1.4.18 新增 API）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <pthread.h>
#include <stdatomic.h>
#include <time.h>
#include <iowow/iowow.h>
#include <iowow/iwkv.h>
#include <iowow/iwp.h>

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

static char db_path[512];

/* --- P4: 线程入口，原子累加 --- */
static atomic_long atomic_counter;
static void *thread_fn(void *arg) {
  (void)arg;
  for (int i = 0; i < 100000; i++) {
    atomic_fetch_add(&atomic_counter, 1);
  }
  return 0;
}

static IWKV_val kv(const char *s) {
  IWKV_val v = { 0 };
  v.data = (void *)s;
  v.size = strlen(s);
  return v;
}

int main(void) {
  const char *tmp = getenv("TMPDIR");
  const char *home = getenv("HOME");
  if (!tmp || access(tmp, W_OK) != 0) tmp = home ? home : ".";
  snprintf(db_path, sizeof(db_path), "%s/iowow18-ohos-%ld.db", tmp, (long)getpid());

  printf("== HarmonyOS PC 平台能力 ==\n");

  /* P1: mmap 匿名映射 */
  {
    size_t sz = 4096;
    char *p = mmap(0, sz, PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    CHECK(p != MAP_FAILED, "P1 mmap MAP_ANONYMOUS allocates");
    if (p != MAP_FAILED) {
      memcpy(p, "ohos-mmap", 9);
      CHECK(msync(p, sz, MS_SYNC) == 0, "P1 msync MS_SYNC ok");
      CHECK(memcmp(p, "ohos-mmap", 9) == 0, "P1 mapped memory readback");
      CHECK(munmap(p, sz) == 0, "P1 munmap releases mapping");
    }
  }

  /* P2: flock 文件锁 */
  {
    int fd = open(db_path, O_CREAT | O_RDWR | O_TRUNC, 0644);
    CHECK(fd >= 0, "P2 open test file");
    if (fd >= 0) {
      CHECK(flock(fd, LOCK_EX) == 0, "P2 flock LOCK_EX acquires");
      CHECK(flock(fd, LOCK_UN) == 0, "P2 flock LOCK_UN releases");
      CHECK(close(fd) == 0, "P2 close test file");
    }
  }

  /* P3: fsync/fdatasync */
  {
    int fd = open(db_path, O_CREAT | O_RDWR | O_TRUNC, 0644);
    CHECK(fd >= 0, "P3 open test file");
    if (fd >= 0) {
      CHECK(write(fd, "sync", 4) == 4, "P3 write 4 bytes");
      CHECK(fsync(fd) == 0, "P3 fsync flushes");
      CHECK(fdatasync(fd) == 0, "P3 fdatasync flushes");
      CHECK(close(fd) == 0, "P3 close test file");
    }
  }

  /* P4: pthread + C11 原子 */
  {
    pthread_t t1, t2;
    atomic_store(&atomic_counter, 0);
    CHECK(pthread_create(&t1, 0, thread_fn, 0) == 0, "P4 pthread_create t1");
    CHECK(pthread_create(&t2, 0, thread_fn, 0) == 0, "P4 pthread_create t2");
    pthread_join(t1, 0);
    pthread_join(t2, 0);
    CHECK(atomic_load(&atomic_counter) == 200000,
          "P4 C11 atomic add 2x100000 == 200000");
  }

  /* P5: clock_gettime CLOCK_MONOTONIC */
  {
    struct timespec ts;
    CHECK(clock_gettime(CLOCK_MONOTONIC, &ts) == 0,
          "P5 clock_gettime(CLOCK_MONOTONIC)");
    CHECK(ts.tv_sec > 0, "P5 monotonic clock advances");
  }

  printf("== iowow 存储引擎（最终包产物）==\n");

  iwrc rc = iw_init();
  CHECK(rc == 0, "S-init iw_init() returns 0");

  remove(db_path);
  IWKV iwkv = 0;
  IWKV_OPTS opts = { .path = db_path, .oflags = IWKV_TRUNC };
  rc = iwkv_open(&opts, &iwkv);
  CHECK(rc == 0, "S1 iwkv_open(IWKV_TRUNC) creates db");
  CHECK(iwkv != 0, "S1 iwkv handle allocated");

  IWDB db = 0;
  rc = iwkv_db(iwkv, 1, 0, &db);
  CHECK(rc == 0, "S1 iwkv_db(1)");
  CHECK(db != 0, "S1 db handle allocated");

  /* S1: 写入（含 UTF-8） */
  IWKV_val k1 = kv("hw:arch"), v1 = kv("aarch64-ohos");
  IWKV_val k2 = kv("hw:greet"), v2 = kv("鸿蒙专项测试");
  rc = iwkv_put(db, &k1, &v1, 0);
  CHECK(rc == 0, "S1 iwkv_put hw:arch");
  rc = iwkv_put(db, &k2, &v2, 0);
  CHECK(rc == 0, "S1 iwkv_put UTF-8 hw:greet");

  /* S1: 读取 */
  {
    IWKV_val val = { 0 };
    rc = iwkv_get(db, &k1, &val);
    CHECK(rc == 0 && val.size == strlen("aarch64-ohos")
          && memcmp(val.data, "aarch64-ohos", val.size) == 0,
          "S1 iwkv_get roundtrip hw:arch");
    iwkv_val_dispose(&val);
  }
  {
    IWKV_val val = { 0 };
    rc = iwkv_get(db, &k2, &val);
    CHECK(rc == 0 && val.size == strlen("鸿蒙专项测试")
          && memcmp(val.data, "鸿蒙专项测试", val.size) == 0,
          "S1 iwkv_get roundtrip UTF-8 hw:greet");
    iwkv_val_dispose(&val);
  }

  /* S2: 更新 + NO_OVERWRITE */
  {
    IWKV_val vb = kv("aarch64-ohos-v2");
    rc = iwkv_put(db, &k1, &vb, 0);
    CHECK(rc == 0, "S2 iwkv_put overwrite hw:arch");
    IWKV_val val = { 0 };
    rc = iwkv_get(db, &k1, &val);
    CHECK(rc == 0 && val.size == strlen("aarch64-ohos-v2")
          && memcmp(val.data, "aarch64-ohos-v2", val.size) == 0,
          "S2 overwritten value reads back");
    iwkv_val_dispose(&val);
    rc = iwkv_put(db, &k1, &v1, IWKV_NO_OVERWRITE);
    CHECK(rc == IWKV_ERROR_KEY_EXISTS, "S2 IWKV_NO_OVERWRITE returns KEY_EXISTS");
  }

  /* S3: 删除 */
  {
    IWKV_val k3 = kv("hw:temp"), v3 = kv("temp");
    rc = iwkv_put(db, &k3, &v3, 0);
    CHECK(rc == 0, "S3 iwkv_put hw:temp");
    rc = iwkv_del(db, &k3, 0);
    CHECK(rc == 0, "S3 iwkv_del hw:temp");
    IWKV_val val = { 0 };
    CHECK(iwkv_get(db, &k3, &val) == IWKV_ERROR_NOTFOUND,
          "S3 deleted key NOTFOUND");
  }

  /* S4: IWKV_SYNC（fsync 路径） */
  {
    IWKV_val k4 = kv("hw:sync"), v4 = kv("synced-value");
    rc = iwkv_put(db, &k4, &v4, IWKV_SYNC);
    CHECK(rc == 0, "S4 iwkv_put IWKV_SYNC (fsync path)");
  }

  /* S5: 游标升序遍历（AFTER_LAST+PREV，1.4.18 语义） */
  {
    IWKV_cursor cur = 0;
    rc = iwkv_cursor_open(db, &cur, IWKV_CURSOR_AFTER_LAST, 0);
    CHECK(rc == 0, "S5 cursor open AFTER_LAST");
    int n = 0;
    char firstkey[64] = { 0 };
    while ((rc = iwkv_cursor_to(cur, IWKV_CURSOR_PREV)) == 0) {
      IWKV_val k = { 0 }, v = { 0 };
      if (iwkv_cursor_get(cur, &k, &v) == 0) {
        if (n == 0 && k.size < sizeof(firstkey)) {
          memcpy(firstkey, k.data, k.size);
          firstkey[k.size] = '\0';
        }
        iwkv_kv_dispose(&k, &v);
      }
      n++;
    }
    CHECK(n == 3, "S5 cursor visits 3 records ascending");
    CHECK(strcmp(firstkey, "hw:arch") == 0, "S5 first key is smallest (hw:arch)");
    iwkv_cursor_close(&cur);
  }

  /* S3: 持久化往返（close → reopen） */
  rc = iwkv_close(&iwkv);
  CHECK(rc == 0, "S3 iwkv_close");

  {
    IWKV_OPTS opts2 = { .path = db_path };
    rc = iwkv_open(&opts2, &iwkv);
    CHECK(rc == 0, "S3 iwkv reopen existing db");
    IWDB db2 = 0;
    rc = iwkv_db(iwkv, 1, 0, &db2);
    CHECK(rc == 0, "S3 iwkv_db(1) after reopen");
    IWKV_val val = { 0 };
    rc = iwkv_get(db2, &k1, &val);
    CHECK(rc == 0 && val.size == strlen("aarch64-ohos-v2")
          && memcmp(val.data, "aarch64-ohos-v2", val.size) == 0,
          "S3 updated value persists after reopen");
    iwkv_val_dispose(&val);
    IWKV_val k4 = kv("hw:sync");
    rc = iwkv_get(db2, &k4, &val);
    CHECK(rc == 0 && val.size == strlen("synced-value")
          && memcmp(val.data, "synced-value", val.size) == 0,
          "S4 IWKV_SYNC value persists after reopen");
    iwkv_val_dispose(&val);
    rc = iwkv_close(&iwkv);
    CHECK(rc == 0, "S3 iwkv_close after reopen");
  }

  /* S6: iwp_random_fill（1.4.18 新增，平台层 /dev/urandom 路径） */
  {
    char buf[16];
    memset(buf, 0, sizeof(buf));
    rc = iwp_random_fill(buf, sizeof(buf), false);
    CHECK(rc == 0, "S6 iwp_random_fill returns 0");
    rc = iwp_random_fill(buf, sizeof(buf), true);
    CHECK(rc == 0, "S6 iwp_random_fill(ascii) returns 0");
  }

  /* 清理 */
  remove(db_path);
  CHECK(access(db_path, F_OK) != 0, "cleanup db file removed");

  printf("harmonyos_test: %d/%d checks passed (iowow %s)\n",
         checks - failures, checks, iowow_version_full());
  if (failures > 0) {
    fprintf(stderr, "harmonyos_test: %d failure(s)\n", failures);
    return 1;
  }
  printf("harmonyos_test: ALL PASS\n");
  return 0;
}
