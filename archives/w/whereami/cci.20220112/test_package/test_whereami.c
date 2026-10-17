#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "module_probe.h"

typedef int (*path_function)(char *, int, int *);

static int check_path(path_function get_path, const char *label,
                      const char *expected_name)
{
    int dirname_length = -1;
    int length = get_path(NULL, 0, NULL);
    char *path;

    if (length <= 0) {
        fprintf(stderr, "%s length query failed: %d\n", label, length);
        return 1;
    }

    path = (char *)malloc((size_t)length + 1);
    if (path == NULL) {
        return 1;
    }

    if (get_path(path, length, &dirname_length) != length) {
        fprintf(stderr, "%s path query failed\n", label);
        free(path);
        return 1;
    }
    path[length] = '\0';

    if (path[0] != '/' || dirname_length <= 0 || dirname_length >= length ||
        path[dirname_length] != '/' || strstr(path, expected_name) == NULL) {
        fprintf(stderr, "%s returned invalid path: %s\n", label, path);
        free(path);
        return 1;
    }

    printf("%s: %s\n", label, path);
    free(path);
    return 0;
}

int main(void)
{
    void *module = dlopen("./libmodule_probe.so", RTLD_NOW | RTLD_LOCAL);
    path_function executable_path;
    path_function module_path;

    if (module == NULL) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    executable_path = (path_function)dlsym(module, "probe_executable_path");
    module_path = (path_function)dlsym(module, "probe_module_path");
    if (executable_path == NULL || module_path == NULL) {
        fprintf(stderr, "dlsym failed: %s\n", dlerror());
        dlclose(module);
        return 1;
    }

    if (check_path(executable_path, "executable", "whereami_test") != 0 ||
        check_path(module_path, "module", "libmodule_probe.so") != 0) {
        dlclose(module);
        return 1;
    }

    dlclose(module);
    return 0;
}
