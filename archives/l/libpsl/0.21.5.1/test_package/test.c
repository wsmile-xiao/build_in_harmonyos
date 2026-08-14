/* libpsl 0.21.5 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 判得对。公共后缀列表（PSL）的判定有
 * **唯一正确答案**，可以精确对账：
 *
 *   com            是公共后缀        example.com     不是
 *   co.uk          是公共后缀        bar.co.uk       不是
 *   www.example.com 的可注册域是 example.com
 *   a.b.bar.co.uk   的可注册域是 bar.co.uk（两级后缀，最容易出错的一类）
 *
 * 用内置 PSL 数据（psl_builtin）——这同时验证了**数据真的编进了包**，
 * 而不只是代码能跑。数据没进去的话，所有查询都会给出错误答案而非崩溃，
 * 只看「没崩」是发现不了的。
 */
#include <libpsl.h>

#include <stdio.h>
#include <string.h>

static int expect_suffix(const psl_ctx_t *psl, const char *d, int want)
{
    const int got = psl_is_public_suffix(psl, d) ? 1 : 0;
    if (got != want) {
        printf("FAIL psl_is_public_suffix(%s) = %d，期望 %d\n", d, got, want);
        return 1;
    }
    return 0;
}

static int expect_regdom(const psl_ctx_t *psl, const char *d, const char *want)
{
    const char *got = psl_registrable_domain(psl, d);
    if (!got || strcmp(got, want) != 0) {
        printf("FAIL psl_registrable_domain(%s) = [%s]，期望 [%s]\n",
               d, got ? got : "(null)", want);
        return 1;
    }
    return 0;
}

int main(void)
{
    const psl_ctx_t *psl = psl_builtin();
    if (!psl) {
        printf("FAIL psl_builtin() 为空 —— 内置 PSL 数据没编进包\n");
        return 1;
    }
    if (psl_builtin_outdated()) {
        printf("注意：内置 PSL 数据已过期（不影响本测试的判定）\n");
    }

    /* ① 单级公共后缀 */
    if (expect_suffix(psl, "com", 1)) return 1;
    if (expect_suffix(psl, "example.com", 0)) return 1;

    /* ② 多级公共后缀 —— 最容易出错的一类 */
    if (expect_suffix(psl, "co.uk", 1)) return 1;
    if (expect_suffix(psl, "bar.co.uk", 0)) return 1;

    /* ③ 可注册域提取 */
    if (expect_regdom(psl, "www.example.com", "example.com")) return 1;
    if (expect_regdom(psl, "a.b.bar.co.uk", "bar.co.uk")) return 1;

    /* ④ 公共后缀本身没有可注册域，必须返回 NULL 而不是瞎给一个 */
    {
        const char *r = psl_registrable_domain(psl, "com");
        if (r != NULL) {
            printf("FAIL psl_registrable_domain(\"com\") = [%s]，公共后缀本身应返回 NULL\n", r);
            return 1;
        }
    }

    /* ⑤ 内置数据规模合理 —— 数据被截断的话前面的断言仍可能侥幸通过 */
    {
        const int n = psl_suffix_count(psl);
        if (n < 1000) {
            printf("FAIL 内置 PSL 只有 %d 条后缀，明显被截断（正常应有数千条）\n", n);
            return 1;
        }
        printf("libpsl OK: 单级/多级公共后缀判定 + 可注册域提取 + 公共后缀无注册域 "
               "+ 内置数据 %d 条，共 5 组；版本 %s\n", n, psl_get_version());
    }
    return 0;
}
