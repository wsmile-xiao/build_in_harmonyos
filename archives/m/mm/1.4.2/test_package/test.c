/*
 * Consumer-view test for OSSP mm (libmm) on HarmonyOS PC.
 *
 * Exercises the public API via the installed package only:
 *   - library/global API : mm_lib_version(), mm_create()/mm_destroy()
 *   - low-level core API : mm_core_size()
 *   - malloc-style API   : mm_malloc()/mm_free()/mm_realloc()
 *
 * The second half runs the *default* backing-file path (file == NULL), which is
 * exactly the code path the HarmonyOS portability patch touches: the default
 * must resolve through $TMPDIR instead of the read-only /tmp (knowledge E002).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mm.h"

#define CHECK(cond, msg)                                                  \
    do {                                                                  \
        if (!(cond)) {                                                    \
            fprintf(stderr, "FAIL: %s\n", (msg));                         \
            return 1;                                                     \
        }                                                                 \
        printf("ok: %s\n", (msg));                                        \
    } while (0)

int main(void)
{
    MM          *mm;
    void        *p;
    void        *q;
    const char  *tmpdir;
    char         path[1024];
    int          version;

    version = mm_lib_version();
    CHECK(version != 0, "mm_lib_version() returns a non-zero version");

    /* ── explicit backing file, placed in $TMPDIR (fallback: CWD) ── */
    tmpdir = getenv("TMPDIR");
    if (tmpdir == NULL || *tmpdir == '\0')
        tmpdir = ".";
    snprintf(path, sizeof(path), "%s/mm-test-package.core", tmpdir);

    mm = mm_create(64 * 1024, path);
    CHECK(mm != NULL, "mm_create() on an explicit backing file");
    CHECK(mm_core_size(mm) > 0, "mm_core_size() reports a usable segment");

    p = mm_malloc(mm, 4096);
    CHECK(p != NULL, "mm_malloc(4096) returns a block");
    memset(p, 0xAB, 4096);

    q = mm_realloc(mm, p, 8192);
    CHECK(q != NULL, "mm_realloc(8192) grows the block");
    CHECK(((unsigned char *)q)[0] == 0xAB &&
          ((unsigned char *)q)[4095] == 0xAB,
          "payload survives mm_realloc()");

    mm_free(mm, q);
    mm_destroy(mm);

    /* ── default backing file: exercises the $TMPDIR patch (E002) ── */
    mm = mm_create(64 * 1024, NULL);
    CHECK(mm != NULL, "mm_create() with the default ($TMPDIR) backing file");
    CHECK(mm_core_size(mm) > 0, "default-path segment reports a usable size");

    p = mm_malloc(mm, 1024);
    CHECK(p != NULL, "mm_malloc(1024) on the default-path segment");
    memset(p, 0xCD, 1024);
    CHECK(((unsigned char *)p)[1023] == 0xCD,
          "payload is writable in the default-path segment");

    mm_free(mm, p);
    mm_destroy(mm);

    printf("test mm 1.4.2: OK\n");
    return 0;
}
