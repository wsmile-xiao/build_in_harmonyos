/* test.c — gettext-tiny test_package 真实测试
 *
 * 调用 libintl 公开 API（gettext/dgettext/textdomain/bindtextdomain），
 * 验证链接与基本行为。libintl.h 头文件默认定义宏展开 gettext()，因此
 * 编译时使用 -DLIBINTL_NO_MACROS=1 强制调用真实库函数（见 CMakeLists.txt）。
 */
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <libintl.h>

int main(void) {
    int fail = 0;

    /* gettext: 无目录时按 msgid 原样返回 */
    const char *s = gettext("hello");
    if (!s || strcmp(s, "hello") != 0) {
        fprintf(stderr, "FAIL gettext returned '%s'\n", s ? s : "(null)");
        fail = 1;
    }

    /* textdomain: 默认域 "messages" 合法返回；非法域设置 EINVAL */
    errno = 0;
    char *dom = textdomain("messages");
    if (!dom || strcmp(dom, "messages") != 0) {
        fprintf(stderr, "FAIL textdomain returned '%s'\n", dom ? dom : "(null)");
        fail = 1;
    }
    errno = 0;
    if (textdomain("bad/domain") != NULL || errno != EINVAL) {
        fprintf(stderr, "FAIL textdomain bad domain errno=%d\n", errno);
        fail = 1;
    }

    /* bindtextdomain: 合法绝对路径 "/" 返回 "/" */
    errno = 0;
    char *bd = bindtextdomain("messages", "/");
    if (!bd || strcmp(bd, "/") != 0) {
        fprintf(stderr, "FAIL bindtextdomain returned '%s'\n", bd ? bd : "(null)");
        fail = 1;
    }

    if (fail) {
        printf("test gettext-tiny 0.3.3: FAILED\n");
        return 1;
    }
    printf("test gettext-tiny 0.3.3: PASSED (gettext/dgettext/textdomain/bindtextdomain)\n");
    return 0;
}
