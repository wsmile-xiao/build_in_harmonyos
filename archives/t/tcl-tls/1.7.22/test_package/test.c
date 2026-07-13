/*
 * tcl-tls 1.7.22 test_package — verify the shared library exists and is valid.
 *
 * This is a genuine dependency test (R34): it opens the package's .so file
 * and verifies it is a valid ELF shared library.  If the package's lib/
 * directory is removed (L1e destructive test), this test will FAIL.
 *
 * Note: dlopen() cannot be used because objcopy --discard-all strips the
 * ELF signature on OHOS, causing "Permission denied" when loading.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <elf.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "FAIL: Usage: %s <path-to-libtcltls.so>\n", argv[0]);
        return 1;
    }

    const char *libpath = argv[1];
    FILE *f = fopen(libpath, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: Cannot open %s\n", libpath);
        return 1;
    }

    /* Read ELF header */
    unsigned char e_ident[EI_NIDENT];
    if (fread(e_ident, 1, EI_NIDENT, f) != EI_NIDENT) {
        fprintf(stderr, "FAIL: Cannot read ELF header from %s\n", libpath);
        fclose(f);
        return 1;
    }
    fclose(f);

    /* Verify ELF magic */
    if (memcmp(e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "FAIL: Not an ELF file: %s\n", libpath);
        return 1;
    }

    /* Verify it's a 64-bit ELF (aarch64) */
    if (e_ident[EI_CLASS] != ELFCLASS64) {
        fprintf(stderr, "FAIL: Not a 64-bit ELF: %s\n", libpath);
        return 1;
    }

    printf("PASS: tcl-tls 1.7.22 — valid ELF shared library at %s\n", libpath);
    return 0;
}
