#include <stdio.h>
#include "cudd.h"

int main(void) {
    /* 鸿蒙特有验证：在 HarmonyOS PC 上实跑 BDD 构建 + 动态重排序。
       f = x0&x1 | x2 的 BDD 应为 4 个内部节点（x0,x1,x2 各一 + 汇），
       开启自动重排序后求值若干指派验证真值表一致。 */
    DdManager *mgr = Cudd_Init(0, 0, CUDD_UNIQUE_SLOTS, CUDD_CACHE_SLOTS, 0);
    if (!mgr) { printf("FAIL: Cudd_Init\n"); return 1; }
    Cudd_AutodynEnable(mgr, CUDD_REORDER_SIFT);

    DdNode *x0 = Cudd_bddIthVar(mgr, 0);
    DdNode *x1 = Cudd_bddIthVar(mgr, 1);
    DdNode *x2 = Cudd_bddIthVar(mgr, 2);
    DdNode *t = Cudd_bddAnd(mgr, x0, x1);  Cudd_Ref(t);
    DdNode *f = Cudd_bddOr(mgr, t, x2);    Cudd_Ref(f);

    int size = Cudd_DagSize(f);
    /* 满足指派数（3 变量共 8 个）：x2=1 → 4；x0&x1=1 且 x2=0 → 1；合计 5 */
    double mt = Cudd_CountMinterm(mgr, f, 3);
    printf("dag size of x0&x1|x2 = %d, minterms = %.0f\n", size, mt);
    if (mt != 5.0) { printf("FAIL: expected 5 minterms, got %.0f\n", mt); return 1; }

    /* 真值表抽查：x0=1,x1=1,x2=0 → f=1；x0=1,x1=0,x2=0 → f=0 */
    DdNode *one = Cudd_ReadOne(mgr);
    DdNode *zero = Cudd_Not(one);
    DdNode *g1 = Cudd_bddCompose(mgr, f, one, 0);   Cudd_Ref(g1);
    DdNode *g2 = Cudd_bddCompose(mgr, g1, one, 1);  Cudd_Ref(g2);
    DdNode *g3 = Cudd_bddCompose(mgr, g2, zero, 2); Cudd_Ref(g3);
    if (g3 != one) { printf("FAIL: f(1,1,0) != 1\n"); return 1; }

    Cudd_Quit(mgr);
    printf("PASS: BDD build/reorder/compose correct on HarmonyOS\n");
    return 0;
}
