#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    void *handle = dlopen("libsee.so", RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
        fprintf(stderr, "libsee consumer: dlopen failed: %s\n", dlerror());
        return 1;
    }

    dlerror();
    size_t (*print_size)(size_t, char, char *) =
        (size_t (*)(size_t, char, char *))dlsym(handle, "libsee_print_size");
    const char *error = dlerror();
    if (error != NULL || print_size == NULL) {
        fprintf(stderr, "libsee consumer: dlsym failed: %s\n",
                error != NULL ? error : "null symbol");
        dlclose(handle);
        return 1;
    }

    char buffer[64] = {0};
    const char expected[] = "1,234,567";
    size_t length = print_size(1234567, ',', buffer);
    if (length != sizeof(expected) - 1) {
        fprintf(stderr, "libsee consumer: expected length %zu, got %zu\n",
                sizeof(expected) - 1, length);
        dlclose(handle);
        return 1;
    }
    if (strcmp(buffer, expected) != 0) {
        fprintf(stderr, "libsee consumer: expected %s, got %s\n", expected, buffer);
        dlclose(handle);
        return 1;
    }
    printf("libsee consumer: libsee_print_size -> %s\n", buffer);
    dlclose(handle);
    return 0;
}
