/* libxau 1.0.11 consumer link + API smoke test.
 *
 * Exercises XauFileName() which returns the path to the Xauthority file
 * (or NULL when XAUTHORITY env / $HOME cannot resolve one). Also exercises
 * XauDisposeAuth() on a NULL pointer (must be safe per the API contract).
 *
 * Note: XauLockAuth / XauReadAuth are intentionally NOT called — they
 * touch the filesystem and the IPC lock subsystem, which has surprising
 * behaviour on a bare OHOS test runner. The two calls below are sufficient
 * to prove the package links and that its public API symbols resolve.
 */

#include <stdio.h>
#include <stdlib.h>
#include <X11/Xauth.h>

int main(void) {
    /* 1. XauFileName() returns a path or NULL. */
    char *path = XauFileName();
    if (path == NULL) {
        /* Acceptable on a headless CI worker with no X server. */
        fprintf(stderr, "XauFileName() returned NULL (no Xauthority path)\n");
    } else if (path[0] == '\0') {
        fprintf(stderr, "XauFileName() returned empty string\n");
        return 1;
    } else {
        printf("XauFileName() = %s\n", path);
    }

    /* 2. XauDisposeAuth(NULL) must be safe — documented no-op per API. */
    XauDisposeAuth(NULL);

    /* 3. Verify the Xauth struct is at least 32 bytes wide (basic ABI sanity
     *    check — X.Org guarantees the struct layout is stable). */
    if (sizeof(Xauth) < 32) {
        fprintf(stderr, "sizeof(Xauth) too small: %zu\n", sizeof(Xauth));
        return 2;
    }

    if (printf("libxau api smoke ok\n") < 0) {
        return 3;
    }
    return 0;
}