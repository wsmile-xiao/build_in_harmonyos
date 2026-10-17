#ifndef __OHOS__
#error "The HarmonyOS consumer test must be compiled for OHOS"
#endif

#include "png2ico_test_common.h"

int main(int argc, char **argv)
{
    const char *root;

    if (argc != 2) {
        fprintf(stderr, "usage: test_ohos /path/to/png2ico\n");
        return 2;
    }
    root = getenv("TMPDIR");
    if (root == NULL || root[0] == '\0') {
        fprintf(stderr, "FAIL: HarmonyOS test requires a writable TMPDIR\n");
        return 1;
    }
    return run_png2ico_case(argv[1], root, "png2ico-harmonyos");
}
