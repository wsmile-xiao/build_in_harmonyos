#include <glib.h>
#include <stdio.h>

int main(void) {
    /* Test glib basic functions */
    gchar *str = g_strdup("hello");
    g_free(str);

    /* Test glib version */
    printf("glib version: %d.%d.%d\n",
           GLIB_MAJOR_VERSION,
           GLIB_MINOR_VERSION,
           GLIB_MICRO_VERSION);

    printf("glib test: PASS\n");
    return 0;
}
