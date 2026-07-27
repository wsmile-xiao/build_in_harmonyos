#include <stdio.h>
#include <stdlib.h>

int main(void) {
    const char *test_name = "analog homebrew (upstream 6.0.18)";
    printf("%s: running analog --version\n", test_name);

    /* Call analog binary to verify it's installed and executable */
    int ret = system("analog --version > /dev/null 2>&1");
    if (ret == 0) {
        printf("%s: analog --version OK\n", test_name);
    } else {
        printf("%s: analog --version FAILED (exit code %d)\n", test_name, ret);
        return 1;
    }

    /* Check --help works */
    ret = system("analog --help > /dev/null 2>&1");
    if (ret == 0) {
        printf("%s: analog --help OK\n", test_name);
    } else {
        printf("%s: analog --help FAILED (exit code %d)\n", test_name, ret);
        return 1;
    }

    printf("%s: all tests passed\n", test_name);
    return 0;
}