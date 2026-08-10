/* libidn2 2.3.7 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 转换得对。IDN（国际化域名）的编解码有
 * **RFC 标准里写死的测试向量**，可以精确对账：
 *
 *   münchen        → xn--mnchen-3ya
 *   bücher         → xn--bcher-kva
 *   例え.テスト     → xn--r8jz45g.xn--zckzah
 *
 * 还验往返：A-label 解回 U-label 必须还原成原文。
 * 只调 idn2_to_ascii 看返回 0 是不够的 —— 转错了它照样返回成功。
 */
#include <idn2.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check(const char *u, const char *want_a)
{
    char *a = NULL, *back = NULL;
    int rc = idn2_to_ascii_8z(u, &a, IDN2_NONTRANSITIONAL);
    if (rc != IDN2_OK) {
        printf("FAIL to_ascii(%s) 返回 %d: %s\n", u, rc, idn2_strerror(rc));
        return 1;
    }
    if (strcmp(a, want_a) != 0) {
        printf("FAIL to_ascii(%s) = [%s]，期望 [%s]\n", u, a, want_a);
        idn2_free(a);
        return 1;
    }
    /* 往返：A-label 解回来必须与原文一致 */
    rc = idn2_to_unicode_8z8z(a, &back, 0);
    if (rc != IDN2_OK) {
        printf("FAIL to_unicode(%s) 返回 %d: %s\n", a, rc, idn2_strerror(rc));
        idn2_free(a);
        return 1;
    }
    if (strcmp(back, u) != 0) {
        printf("FAIL 往返不一致: %s → %s → %s\n", u, a, back);
        idn2_free(a); idn2_free(back);
        return 1;
    }
    idn2_free(a); idn2_free(back);
    return 0;
}

int main(void)
{
    /* ① RFC 标准测试向量，逐条精确对账 */
    if (check("münchen", "xn--mnchen-3ya")) return 1;
    if (check("bücher", "xn--bcher-kva")) return 1;
    if (check("例え.テスト", "xn--r8jz45g.xn--zckzah")) return 1;

    /* ② 纯 ASCII 域名必须原样通过，不得被改写 */
    {
        char *a = NULL;
        if (idn2_to_ascii_8z("example.com", &a, 0) != IDN2_OK) {
            printf("FAIL 纯 ASCII 域名转换失败\n");
            return 1;
        }
        if (strcmp(a, "example.com") != 0) {
            printf("FAIL 纯 ASCII 域名被改写成 [%s]\n", a);
            idn2_free(a);
            return 1;
        }
        idn2_free(a);
    }

    /* ③ 错误路径：非法输入必须返回错误码，不得崩溃也不得假装成功 */
    {
        char *a = NULL;
        /* 超长标签（>63 字节）是 RFC 明确禁止的 */
        char toolong[128];
        memset(toolong, 'a', sizeof(toolong) - 1);
        toolong[sizeof(toolong) - 1] = '\0';
        int rc = idn2_to_ascii_8z(toolong, &a, 0);
        if (rc == IDN2_OK) {
            printf("FAIL 超长标签(%zu 字节)竟然转换成功\n", strlen(toolong));
            idn2_free(a);
            return 1;
        }
    }

    printf("libidn2 OK: 3 组 RFC 测试向量精确吻合 + 往返还原 + ASCII 透传 + 错误路径；版本 %s\n",
           idn2_check_version(NULL));
    return 0;
}
