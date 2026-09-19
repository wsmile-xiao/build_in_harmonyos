/* Consumer behaviour test for the packaged shellex.
 *
 * 1. Loads the real shellex_preload.so into a live /bin/sh process via
 *    LD_PRELOAD and asserts the shell executes a command normally and the
 *    library actually loads (a broken/unloadable .so makes the loader
 *    print "Error loading shared library" on stderr).
 * 2. Syntax-checks the generated launcher script with `sh -n`.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define SHELLEX_MARKER "shellex_consumer_ok"

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s <shellex_preload.so> <launcher-script>\n", argv[0]);
        return 2;
    }

    /* --- part 1: preload library load + host shell behaviour --- */
    setenv("LD_PRELOAD", argv[1], 1);
    FILE *p = popen("/bin/sh -c 'printf " SHELLEX_MARKER "' 2>shellex_ldpreload.err", "r");
    if (!p) {
        perror("popen");
        return 2;
    }
    char out[128] = {0};
    size_t n = fread(out, 1, sizeof(out) - 1, p);
    int rc = pclose(p);
    unsetenv("LD_PRELOAD");

    /* assertion 1: the preloaded shell must exit successfully */
    if (rc == -1 || !WIFEXITED(rc) || WEXITSTATUS(rc) != 0) {
        fprintf(stderr, "preloaded /bin/sh did not exit cleanly (rc=%d)\n", rc);
        return 1;
    }
    /* assertion 2: the shell must have executed the command */
    if (n != strlen(SHELLEX_MARKER) || strcmp(out, SHELLEX_MARKER) != 0) {
        fprintf(stderr, "preloaded /bin/sh produced wrong output: '%s'\n", out);
        return 1;
    }
    /* assertion 3: the preload library must have actually loaded */
    FILE *e = fopen("shellex_ldpreload.err", "r");
    if (!e) {
        perror("fopen err");
        return 2;
    }
    char err[1024] = {0};
    size_t en = fread(err, 1, sizeof(err) - 1, e);
    fclose(e);
    err[en] = '\0';
    unlink("shellex_ldpreload.err");
    if (strstr(err, "Error loading shared library") != NULL) {
        fprintf(stderr, "shellex_preload.so failed to load: %s\n", err);
        return 1;
    }

    /* --- part 2: the generated launcher script must be valid POSIX sh --- */
    char cmd[4096];
    snprintf(cmd, sizeof(cmd), "/bin/sh -n %s", argv[2]);
    /* assertion 4: `sh -n` on the launcher exits 0 */
    if (system(cmd) != 0) {
        fprintf(stderr, "launcher script failed sh -n syntax check\n");
        return 1;
    }

    printf("shellex consumer test: preload library loaded and shell behaved, "
           "launcher script syntax OK\n");
    return 0;
}
