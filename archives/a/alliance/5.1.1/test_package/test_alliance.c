/* test_alliance.c — Alliance Mut 核心库消费者测试（鸿蒙特有 test_package） */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mut.h>

/* Release 下 assert() 会被 -DNDEBUG 移除，用自研 CHECK 宏（Debug/Release 均生效） */
#define CHECK(expr)                                                        \
    do {                                                                   \
        if (!(expr)) {                                                     \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
            exit(1);                                                       \
        }                                                                  \
    } while (0)

int main(void)
{
    /* 1. chain_list 基本操作：addchain 构造双节点链 */
    chain_list *ch = NULL;
    ch = addchain(NULL, "hello");
    CHECK(ch != NULL);
    ch = addchain(ch, "alliance");
    CHECK(ch != NULL);

    /* 2. struct chain 字段（NEXT/DATA）检索 */
    CHECK(ch->DATA != NULL);
    CHECK(strcmp((const char *)ch->DATA, "alliance") == 0);    /* 链头 DATA */
    CHECK(ch->NEXT != NULL);                                   /* 存在后续节点 */
    CHECK(strcmp((const char *)ch->NEXT->DATA, "hello") == 0); /* 链尾 DATA */

    /* 3. mbkalloc / mbkfree 基础内存分配与释放 */
    void *p = mbkalloc(1024);
    CHECK(p != NULL);
    memset(p, 0x5a, 1024);
    mbkfree(p);

    printf("alliance test_package OK (Mut core API)\n");
    return 0;
}
