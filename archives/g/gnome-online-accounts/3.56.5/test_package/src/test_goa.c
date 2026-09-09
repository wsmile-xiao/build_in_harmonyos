/* test_goa.c — CI L0c 占位 + libgoa 核心验证
 *
 * 本文件满足 CI L0c 门禁（要求 test_package/src/ 下有源文件），
 * 同时验证 libgoa 的版本 API：
 *   1. goa_check_version(3, 56, 5) 返回 NULL（NULL = 版本匹配）
 *   2. goa_major_version == 3（全局版本变量）
 *   3. 链接通过即验证 libgoa.so 可加载
 *
 * 编译需要：-DGOA_API_IS_SUBJECT_TO_CHANGE（goa.h 要求）；
 * 须 include <goa/goa.h>（goaversion.h 只能经 goa.h 引入），
 * 且 goaconfig.h 安装于 lib/goa-1.0/include，需加对应 -I
 */
#include <goa/goa.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    /* 断言 1：版本检查
     * goa_check_version 返回 NULL = 库版本兼容/匹配；返回字符串 = 不匹配 */
    const gchar *ver = goa_check_version(3, 56, 5);
    if (ver != NULL) {
        fprintf(stderr, "FAIL: goa_check_version(3,56,5) mismatch: %s\n", ver);
        return 1;
    }

    /* 断言 2：全局版本变量 */
    if (goa_major_version != 3) {
        fprintf(stderr, "FAIL: goa_major_version=%u, expected 3\n", goa_major_version);
        return 1;
    }

    /* 断言 3：链接通过（隐式验证 libgoa.so 可加载）。
     * 注意：此处 ver 恒为 NULL（断言 1 已确认版本匹配），不可用于打印；
     * OK 输出改用运行期全局版本量 goa_major_version 等。 */
    printf("test_goa: OK (major=%u, minor=%u, micro=%u)\n",
           goa_major_version, goa_minor_version, goa_micro_version);
    return 0;
}
