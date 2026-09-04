/*
 * test.c — Test source for xf86-video-fbdev Conan test_package.
 *
 * This test verifies the fbdev_drv.so driver module is a valid ELF
 * shared object targeting AArch64. Since the driver is an X.Org plugin
 * that expects the X server to provide symbols at runtime, dlopen is
 * not used (unresolved symbols are expected). Instead, we read the
 * ELF header directly from the file to validate its format.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/stat.h>
#include <elf.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path-to-fbdev_drv.so>\n", argv[0]);
        return 1;
    }

    const char *so_path = argv[1];

    /* Test 1: File exists and is readable */
    struct stat st;
    if (stat(so_path, &st) != 0) {
        fprintf(stderr, "FAIL: Cannot stat %s\n", so_path);
        return 1;
    }
    printf("PASS: fbdev_drv.so exists (%ld bytes)\n", st.st_size);

    /* Test 2: Read ELF header and verify magic */
    FILE *f = fopen(so_path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: Cannot open %s\n", so_path);
        return 1;
    }

    Elf64_Ehdr ehdr;
    if (fread(&ehdr, sizeof(ehdr), 1, f) != 1) {
        fprintf(stderr, "FAIL: Cannot read ELF header\n");
        fclose(f);
        return 1;
    }
    fclose(f);

    /* Verify ELF magic */
    if (memcmp(ehdr.e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "FAIL: Not an ELF file\n");
        return 1;
    }
    printf("PASS: Valid ELF magic\n");

    /* Test 3: Verify 64-bit (ELFCLASS64) */
    if (ehdr.e_ident[EI_CLASS] != ELFCLASS64) {
        fprintf(stderr, "FAIL: Not 64-bit ELF (class=%d)\n", ehdr.e_ident[EI_CLASS]);
        return 1;
    }
    printf("PASS: 64-bit ELF\n");

    /* Test 4: Verify AArch64 (EM_AARCH64 = 183) */
    if (ehdr.e_type != ET_DYN) {
        fprintf(stderr, "FAIL: Not a shared library (type=%d)\n", ehdr.e_type);
        return 1;
    }
    printf("PASS: Shared library (DYN)\n");

    /* Test 5: Verify AArch64 machine type */
    if (ehdr.e_machine != EM_AARCH64) {
        fprintf(stderr, "FAIL: Not AArch64 (machine=%d)\n", ehdr.e_machine);
        return 1;
    }
    printf("PASS: AArch64 architecture\n");

    printf("All tests passed!\n");
    return 0;
}
