/*
 * test.c — genders 1.27-3 消费者断言（16 项）
 *
 * 链接安装的 libgenders（静态），对真实 genders 数据库做 API 行为断言。
 * 夹具由本程序写入自身 CWD（test_genders_db.tmp），供 test() 随后的
 * `nodeattr -f test_genders_db.tmp -l` 消费断言复用。
 *
 * 注意 genders_query 族 API 契约：输出数组必须是 genders_nodelist_create
 * 预分配的「缓冲区数组」（每个槽位指向可写缓冲），库内部对 list[index] 做
 * strcpy —— 裸 char *[]（未初始化槽位）会 strcpy 到垃圾指针段错误。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <genders.h>

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        checks++;                                               \
        if (cond) {                                             \
            printf("PASS: %s\n", (msg));                        \
            fflush(stdout);                                     \
        } else {                                                \
            fprintf(stderr, "FAIL: %s\n", (msg));               \
            failures++;                                         \
        }                                                       \
    } while (0)

static const char *fixture = "test_genders_db.tmp";

int main(void)
{
    FILE *f = fopen(fixture, "w");
    if (!f) {
        fprintf(stderr, "cannot write fixture %s\n", fixture);
        return 2;
    }
    fputs("node1 attr1,attr2=v2\n"
          "node2 attr1\n"
          "node3 attr1,attr2=v2\n", f);
    fclose(f);

    genders_t h = genders_handle_create();
    CHECK(h != NULL, "genders_handle_create returns handle");

    CHECK(genders_load_data(h, fixture) == 0, "genders_load_data loads fixture");
    CHECK(genders_errnum(h) == 0, "genders_errnum == 0 after successful load");

    CHECK(genders_getnumnodes(h) == 3, "genders_getnumnodes == 3");
    CHECK(genders_getnumattrs(h) == 2, "genders_getnumattrs == 2");
    CHECK(genders_getmaxattrs(h) == 2, "genders_getmaxattrs == 2");

    CHECK(genders_isnode(h, "node2") == 1, "genders_isnode(node2) == 1");
    CHECK(genders_isnode(h, "nodeX") == 0, "genders_isnode(nodeX) == 0");
    CHECK(genders_isattr(h, "attr1") == 1, "genders_isattr(attr1) == 1");
    CHECK(genders_isattrval(h, "attr2", "v2") == 1, "genders_isattrval(attr2,v2) == 1");

    /* genders_query 输出数组 = nodelist_create 预分配缓冲区数组（见文件头注） */
    char **nodes = NULL;
    int nlist_len = genders_nodelist_create(h, &nodes);
    CHECK(nlist_len == 3, "genders_nodelist_create allocates 3 slots");

    int n = genders_query(h, nodes, nlist_len, "attr1");
    CHECK(n == 3, "genders_query(attr1) matches 3 nodes");
    n = genders_query(h, nodes, nlist_len, "attr2=v2");
    CHECK(n == 2, "genders_query(attr2=v2) matches 2 nodes");

    CHECK(genders_nodelist_destroy(h, nodes) == 0, "genders_nodelist_destroy succeeds");

    CHECK(genders_testquery(h, "node1", "attr2=v2") == 1,
          "genders_testquery(node1, attr2=v2) == 1");

    CHECK(genders_handle_destroy(h) == 0, "genders_handle_destroy succeeds");

    printf("test_genders: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
