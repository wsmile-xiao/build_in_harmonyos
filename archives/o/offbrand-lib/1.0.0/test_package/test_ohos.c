/*
 * test_ohos.c — HarmonyOS 专项测试
 *
 * 在 OHOS (musl libc, clang 15, aarch64) 运行时下验证 offbrand-lib
 * 引用计数对象模型、obmap 哈希表与 obstring 正则匹配的真实行为。
 * 仅通过库导出的公开头文件与公开 API 使用该库。
 */
#include <stdio.h>
#include <stdlib.h>
#include "offbrand.h"
#include "obmap.h"
#include "obstring.h"

static int failures = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "test_ohos: FAILED: %s\n", msg);                 \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int main(void) {
    /* 1) 引用计数：ob_retain/ob_release 生命周期 */
    obstring *s = obstring_new("harmonyos");
    CHECK(s != NULL, "obstring_new failed");
    ob_retain((obj *)s);
    CHECK(ob_reference_count((obj *)s) == 2, "refcount != 2 after retain");
    ob_release((obj *)s); /* back to 1 */

    /* 2) obmap 哈希表：insert / lookup / remove / length */
    obmap *m = obmap_new();
    CHECK(m != NULL, "obmap_new failed");
    obstring *k1 = obstring_new("alpha");
    obstring *v1 = obstring_new("1");
    obstring *k2 = obstring_new("beta");
    obstring *v2 = obstring_new("2");
    obmap_insert(m, (obj *)k1, (obj *)v1);
    obmap_insert(m, (obj *)k2, (obj *)v2);
    obstring *found = (obstring *)obmap_lookup(m, (obj *)k1);
    CHECK(found != NULL, "obmap_lookup(alpha) returned NULL");
    CHECK(obstring_length(found) == 1, "obmap value length != 1");
    obmap_remove(m, (obj *)k2);
    CHECK(obmap_lookup(m, (obj *)k2) == NULL, "obmap_lookup(beta) not NULL after remove");

    /* 3) obstring 正则匹配（使用 OHOS musl regex） */
    obstring *text = obstring_new("error: code 42 at line 7");
    obstring *matched = obstring_match_regex(text, "code [0-9]+");
    CHECK(matched != NULL, "obstring_match_regex returned NULL");
    if (matched) {
        CHECK(obstring_length(matched) == 7, "regex match length != 7 (\"code 42\")");
        ob_release((obj *)matched);
    }
    /* 无匹配时上游实现返回空字符串（长度 0），而非 NULL */
    obstring *no_match = obstring_match_regex(text, "zzz[0-9]");
    CHECK(no_match != NULL && obstring_length(no_match) == 0,
          "obstring_match_regex should return empty string for 'zzz'");

    /* 清理（引用计数自动回收） */
    ob_release((obj *)s);
    ob_release((obj *)k1);
    ob_release((obj *)v1);
    ob_release((obj *)k2);
    ob_release((obj *)v2);
    ob_release((obj *)m);
    ob_release((obj *)text);

    if (failures == 0) {
        printf("test_ohos: ALL HARMONYOS TESTS PASSED\n");
        return 0;
    }
    fprintf(stderr, "test_ohos: %d FAILURE(S)\n", failures);
    return 1;
}
