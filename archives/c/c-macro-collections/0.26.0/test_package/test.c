// test.c — c-macro-collections 0.26.0 consumer smoke test (R34: 必须实质调用被测包 API)
// 使用 cmc/list.h 宏生成一个 int 链表，插入元素、迭代读取并校验结果，
// 验证消费者可通过已安装公开头文件使用该三方库。
#include <stdio.h>
#include <stdlib.h>

#define V int
#define PFX intl
#define SNAME int_list
#define CMC_EXT_ITER
#include "cmc/list.h"
#include "cmc/utl/futils.h"

int main(void)
{
    // cpy/free 对 int 基本类型可空（上游 unt_list.h 同款用法：.cpy = NULL, .free = NULL）
    struct int_list *list = intl_new(8, &(struct int_list_fval){ .cmp = cmc_i32_cmp, .cpy = NULL, .str = cmc_i32_str, .free = NULL, .hash = cmc_i32_hash, .pri = cmc_i32_cmp });
    if (!list)
    {
        fprintf(stderr, "intl_new failed\n");
        return 1;
    }

    // 插入 1..5
    for (int i = 1; i <= 5; i++)
    {
        if (!intl_push_back(list, i))
        {
            fprintf(stderr, "intl_push_back(%d) failed\n", i);
            intl_free(list);
            return 1;
        }
    }

    size_t count = 0;
    int sum = 0;
    struct int_list_iter it = intl_iter_start(list);
    while (!intl_iter_at_end(&it))
    {
        sum += intl_iter_value(&it);
        count++;
        intl_iter_next(&it);
    }

    intl_free(list);

    if (count != 5 || sum != 15)
    {
        fprintf(stderr, "FAIL: count=%zu sum=%d (expected 5/15)\n", count, sum);
        return 1;
    }

    printf("c-macro-collections 0.26.0 consumer OK: count=%zu sum=%d\n", count, sum);
    return 0;
}
