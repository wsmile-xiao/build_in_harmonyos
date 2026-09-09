#include <telepathy-glib/telepathy-glib.h>
#include <glib.h>
#include <stdio.h>

int main(void)
{
    GValue *v = NULL;
    GQuark quark = 0;

    /* 纯函数实质调用（不依赖运行环境）：util 值构造 + 错误域注册 */
    v = tp_g_value_slice_new_boolean(TRUE);
    if (v == NULL) {
        fprintf(stderr, "FAIL: tp_g_value_slice_new_boolean returned NULL\n");
        return 1;
    }
    if (!G_VALUE_HOLDS_BOOLEAN(v) || g_value_get_boolean(v) != TRUE) {
        fprintf(stderr, "FAIL: GValue 内容不正确\n");
        return 1;
    }
    tp_g_value_slice_free(v);

    quark = tp_errors_quark();
    if (quark == 0) {
        fprintf(stderr, "FAIL: tp_errors_quark returned 0\n");
        return 1;
    }

    printf("OK: telepathy-glib link + util/error API callable\n");
    return 0;
}
