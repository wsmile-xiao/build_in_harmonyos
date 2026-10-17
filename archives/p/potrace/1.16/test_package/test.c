#include <stdio.h>
#include <potracelib.h>

int main(void) {
    const char *ver = potrace_version();
    if (ver == NULL) {
        fprintf(stderr, "ERROR: potrace_version() returned NULL\n");
        return 1;
    }
    printf("potrace version: %s\n", ver);

    /* Test param allocation/free (minimal API exercise) */
    potrace_param_t *param = potrace_param_default();
    if (param == NULL) {
        fprintf(stderr, "ERROR: potrace_param_default() returned NULL\n");
        return 1;
    }
    potrace_param_free(param);
    printf("potrace param alloc/free: OK\n");
    return 0;
}
