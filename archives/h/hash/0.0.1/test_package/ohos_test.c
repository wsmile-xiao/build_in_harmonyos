/*
 * ohos_test.c — hash 0.0.1 HarmonyOS 专项测试
 *
 * 针对本次适配在 OHOS (aarch64, clang 15, OHOS libc) 上验证 hash 库的真实
 * 行为，不是上游测试的复述：
 *   1. 大规模压力: 10 万条字符串键/指针值插入, 验证 size 与哈希表自动扩容
 *   2. 全量读取校验: 10 万键逐条取回一致 (覆盖 khash 探测序列)
 *   3. 迭代完整性: hash_each 遍历数量 == 插入数量
 *   4. 删除与清空: 删除一半后 size 减半, clear 后归零 (覆盖 tombstones/重建)
 *   5. 生命周期: 反复 new/free 并逐一释放 strdup 键, 防止内存泄漏 (OHOS libc malloc/free)
 *
 * 仅通过安装后公开头文件 hash.h/khash.h 与 libhash.a 使用，与上游
 * TEST_HASH 自测分别计数。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hash.h"

#define N_ENTRIES 100000

int
main(void) {
  int rc = 0;
  int nkeys = 0;
  hash_t *hash = hash_new();
  if (!hash) { fprintf(stderr, "FAIL: hash_new\n"); return 1; }

  /* 1) 大规模插入（触发 khash 多次扩容重哈希）
   * 注意: clibs/hash 存储的是键指针而非拷贝，键必须用稳定内存
   * （字符串字面量或 strdup 后的堆内存），不能复用栈缓冲区。*/
  char **keys = malloc(sizeof(char *) * N_ENTRIES);
  if (!keys) { fprintf(stderr, "FAIL: malloc keys\n"); hash_free(hash); return 1; }
  for (int i = 0; i < N_ENTRIES; i++) {
    char key[32];
    snprintf(key, sizeof(key), "key-%06d", i);
    keys[i] = strdup(key);
    if (!keys[i]) { fprintf(stderr, "FAIL: strdup(%s)\n", key); rc = 2; goto cleanup; }
    nkeys = i + 1;
    void *val = (void *)(long)(i + 1); /* 值地址直接编码序号, 非真实指针但为有效指针值 */
    hash_set(hash, keys[i], val);
  }
  if (hash_size(hash) != N_ENTRIES) {
    fprintf(stderr, "FAIL: size after insert = %lu, expected %d\n",
            (unsigned long) hash_size(hash), N_ENTRIES);
    rc = 3;
    goto cleanup;
  }

  /* 2) 全量读取校验: 10 万键逐条取回一致（覆盖 khash 探测序列）*/
  for (int i = 0; i < N_ENTRIES; i++) {
    char key[32];
    snprintf(key, sizeof(key), "key-%06d", i);
    void *v = hash_get(hash, key);
    if (v != (void *)(long)(i + 1)) {
      fprintf(stderr, "FAIL: get(%s) → %p\n", key, v);
      rc = 4;
      goto cleanup;
    }
    if (!hash_has(hash, key)) {
      fprintf(stderr, "FAIL: has(%s)\n", key);
      rc = 5;
      goto cleanup;
    }
  }

  /* 3) 迭代完整性 */
  unsigned int iterated = 0;
  hash_each(hash, { iterated++; });
  if (iterated != N_ENTRIES) {
    fprintf(stderr, "FAIL: hash_each iterated %u, expected %d\n",
            iterated, N_ENTRIES);
    rc = 6;
    goto cleanup;
  }

  /* 4) 删除一半 + 清空（kh_get 按内容匹配, 栈缓冲查询即可）*/
  for (int i = 0; i < N_ENTRIES; i += 2) {
    char key[32];
    snprintf(key, sizeof(key), "key-%06d", i);
    hash_del(hash, key);
  }
  if (hash_size(hash) != N_ENTRIES / 2) {
    fprintf(stderr, "FAIL: size after del = %lu, expected %d\n",
            (unsigned long) hash_size(hash), N_ENTRIES / 2);
    rc = 7;
    goto cleanup;
  }
  hash_clear(hash);
  if (hash_size(hash) != 0) {
    fprintf(stderr, "FAIL: size after clear = %lu\n", (unsigned long) hash_size(hash));
    rc = 8;
    goto cleanup;
  }

  /* 5) 生命周期压力（防泄漏）: 键同样使用 strdup 稳定内存；
   *    khash 只保存键指针不释放键内存，因此每轮把 strdup 结果存入
   *    局部数组 rkeys，hash_free(h2) 后逐一 free，杜绝 10 万次分配泄漏。*/
  for (int round = 0; round < 100; round++) {
    hash_t *h2 = hash_new();
    if (!h2) { fprintf(stderr, "FAIL: hash_new (round %d)\n", round); rc = 9; goto cleanup; }
    char *rkeys[1000];
    int nrk = 0;
    for (int i = 0; i < 1000; i++) {
      char key[32];
      snprintf(key, sizeof(key), "r%02d-k%05d", round, i);
      rkeys[i] = strdup(key);
      if (!rkeys[i]) {
        fprintf(stderr, "FAIL: strdup (round %d, i=%d)\n", round, i);
        nrk = i;
        hash_free(h2);
        for (int j = 0; j < nrk; j++) free(rkeys[j]);
        rc = 10;
        goto cleanup;
      }
      nrk = i + 1;
      hash_set(h2, rkeys[i], (void *)(long)i);
    }
    hash_free(h2);
    for (int i = 0; i < 1000; i++) free(rkeys[i]);
  }

  /* 释放键内存（值非真实堆指针, 无需释放）*/
  printf("hash_ohos_test: OK (%d entries, %u iterated, all keys verified, del/clear/lifecycle passed)\n",
         N_ENTRIES, iterated);
  rc = 0;

cleanup:
  for (int i = 0; i < nkeys; i++) free(keys[i]);
  free(keys);
  hash_free(hash);
  return rc;
}
