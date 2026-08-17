/* 真实断言：用 PPL 的 C 接口从**约束**造一个单位正方形，再让它反算出**顶点**。
 *
 * 为什么要这样测：PPL 的核心能力就是「约束表示 ↔ 生成元表示」的双描述转换
 * （Chernikova 算法）。能 include、能链接、能 ppl_initialize() 都不说明这条
 * 转换是对的 —— 而它一旦因为 GMP 没接对而算错，上层（sage 的 Polyhedron）
 * 得到的顶点数就是错的，且不会报错。
 *
 * 断言：
 *   ① 0≤x≤1, 0≤y≤1 转出的生成元恰好 4 个（正方形的 4 个顶点）
 *   ② 每个生成元的类型都是 PPL_GENERATOR_TYPE_POINT（不该出现射线/直线）
 *   ③ 该多面体是有界的（is_bounded）
 */
#include <ppl_c.h>

#include <gmp.h>
#include <stdio.h>
#include <stdlib.h>

/* 往 le 里加一项 coeff * x_var */
static void add_term(ppl_Linear_Expression_t le, ppl_dimension_type var, long coeff)
{
    mpz_t z;
    ppl_Coefficient_t c;
    mpz_init_set_si(z, coeff);
    ppl_new_Coefficient_from_mpz_t(&c, z);
    ppl_Linear_Expression_add_to_coefficient(le, var, c);
    ppl_delete_Coefficient(c);
    mpz_clear(z);
}

/* 往 le 里加常数项 */
static void add_const(ppl_Linear_Expression_t le, long v)
{
    mpz_t z;
    ppl_Coefficient_t c;
    mpz_init_set_si(z, v);
    ppl_new_Coefficient_from_mpz_t(&c, z);
    ppl_Linear_Expression_add_to_inhomogeneous(le, c);
    ppl_delete_Coefficient(c);
    mpz_clear(z);
}

/* 加一条 `coeff*x_var + konst >= 0` 的约束 */
static void add_ge0(ppl_Polyhedron_t ph, ppl_dimension_type var, long coeff, long konst)
{
    ppl_Linear_Expression_t le;
    ppl_Constraint_t c;
    ppl_new_Linear_Expression(&le);
    add_term(le, var, coeff);
    add_const(le, konst);
    ppl_new_Constraint(&c, le, PPL_CONSTRAINT_TYPE_GREATER_OR_EQUAL);
    ppl_Polyhedron_add_constraint(ph, c);
    ppl_delete_Constraint(c);
    ppl_delete_Linear_Expression(le);
}

int main(void)
{
    ppl_Polyhedron_t ph;
    ppl_const_Generator_System_t gs;
    ppl_Generator_System_const_iterator_t it, end;
    int npoints = 0, nother = 0, bad = 0, bounded;

    if (ppl_initialize() < 0) {
        fprintf(stderr, "ppl: ppl_initialize 失败\n");
        return 1;
    }

    /* 2 维全空间，再加 4 条约束围成单位正方形 */
    ppl_new_C_Polyhedron_from_space_dimension(&ph, 2, 0);
    add_ge0(ph, 0, 1, 0);    /*  x     >= 0 */
    add_ge0(ph, 0, -1, 1);   /* -x + 1 >= 0 → x <= 1 */
    add_ge0(ph, 1, 1, 0);    /*  y     >= 0 */
    add_ge0(ph, 1, -1, 1);   /* -y + 1 >= 0 → y <= 1 */

    /* ③ 有界 */
    bounded = ppl_Polyhedron_is_bounded(ph);
    if (bounded != 1) {
        fprintf(stderr, "ppl: 单位正方形应当有界，is_bounded 返回 %d\n", bounded);
        bad = 1;
    } else {
        printf("ppl: is_bounded = 1 通过\n");
    }

    /* ①② 双描述转换：数生成元 */
    ppl_Polyhedron_get_generators(ph, &gs);
    ppl_new_Generator_System_const_iterator(&it);
    ppl_new_Generator_System_const_iterator(&end);
    ppl_Generator_System_begin(gs, it);
    ppl_Generator_System_end(gs, end);
    while (!ppl_Generator_System_const_iterator_equal_test(it, end)) {
        ppl_const_Generator_t g;
        ppl_Generator_System_const_iterator_dereference(it, &g);
        if (ppl_Generator_type(g) == PPL_GENERATOR_TYPE_POINT)
            ++npoints;
        else
            ++nother;
        ppl_Generator_System_const_iterator_increment(it);
    }
    ppl_delete_Generator_System_const_iterator(it);
    ppl_delete_Generator_System_const_iterator(end);
    ppl_delete_Polyhedron(ph);

    if (npoints != 4) {
        fprintf(stderr, "ppl: 单位正方形的顶点数应为 4，实得 %d\n", npoints);
        bad = 1;
    } else {
        printf("ppl: 顶点数 = 4 通过（约束→生成元的双描述转换正确）\n");
    }
    if (nother != 0) {
        fprintf(stderr, "ppl: 有界多面体不该有射线/直线，实得 %d 个\n", nother);
        bad = 1;
    } else {
        printf("ppl: 无射线/直线 通过\n");
    }

    ppl_finalize();
    return bad;
}
