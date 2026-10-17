#include <stdio.h>
#include <glib.h>
#include <ayatana/common/utils.h>

/* Exercise real ayatana-common API (R34: no empty-shell tests). */
int main(void) {
    /* Desktop-session detection reads the environment: with nothing set,
     * none of the desktop/session predicates should fire. */
    g_unsetenv("XDG_CURRENT_DESKTOP");
    g_unsetenv("XDG_SESSION_DESKTOP");
    g_unsetenv("DESKTOP_SESSION");
    if (ayatana_common_utils_is_gnome()) {
        fprintf(stderr, "FAIL: is_gnome() should be FALSE with no desktop set\n");
        return 1;
    }

    /* Set XDG_CURRENT_DESKTOP=GNOME -> is_gnome() must return TRUE. */
    g_setenv("XDG_CURRENT_DESKTOP", "GNOME", TRUE);
    if (!ayatana_common_utils_is_gnome()) {
        fprintf(stderr, "FAIL: is_gnome() should be TRUE with XDG_CURRENT_DESKTOP=GNOME\n");
        return 2;
    }
    if (ayatana_common_utils_is_unity()) {
        fprintf(stderr, "FAIL: is_unity() should be FALSE with XDG_CURRENT_DESKTOP=GNOME\n");
        return 3;
    }

    /* have_program() must find a shell that exists. */
    if (!ayatana_common_utils_have_program("sh")) {
        fprintf(stderr, "FAIL: have_program(sh) returned FALSE\n");
        return 4;
    }

    g_unsetenv("XDG_CURRENT_DESKTOP");
    printf("ayatana-common 0.9.11: API smoke test OK\n");
    return 0;
}
