#include <stdio.h>
#include <glib.h>
#include <ayatana/common/utils.h>

int main(void) {
    int rc = 0;

    /* 场景 1：无桌面环境变量 → is_lomiri() 应为 FALSE */
    g_unsetenv("XDG_CURRENT_DESKTOP");
    g_unsetenv("XDG_SESSION_DESKTOP");
    g_unsetenv("DESKTOP_SESSION");
    if (ayatana_common_utils_is_lomiri()) {
        fprintf(stderr, "FAIL: is_lomiri() expected FALSE with no desktop env\n");
        rc = 1;
    }

    /* 场景 2：XDG_CURRENT_DESKTOP=Lomiri → is_lomiri() 应为 TRUE */
    g_setenv("XDG_CURRENT_DESKTOP", "Lomiri", TRUE);
    if (!ayatana_common_utils_is_lomiri()) {
        fprintf(stderr, "FAIL: is_lomiri() expected TRUE with XDG_CURRENT_DESKTOP=Lomiri\n");
        rc = 1;
    }

    /* 场景 3：XDG_CURRENT_DESKTOP=GNOME → is_lomiri() 应为 FALSE */
    g_setenv("XDG_CURRENT_DESKTOP", "GNOME", TRUE);
    if (ayatana_common_utils_is_lomiri()) {
        fprintf(stderr, "FAIL: is_lomiri() expected FALSE with XDG_CURRENT_DESKTOP=GNOME\n");
        rc = 1;
    }

    if (rc == 0)
        printf("OK: libayatana-common test passed (is_lomiri 3 scenarios)\n");
    return rc;
}
