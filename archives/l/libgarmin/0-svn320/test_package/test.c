/* test_package/test.c — consumer test for libgarmin (HarmonyOS PC).
 *
 * Substantively exercises the installed static library (R34): links it and
 * calls the real public API gar_init()/gar_free().  gar_init() returns a
 * freshly calloc'd context (it does not dereference the (NULL) IMG path),
 * proving the library links and its entry points are callable on
 * aarch64-linux-ohos.  mylog() matches libgarmin's log_fn prototype exactly.
 */
#include "libgarmin.h"

#include <stdio.h>

/* Swallow log output — must match libgarmin's log_fn typedef:
 *   void (*log_fn)(char *file, int line, int level, char *fmt, ...) */
static void mylog(char *file, int line, int level, char *fmt, ...) {
    (void)file;
    (void)line;
    (void)level;
    (void)fmt;
}

int main(void) {
    struct gar *g = gar_init(NULL, mylog);
    if (!g) {
        fprintf(stderr, "FAIL: gar_init returned NULL\n");
        return 1;
    }
    gar_free(g);
    printf("OK: libgarmin linked and gar_init/gar_free work on OHOS\n");
    return 0;
}
