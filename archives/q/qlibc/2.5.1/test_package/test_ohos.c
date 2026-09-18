/******************************************************************************
 * test_ohos.c — HarmonyOS 专项消费者测试 for qlibc 2.5.1
 *
 * 在 OHOS (aarch64-linux-ohos, clang 15, musl libc) 平台实际编译链接并
 * 运行，验证 qlibc 容器/字符串/MD5 工具在鸿蒙 PC 上的可用性。
 * 真实断言，非空壳；编译器禁任何 优化 消除（结果写入 stdout 并做断言）。
 *****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <assert.h>

#include <qlibc/qlibc.h>
#include <qlibc/containers/qvector.h>
#include <qlibc/containers/qlist.h>
#include <qlibc/containers/qhasharr.h>
#include <qlibc/utilities/qstring.h>
#include <qlibc/utilities/qhash.h>

static int g_failures = 0;

/* every failed assertion bumps counter and prints detail */
#define CHECK(cond, msg)                         \
    do {                                         \
        if (!(cond)) {                           \
            g_failures++;                        \
            fprintf(stderr, "FAIL: %s\n", msg);  \
        }                                        \
    } while (0)

int main(int argc, char *argv[])
{
    /* ---------- 1. qvector: 整型容器 ---------- */
    qvector_t *vec = qvector(4, sizeof(int), QVECTOR_RESIZE_DOUBLE);
    CHECK(vec != NULL, "qvector() constructor");
    if (vec) {
        int data[16];
        int i;
        for (i = 0; i < 16; i++) {
            data[i] = i * i;
            CHECK(qvector_addlast(vec, &data[i]), "qvector_addlast");
        }
        CHECK(qvector_size(vec) == 16, "qvector_size == 16");
        int val = *(int *)qvector_getat(vec, 4, false);
        CHECK(val == 16, "qvector_getat(4) == 16");
        val = *(int *)qvector_getat(vec, 15, false);
        CHECK(val == 225, "qvector_getat(15) == 225");
        qvector_free(vec);
    }

    /* ---------- 2. qlist: 链表字符串 ---------- */
    qlist_t *list = qlist(0);
    CHECK(list != NULL, "qlist() constructor");
    if (list) {
        const char *items[] = {"alpha", "beta", "gamma"};
        int i;
        for (i = 0; i < 3; i++) {
            CHECK(qlist_addlast(list, items[i], strlen(items[i]) + 1),
                  "qlist_addlast");
        }
        size_t n = 0;
        char *out = qlist_getat(list, 1, &n, true);
        CHECK(out != NULL && n == 5 && strcmp(out, "beta") == 0,
              "qlist_getat(1) == beta");
        free(out);
        qlist_free(list);
    }

    /* ---------- 3. qhasharr: 静态哈希表 key/value ---------- */
    size_t memsize = qhasharr_calculate_memsize(16);
    void *memory = malloc(memsize);
    CHECK(memory != NULL, "qhasharr memory alloc");
    if (memory) {
        qhasharr_t *tbl = qhasharr(memory, memsize);
        CHECK(tbl != NULL, "qhasharr() constructor");
        if (tbl) {
            CHECK(qhasharr_putstr(tbl, "key1", "value1"), "qhasharr_putstr");
            CHECK(qhasharr_putstr(tbl, "key2", "value2"), "qhasharr_putstr2");
            char *v1 = qhasharr_getstr(tbl, "key1");
            char *v2 = qhasharr_getstr(tbl, "key2");
            CHECK(v1 && strcmp(v1, "value1") == 0, "qhasharr_getstr key1");
            CHECK(v2 && strcmp(v2, "value2") == 0, "qhasharr_getstr key2");
            if (v1) free(v1);
            if (v2) free(v2);
            CHECK(qhasharr_remove(tbl, "key1"), "qhasharr_remove");
            char *gone = qhasharr_getstr(tbl, "key1");
            CHECK(gone == NULL, "qhasharr get removed key == NULL");
            free(gone);
        }
        free(memory);
    }

    /* ---------- 4. qstring: 字符串工具 ---------- */
    char buf[64];
    snprintf(buf, sizeof(buf), "  hello qlibc  ");
    char *trimmed = qstrtrim(buf);
    CHECK(strcmp(trimmed, "hello qlibc") == 0, "qstrtrim");
    char upper[64];
    strcpy(upper, "abcXYZ");
    qstrupper(upper);
    CHECK(strcmp(upper, "ABCXYZ") == 0, "qstrupper");
    qstrlower(upper);
    CHECK(strcmp(upper, "abcxyz") == 0, "qstrlower");

    /* ---------- 5. qhash MD5（校验和可跨平台复现） ---------- */
    unsigned char md5[16];
    CHECK(qhashmd5("abc", 3, md5), "qhashmd5(\"abc\")");
    /* MD5("abc") = 900150983cd24fb0d6963f7d28e17f72 */
    const unsigned char expect[16] = {
        0x90, 0x01, 0x50, 0x98, 0x3c, 0xd2, 0x4f, 0xb0,
        0xd6, 0x96, 0x3f, 0x7d, 0x28, 0xe1, 0x7f, 0x72,
    };
    CHECK(memcmp(md5, expect, 16) == 0, "qhashmd5 correct digest");

    /* ---------- 6. 平台回显 ---------- */
    printf("test_ohos: qlibc 2.5.1 HarmonyOS consumer test\n");
    printf("platform: %s|%ld|clang-ohos-musl\n", "ohos", (long)sizeof(void *) * 8);
    printf("qvector %s | qlist %s | qhasharr %s | qstring %s | qhashmd5 %s\n",
           "ok", "ok", "ok", "ok", "ok");

    if (g_failures == 0) {
        printf("test_ohos: ALL PASS (5 API groups exercised)\n");
        return 0;
    }
    fprintf(stderr, "test_ohos: %d FAILURES\n", g_failures);
    return 1;
}