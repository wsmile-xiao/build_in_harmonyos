/* test_m17n_flt.c — 消费者视角验证 libm17n-flt 公开 API：
 * m17n_init/m17n_init_flt 初始化 + mconv_list_codings 编码列表查询
 * + m17n_fini_flt/m17n_fini 生命周期（无字体/网络依赖，仅验证库可被
 * 第三方编译/链接/调用）。
 * 注意：
 *   - 不用 M17N_INIT()/M17N_FINI() 宏（依赖 merror_code/MERROR_NONE
 *     内部符号，消费者头文件展开编译失败）；
 *   - mconv_list_codings 需传合法 MSymbol** 缓冲（NULL 在 OHOS 段错误）。
 */
#include <stdio.h>
#include <m17n.h>
#include <m17n-flt.h>

#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
        return 1; \
    } \
} while (0)

int main(void)
{
    MSymbol *codings = NULL;
    int n;

    /* 1. m17n_init + m17n_init_flt：初始化库与 FLT（字体布局表）子系统 */
    m17n_init();
    m17n_init_flt();

    /* 2. mconv_list_codings：查询支持的编码列表（合法缓冲，返回个数） */
    n = mconv_list_codings(&codings);
    CHECK(n >= 0);

    /* 3. m17n_fini_flt + m17n_fini：生命周期完整 */
    m17n_fini_flt();
    m17n_fini();

    printf("test_m17n_flt: OK (m17n init/flt/list/fini roundtrip, %d codings)\n", n);
    return 0;
}
