#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: real invocation test — the packaged thttpd binary is located via
   PATH (set up by the conanrun environment from VirtualRunEnv) and
   executed with popen(). Both the exit code and the version output are
   verified, so this test fails if the package binary is missing, broken
   or reports an unexpected version. */
int main(void) {
    FILE *p;
    char buf[256];
    size_t n;
    int rc;

    p = popen("thttpd -V", "r");
    if (p == NULL) {
        fprintf(stderr, "FATAL: cannot spawn thttpd from PATH\n");
        return 1;
    }
    memset(buf, 0, sizeof(buf));
    n = fread(buf, 1, sizeof(buf) - 1, p);
    rc = pclose(p);
    if (rc != 0) {
        fprintf(stderr, "FATAL: thttpd -V exited with %d\n", rc);
        return 1;
    }
    if (n == 0 || strstr(buf, "thttpd/") == NULL) {
        fprintf(stderr, "FATAL: unexpected thttpd -V output: '%s'\n", buf);
        return 1;
    }
    printf("thttpd binary OK: %s", buf);
    return 0;
}
