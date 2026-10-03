/* Consumer test for vte 0.84.1 (gtk4 flavour, libvte-2.91-gtk4).
 *
 * Exercises the non-widget core API that needs no display server and
 * no PTY: version macros, feature string, and the pty-free attribute
 * API. Mirrors the 0.74.2 consumer test's no-GDK path but links the
 * gtk4 flavour library.
 */
#include <stdio.h>
#include <string.h>

#include <vte/vte.h>

int main(int argc, char *argv[])
{
    /* Test 1: version macros */
    printf("VTE version: %d.%d.%d (expect 0.84.1)\n",
           VTE_MAJOR_VERSION, VTE_MINOR_VERSION, VTE_MICRO_VERSION);
    if (VTE_MAJOR_VERSION != 0 || VTE_MINOR_VERSION != 84 || VTE_MICRO_VERSION != 1) {
        fprintf(stderr, "FAIL: version macros mismatch\n");
        return 1;
    }

    /* Test 2: feature string (runtime, no GDK init needed) */
    const char *features = vte_get_features();
    if (!features) {
        fprintf(stderr, "FAIL: vte_get_features() returned NULL\n");
        return 1;
    }
    printf("features: %s\n", features);

    /* Test 3: pty-free attribute helpers — VteRegex is PCRE2-backed
     * and needs no windowing system. */
    VteRegex *regex = vte_regex_new_for_match("foo(bar)?", -1, 0, NULL);
    if (!regex) {
        fprintf(stderr, "FAIL: vte_regex_new_for_match returned NULL\n");
        return 1;
    }
    /* substitute path exercises the PCRE2 replace engine */
    char *subst = vte_regex_substitute(regex, "foobar", "X", 0, NULL);
    if (!subst) {
        fprintf(stderr, "FAIL: vte_regex_substitute returned NULL\n");
        return 1;
    }
    printf("substitute(foobar -> X): %s (expect X)\n", subst);
    if (strcmp(subst, "X") != 0) {
        fprintf(stderr, "FAIL: substitute result mismatch\n");
        g_free(subst);
        return 1;
    }
    g_free(subst);
    vte_regex_unref(regex);

    /* Test 4: GDK headless init attempt; fall back to symbol-only
     * verification if the offscreen backend cannot start (no display
     * in the build sandbox). */
    g_setenv("GDK_BACKEND", "broadway", TRUE);
    /* GTK4: gtk_init_check() takes no arguments (unlike GTK3's (&argc, &argv)) */
    if (!gtk_init_check()) {
        printf("gtk_init_check failed (headless path); core symbols verified\n");
        printf("test vte 0.84.1 (no-GDK path): OK — features=%s\n", features);
        return 0;
    }

    /* Full widget path when a display is available */
    GtkWidget *terminal = vte_terminal_new();
    if (!terminal) {
        fprintf(stderr, "FAIL: vte_terminal_new() returned NULL\n");
        return 1;
    }
    GType t = vte_terminal_get_type();
    if (t == 0) {
        fprintf(stderr, "FAIL: vte_terminal_get_type() == 0\n");
        return 1;
    }
    g_object_unref(terminal);
    printf("test vte 0.84.1: OK — terminal created, type=%lu, features=%s\n",
           (unsigned long)t, features);
    return 0;
}
