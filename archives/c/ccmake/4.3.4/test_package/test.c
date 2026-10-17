#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* R34: the test must exercise the packaged tool, not just print a string.
 * Usage: test_cmake <path-to-cmake-binary>
 * Drives the packaged cmake through a real configure+build of a tiny project. */
int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <cmake-binary>\n", argv[0]);
        return 2;
    }
    char cmd[4096];
    snprintf(cmd, sizeof(cmd),
             "\"%s\" --version > /dev/null 2>&1", argv[1]);
    if (system(cmd) != 0) {
        fprintf(stderr, "FAIL: %s --version returned non-zero\n", argv[1]);
        return 1;
    }
    snprintf(cmd, sizeof(cmd),
             "rm -rf \"./tp-build\" && \"%s\" -S ./proj -B ./tp-build "
             "-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_MAKE_PROGRAM=make > /dev/null 2>&1 "
             "&& \"%s\" --build ./tp-build > /dev/null 2>&1 "
             "&& ./tp-build/hello | grep -q hello", argv[1], argv[1]);
    if (system(cmd) != 0) {
        fprintf(stderr, "FAIL: packaged cmake could not configure/build a project\n");
        return 1;
    }
    printf("test cmake 4.3.4: OK\n");
    return 0;
}
