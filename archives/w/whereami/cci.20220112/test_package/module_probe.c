#include <whereami.h>

int probe_executable_path(char *path, int capacity, int *dirname_length)
{
    return wai_getExecutablePath(path, capacity, dirname_length);
}

int probe_module_path(char *path, int capacity, int *dirname_length)
{
    volatile int result = wai_getModulePath(path, capacity, dirname_length);
    return result;
}
