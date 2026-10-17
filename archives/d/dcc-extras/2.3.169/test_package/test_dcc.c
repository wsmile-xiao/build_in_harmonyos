/* dcc-extras 2.3.169 — C 消费者测试（L1）
 *
 * 目的：
 *   1) 真实链接并调用上游文档所称的 "the public DCC client library"
 *      （libdcc；见 dccifd/dccif-test/Makefile.in 注释），验证包内
 *      include/ + lib/ 可用；
 *   2) OHOS 专有验证点：u_char / u_int32_t / caddr_t 三个 BSD 风格别名
 *      只有在 include/dcc_types.h 补了 <sys/types.h> 之后才能在 OHOS
 *      sysroot（musl）下编译通过。本文件直接使用这三个类型，因此
 *      “编译成功”本身就是补丁生效的断言（首个错误见
 *      reports/test-report.md §2：unknown type name 'u_char'）。
 *
 * 退出码：0 通过；1..7 对应各断言失败点。
 */
#include "dcc_defs.h"           /* dcc_types.h → <sys/types.h>（本包补丁） */
#include <netdb.h>
#include <string.h>
#include <stdio.h>

int main(void)
{
    /* 断言 1/2：真实调用 libdcc 的 API（dcc_hstrerror）。 */
    const char *s1 = dcc_hstrerror(HOST_NOT_FOUND);
    const char *s2 = dcc_hstrerror(TRY_AGAIN);
    if (s1 == NULL || s1[0] == '\0') {
        printf("FAIL: dcc_hstrerror(HOST_NOT_FOUND) 返回空\n");
        return 1;
    }
    if (s2 == NULL || s2[0] == '\0') {
        printf("FAIL: dcc_hstrerror(TRY_AGAIN) 返回空\n");
        return 2;
    }

    /* 断言 3/4/5：OHOS 专有——BSD 风格类型必须可编译可用。 */
    u_char    c8  = 0x5a;
    u_int32_t c32 = 0x01020304u;
    caddr_t   cp  = NULL;
    if (c8 != 0x5a)          { printf("FAIL: u_char 语义异常\n");        return 3; }
    if (c32 != 0x01020304u)  { printf("FAIL: u_int32_t 语义异常\n");     return 4; }
    if (cp != NULL)          { printf("FAIL: caddr_t 语义异常\n");       return 5; }

    /* 断言 6/7：编译期内置路径保持上游默认（安装根不影响运行期路径）。 */
    if (strcmp(DCC_HOMEDIR, "/var/dcc") != 0) {
        printf("FAIL: DCC_HOMEDIR=%s（期望 /var/dcc）\n", DCC_HOMEDIR);
        return 6;
    }
    if (DCC_LIBEXECDIR[0] == '\0') {
        printf("FAIL: DCC_LIBEXECDIR 为空\n");
        return 7;
    }

    printf("dcc-extras consumer test OK: dcc_hstrerror=\"%s\", "
           "DCC_HOMEDIR=%s, DCC_LIBEXECDIR=%s, "
           "u_char/u_int32_t/caddr_t 可用（OHOS 补丁生效）\n",
           s1, DCC_HOMEDIR, DCC_LIBEXECDIR);
    return 0;
}
