#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int ret;

    /* Test 1: halibut --version */
    ret = system("halibut --version");
    if (ret != 0) {
        fprintf(stderr, "FAIL: halibut --version returned %d\n", ret);
        return 1;
    }

    /* Test 2: Smoke test with HTML output */
    ret = system("echo '\\C{test} Hello World' > test-halibut.but");
    if (ret != 0) {
        fprintf(stderr, "FAIL: could not create test input\n");
        return 1;
    }

    ret = system("halibut --html=test-halibut.html test-halibut.but");
    if (ret != 0) {
        fprintf(stderr, "FAIL: halibut smoke test failed\n");
        return 1;
    }

    printf("halibut 1.3: OK\n");
    return 0;
}