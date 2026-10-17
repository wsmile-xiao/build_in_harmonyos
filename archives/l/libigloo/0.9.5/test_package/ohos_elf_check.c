/* OHOS-specific consumer artifact check for the libigloo 0.9.5 package.
 *
 * Opens the consumer binary built by this test_package (test_libigloo,
 * linked against the packaged libigloo) and verifies it is a 64-bit
 * little-endian ELF targeting AArch64 — the artifact shape required for
 * HarmonyOS armv8. The binary path is injected by CTest via
 * $<TARGET_FILE:test_libigloo>.
 *
 * Every failure path prints "FAIL: ..." and returns non-zero; there is
 * no stub, no skip and no print-only path. Success prints the observed
 * header fields and returns 0.
 */
#include <stdio.h>
#include <stdint.h>

#define ELFCLASS64  2
#define ELFDATA2LSB 1
#define EM_AARCH64  183

static int fail(const char *path, const char *reason) {
    printf("FAIL: consumer ELF check (%s): %s\n", path, reason);
    return 1;
}

int main(int argc, char **argv) {
    unsigned char hdr[20];
    const char *path;
    FILE *f;
    uint16_t e_machine;

    if (argc != 2)
        return fail("(no args)", "usage: check_ohos_elf <consumer-binary>");

    path = argv[1];
    f = fopen(path, "rb");
    if (!f)
        return fail(path, "cannot open consumer binary");
    if (fread(hdr, 1, sizeof(hdr), f) != sizeof(hdr)) {
        fclose(f);
        return fail(path, "shorter than a 64-bit ELF header");
    }
    fclose(f);

    if (hdr[0] != 0x7f || hdr[1] != 'E' || hdr[2] != 'L' || hdr[3] != 'F')
        return fail(path, "not an ELF file (bad magic)");

    if (hdr[4] != ELFCLASS64)
        return fail(path, "not ELF64 (EI_CLASS != 2)");

    /* e_machine is read little-endian, so require ELFDATA2LSB first */
    if (hdr[5] != ELFDATA2LSB)
        return fail(path, "not little-endian (EI_DATA != 1)");

    e_machine = (uint16_t)(hdr[18] | ((uint16_t)hdr[19] << 8));
    if (e_machine != EM_AARCH64) {
        printf("FAIL: consumer ELF check (%s): e_machine=%u, expected 183 (EM_AARCH64)\n",
               path, (unsigned)e_machine);
        return 1;
    }

    printf("PASS: consumer binary %s is ELF64 little-endian AArch64 (e_machine=183)\n",
           path);
    return 0;
}
