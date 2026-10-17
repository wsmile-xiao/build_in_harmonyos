/* 真实断言：用 symmetrica 自己的对象系统算一个可手算的组合学量。
 *
 * symmetrica 的 API 是「一切皆 OP 对象」：callocobject() 拿对象、M_I_I 塞整数、
 * S_I_I 取整数；用前必须 anfang()（初始化全局表），用完 ende()。
 *
 * 断言 1：10! = 3628800（手算可验）
 * 断言 2：0! = 1（边界，顺带证明 fakul 不是碰巧返回了输入）
 *
 * 为什么不用 dlopen 探针：那只能证明 .so 装进包里了，证明不了
 * 「-DALLTRUE 有没有生效」这类静默能力缺失 —— 而这正是本包最容易出的错。
 */
#include <stdio.h>
#include <symmetrica.h>

static int check_fakul(int n, long expect)
{
    OP a = callocobject();
    OP b = callocobject();
    M_I_I(n, a);
    fakul(a, b);
    long got = (long) S_I_I(b);
    freeall(a);
    freeall(b);
    if (got != expect) {
        fprintf(stderr, "symmetrica: %d! 应为 %ld，实得 %ld\n", n, expect, got);
        return 1;
    }
    printf("symmetrica: %d! = %ld 通过\n", n, got);
    return 0;
}

int main(void)
{
    int bad = 0;
    anfang();
    bad += check_fakul(10, 3628800L);
    bad += check_fakul(0, 1L);
    ende();
    return bad ? 1 : 0;
}
