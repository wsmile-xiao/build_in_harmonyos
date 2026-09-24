#include <fakekey/fakekey.h>

#include <stdio.h>
#include <string.h>
#include <sys/utsname.h>

static int test_null_display(void)
{
    if (fakekey_init(NULL) != NULL) {
        fprintf(stderr, "fakekey_init(NULL) unexpectedly succeeded\n");
        return 1;
    }
    puts("PASS: public API rejects a NULL X11 display");
    return 0;
}

static int test_harmonyos_runtime(void)
{
    struct utsname info;

    if (uname(&info) != 0) {
        perror("uname");
        return 1;
    }
    if (strcmp(info.sysname, "HarmonyOS") != 0) {
        fprintf(stderr, "expected HarmonyOS, got %s\n", info.sysname);
        return 1;
    }
    puts("PASS: HarmonyOS PC runtime identity verified");
    return 0;
}

int main(void)
{
    if (test_null_display() != 0) {
        return 1;
    }
    if (test_harmonyos_runtime() != 0) {
        return 1;
    }
    puts("libfakekey tests: 2/2 passed");
    return 0;
}
