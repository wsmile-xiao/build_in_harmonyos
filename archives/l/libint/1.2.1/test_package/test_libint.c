/*
 * libint 1.2.1 test_package 消费者测试。
 *
 * 仅通过公开头 <libint/libint.h> 与公开 C API 使用本库（真实链接安装出的
 * libint.a），10 条断言：
 *   - libint_storage_required()：合法 (max_am, prim) 返回正内存需求；
 *   - init_libint_base()：填充 ERI kernel 分发表 build_eri（抽查
 *     00|p0、pp|pp、ff|ff 三类内核非空）；
 *   - init_libint()/free_libint()：完整生命周期，成功返回非负内存、分配
 *     int_stack/PrimQuartet，free 后置空；
 *   - 非法 max_am（>= LIBINT_MAX_AM）必须返回负值（失败路径反向证伪）。
 *
 * 任一断言失败以非零退出（ctest 据此判定整用例 Passed/Failed），
 * 并在 stderr 标注失败项。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libint/libint.h>

static int checks = 0;
static int failures = 0;

static void
ck (int cond, const char *msg)
{
    if (cond)
        printf ("ok %d - %s\n", ++checks, msg);
    else
    {
        printf ("not ok %d - %s\n", ++checks, msg);
        fprintf (stderr, "FAILED: %s\n", msg);
        failures++;
    }
}

int
main (void)
{
    printf ("libint 1.2.1 consumer test (LIBINT_MAX_AM=%d)\n", LIBINT_MAX_AM);

    /* 1. 合法 (max_am=0, max_num_prim_quartets=1) 的存储需求必须为正 */
    int req = libint_storage_required (0, 1);
    ck (req > 0, "libint_storage_required(0,1) > 0");

    /* 2. init_libint_base() 填充 ERI kernel 分发表 */
    init_libint_base ();
    ck (build_eri[0][0][1][0] != NULL, "kernel 00|p0 present after init_libint_base");
    ck (build_eri[1][1][1][1] != NULL, "kernel pp|pp present after init_libint_base");
    ck (build_eri[3][3][3][3] != NULL, "kernel ff|ff present after init_libint_base");

    /* 3. 完整生命周期：init 返回非负内存并分配 buffer，free 后置空 */
    Libint_t tints;
    memset (&tints, 0, sizeof (tints));
    int mem = init_libint (&tints, 3, 1);   /* max_am=3 合法（< LIBINT_MAX_AM=5） */
    ck (mem >= 0, "init_libint(3,1) succeeds (mem>=0)");
    ck (tints.int_stack != NULL, "int_stack allocated");
    ck (tints.PrimQuartet != NULL, "PrimQuartet allocated");
    free_libint (&tints);
    ck (tints.int_stack == NULL, "free_libint releases int_stack");
    ck (tints.PrimQuartet == NULL, "free_libint releases PrimQuartet");

    /* 4. 非法 max_am（>= LIBINT_MAX_AM）必须失败（负返回） */
    Libint_t bad;
    memset (&bad, 0, sizeof (bad));
    int r = init_libint (&bad, LIBINT_MAX_AM, 1);
    ck (r < 0, "init_libint(max_am >= LIBINT_MAX_AM) fails (r<0)");
    free_libint (&bad);

    printf ("RESULT: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
