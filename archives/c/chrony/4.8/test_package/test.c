#include <stdio.h>
#include <sys/stat.h>

/* CHRONYC_PATH is baked in at compile time by test_package/conanfile.py
   (cmake.configure variables) and points at the Conan-packaged chronyc
   binary, NOT a host PATH lookup (R34: test must target the packaged
   binary). test_chrony is a compile-time verification target: it cannot
   be executed on the x86 CI worker because it is cross-compiled for
   OHOS aarch64 (Exec format error). */
#ifndef CHRONYC_PATH
#error "CHRONYC_PATH must be defined (Conan packaged chronyc absolute path)"
#endif

int main(void) {
    struct stat st;
    if (stat(CHRONYC_PATH, &st) != 0) {
        fprintf(stderr, "packaged chronyc not found at %s\n", CHRONYC_PATH);
        return 1;
    }
    printf("packaged chronyc present at %s\n", CHRONYC_PATH);
    return 0;
}
