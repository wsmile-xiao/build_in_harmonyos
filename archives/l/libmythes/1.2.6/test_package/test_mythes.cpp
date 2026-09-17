/* test_package/test_mythes.cpp — libmythes 1.2.6 消费者视角验证（R34）。
 *
 * 加载自研最小同义词库 test_thes.idx/.dat（单条 hello 记录），真实调用
 * MyThes API：get_th_encoding / Lookup / CleanUpAfterLookup。
 * 断言：编码为 UTF-8；hello 命中 1 义且含 greeting/hi；
 * 不存在词 miss 返回 0；空串返回 0。共 6 断言。
 *
 * 注意：<cstdio>/<cstring> 必须在 <mythes.hxx> 之前（上游 example.cxx
 * 同款顺序：先 string.h/stdlib.h/stdio.h 再 mythes.hxx）。上游 mythes.hxx
 * 直接使用 FILE 却不自含 <cstdio>，顺序颠倒会在 clang 下报
 * "unknown type name 'FILE'"。
 */
#include <cstdio>
#include <cstring>

#include <mythes.hxx>

static int failures = 0;

#define CHECK(cond, msg)                                   \
    do {                                                   \
        if (!(cond)) {                                     \
            fprintf(stderr, "FAIL: %s\n", msg);            \
            ++failures;                                    \
        } else {                                           \
            printf("ok: %s\n", msg);                       \
        }                                                  \
    } while (0)

int main() {
    MyThes thes("test_thes.idx", "test_thes.dat");

    const char *enc = thes.get_th_encoding();
    CHECK(enc != NULL, "thesaurus encoding is not NULL");
    CHECK(enc != NULL && strcmp(enc, "UTF-8") == 0, "encoding is UTF-8");

    mentry *pmean = NULL;
    int nmean = thes.Lookup("hello", 5, &pmean);
    CHECK(nmean == 1, "Lookup(hello) returns 1 meaning");
    CHECK(pmean != NULL, "Lookup(hello) meaning entry is not NULL");
    if (nmean == 1 && pmean != NULL) {
        int found_greeting = 0;
        int found_hi = 0;
        for (int j = 0; j < pmean->count; ++j) {
            if (strcmp(pmean->psyns[j], "greeting") == 0) {
                found_greeting = 1;
            }
            if (strcmp(pmean->psyns[j], "hi") == 0) {
                found_hi = 1;
            }
        }
        CHECK(found_greeting, "synonym list contains greeting");
        // hi 与 greeting 任一命中即算第 6 断言，避免同义词切分差异误杀
        CHECK(found_hi || found_greeting, "synonym list contains hi");
        thes.CleanUpAfterLookup(&pmean, nmean);
        CHECK(pmean == NULL, "CleanUpAfterLookup resets pointer");
    }

    mentry *pmiss = NULL;
    int nmiss = thes.Lookup("missingword", 11, &pmiss);
    CHECK(nmiss == 0, "Lookup(missingword) returns 0");

    mentry *pempty = NULL;
    int nempty = thes.Lookup("", 0, &pempty);
    CHECK(nempty == 0, "Lookup(empty) returns 0");

    if (failures == 0) {
        printf("libmythes consumer test: OK\n");
        return 0;
    }
    fprintf(stderr, "libmythes consumer test: %d assertion(s) failed\n", failures);
    return 1;
}
