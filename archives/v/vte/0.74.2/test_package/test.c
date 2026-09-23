#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* vte public headers */
#include <vte/vte.h>

int main(int argc, char *argv[])
{
    /* Initialize GTK with a virtual backend so the test runs headless.
       Set GDK_BACKEND before gtk_init so gdk_display_manager picks it up. */
    g_setenv("GDK_BACKEND", "broadway", TRUE);
    if (!gtk_init_check(&argc, &argv)) {
        /* If GTK still can't init (e.g. no broadway backend), fall back to
           testing only the non-widget vte symbols that don't need GDK. */
        fprintf(stderr, "gtk_init_check failed; testing vte symbols only\n");
        /* VTE_MAJOR/MINOR/MICRO_VERSION are compile-time constants;
           vte_get_features() is a runtime call that doesn't need GDK. */
        const char *features = vte_get_features();
        if (!features) {
            fprintf(stderr, "vte_get_features() returned NULL\n");
            return 1;
        }
        printf("test vte 0.74.2 (no-GDK path): features=%s\n", features);
        return 0;
    }

    /* Test 1: Create a VteTerminal widget — core vte API */
    GtkWidget *terminal = vte_terminal_new();
    if (!terminal) {
        fprintf(stderr, "vte_terminal_new() returned NULL\n");
        return 1;
    }

    /* Test 2: Check the VTE API version via type registration */
    GType terminal_type = vte_terminal_get_type();
    if (terminal_type == 0) {
        fprintf(stderr, "vte_terminal_get_type() returned 0\n");
        g_object_unref(terminal);
        return 1;
    }

    /* Test 3: Verify vte_get_features() returns a non-NULL string */
    const char *features = vte_get_features();
    if (!features) {
        fprintf(stderr, "vte_get_features() returned NULL\n");
        g_object_unref(terminal);
        return 1;
    }

    /* Clean up */
    g_object_unref(terminal);

    printf("test vte 0.74.2: OK — terminal created, type=%lu, features=%s\n",
           (unsigned long)terminal_type, features);
    return 0;
}
