#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ctl 是纯头文件模板容器库：消费者通过 `#define P` + `#define T <type>`
 * 后 `#include <vec.h>` 实例化容器（公开头文件 + 公开 API）。
 * str.h 是非模板的固定字符串类型，包含前不得定义 T（否则报
 * "Template type T defined for <str.h>"）。 */

#define P
#define T int
#include <vec.h>

#undef T
#undef P
#include <str.h>

int
int_equal(int* a, int* b)
{ return *a == *b; }

int
main(void)
{
    /* vec_int：公开 API push_back / at / size / foreach 迭代 */
    vec_int v = vec_int_init();
    if (!vec_int_empty(&v))
        return 1;
    vec_int_push_back(&v, 10);
    vec_int_push_back(&v, 20);
    vec_int_push_back(&v, 30);
    if (v.size != 3)
        return 2;
    if (*vec_int_at(&v, 0) != 10 || *vec_int_at(&v, 2) != 30)
        return 3;
    int sum = 0;
    foreach(vec_int, &v, it)
        sum += *it.ref;
    if (sum != 60)
        return 4;
    vec_int_free(&v);

    /* str：公开 API 追加 / 取值 / 迭代（str_init 参数须非 NULL，同上游用例） */
    str s = str_init("");
    str_push_back(&s, 'a');
    str_push_back(&s, 'b');
    str_push_back(&s, 'c');
    if (s.size != 3)
        return 5;
    if (*str_at(&s, 0) != 'a' || *str_at(&s, 2) != 'c')
        return 6;
    str_free(&s);

    printf("test ctl 3.0: PASS (vec+str public API)\n");
    return 0;
}
