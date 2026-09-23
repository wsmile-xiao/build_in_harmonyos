#include "png2ico_test_common.h"

int main(int argc, char **argv)
{
    const char *root;

    if (argc != 2) {
        fprintf(stderr, "usage: test_png2ico /path/to/png2ico\n");
        return 2;
    }
    root = getenv("TMPDIR");
    if (root == NULL || root[0] == '\0') {
#if defined(_WIN32)
        root = ".";
#else
        root = "/tmp";
#endif
    }
    return run_png2ico_case(argv[1], root, "png2ico-conan");
}
