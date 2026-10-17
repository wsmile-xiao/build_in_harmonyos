#include <dlfcn.h>
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <arpa/inet.h>

#include <oas.h>

static int failures;

static void check(int cond, const char *what, long value) {
    if (cond) {
        printf("ok %s (value=%ld)\n", what, value);
    } else {
        printf("NOT OK %s (value=%ld)\n", what, value);
        failures++;
    }
}

int main(void) {
    struct sockaddr_in6 v6;
    int first, second, sentinel;
    void *handle;
    void *sym;

    memset(&v6, 0, sizeof(v6));
    v6.sin6_family = AF_INET6;
    inet_pton(AF_INET6, "::1", &v6.sin6_addr);

    sentinel = oas_address_score(NULL);
    check(sentinel == 10000, "null address returns the no-match sentinel", sentinel);

    first = oas_address_score(&v6);
    check(first == 10000 || (first >= 1 && first <= 1000),
          "v6 address returns sentinel or a positive rule number", first);

    second = oas_address_score(&v6);
    check(second == first, "same address scores identically twice", second);

    handle = dlopen("liboas.so", RTLD_NOW | RTLD_GLOBAL);
    if (handle == NULL) {
        printf("NOT OK dlopen liboas.so: %s\n", dlerror());
        failures++;
    } else {
        sym = dlsym(handle, "oas_address_score");
        check(sym != NULL, "liboas.so exports oas_address_score", (long)(sym != NULL));
        dlclose(handle);
    }

    if (failures != 0) {
        printf("FAILED %d assertion(s)\n", failures);
        return 1;
    }
    printf("PASS all 4 assertions\n");
    return 0;
}
