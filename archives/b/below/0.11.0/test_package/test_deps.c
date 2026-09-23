/* test_deps.c — dependency functional test for below 0.11.0 (test_package).
 *
 * below consumes libelf/0.8.13.1 and zlib/1.3.2 at build time (both ship
 * static libraries only: libelf.a / libz.a), so the packaged binary has no
 * DT_NEEDED entries for them and nothing at runtime would prove the
 * dependencies actually work on HarmonyOS. This consumer program is
 * compiled against the dependency packages' headers/libraries and executed
 * on the device, exercising real dependency code paths:
 *
 *   zlib  : zlibVersion(), compress2(), uncompress() round-trip
 *   libelf: elf_version(), elf_begin(), gelf_getehdr(), elf_getshdrnum()
 *           parsing this very binary (an OHOS aarch64 ELF)
 *
 * Exit status is non-zero when any assertion fails; the last line is a
 * machine-readable SUMMARY so the counts quoted in the PR description stay
 * auditable.
 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <gelf.h>
#include <libelf.h>
#include <zlib.h>

#ifndef EM_AARCH64
#define EM_AARCH64 183
#endif

static int executed = 0;
static int failures = 0;

static void check(int ok, const char *msg)
{
    executed++;
    if (ok) {
        printf("[ok] %s\n", msg);
    } else {
        printf("[fail] %s\n", msg);
        failures++;
    }
}

int main(int argc, char **argv)
{
    printf("== 依赖测试 / dependency functional test (libelf + zlib) ==\n");

    /* ── zlib ─────────────────────────────────────────────────────────── */
    const char *zv = zlibVersion();
    check(zv != NULL && zv[0] != '\0', "zlibVersion() returns a version string");
    printf("     zlib version: %s\n", zv ? zv : "(null)");

    unsigned char in[4096];
    for (size_t i = 0; i < sizeof(in); i++) {
        in[i] = (unsigned char)((i * 7u + 13u) & 0xffu);
    }
    uLongf clen = compressBound((uLong)sizeof(in));
    unsigned char *comp = (unsigned char *)malloc(clen);
    check(comp != NULL, "malloc() for the compression buffer");
    if (comp == NULL) {
        printf("SUMMARY: executed=%d passed=%d failed=%d\n",
               executed, executed - failures, failures);
        return 1;
    }

    int rc = compress2(comp, &clen, in, (uLong)sizeof(in), 6);
    check(rc == Z_OK && clen > 0, "compress2() compresses a 4 KiB buffer");
    printf("     compressed %zu -> %lu bytes\n", sizeof(in), (unsigned long)clen);

    unsigned char out[4096];
    uLongf olen = (uLongf)sizeof(out);
    rc = uncompress(out, &olen, comp, clen);
    check(rc == Z_OK && olen == (uLongf)sizeof(in) &&
              memcmp(in, out, sizeof(in)) == 0,
          "uncompress() round-trips the buffer byte-exactly");
    free(comp);

    /* ── libelf ───────────────────────────────────────────────────────── */
    check(elf_version(EV_CURRENT) != EV_NONE,
          "elf_version(EV_CURRENT) initialises libelf");

    const char *self = (argc > 0 && argv[0] != NULL) ? argv[0] : "/proc/self/exe";
    int fd = open(self, O_RDONLY);
    check(fd >= 0, "open() the test binary itself for libelf");
    if (fd >= 0) {
        Elf *elf = elf_begin(fd, ELF_C_READ, NULL);
        check(elf != NULL, "elf_begin() opens the ELF image");
        if (elf != NULL) {
            check(elf_kind(elf) == ELF_K_ELF, "elf_kind() reports ELF_K_ELF");

            GElf_Ehdr eh;
            int got = gelf_getehdr(elf, &eh) != NULL;
            check(got, "gelf_getehdr() reads the ELF header");
            if (got) {
                check(eh.e_machine == EM_AARCH64,
                      "libelf reports EM_AARCH64 (OHOS PC target)");
                printf("     e_machine=%u e_type=%u\n",
                       (unsigned)eh.e_machine, (unsigned)eh.e_type);
            }

            size_t shnum = 0;
            int sres = elf_getshdrnum(elf, &shnum);
            check(sres == 0 && shnum > 0,
                  "elf_getshdrnum() enumerates the section headers");
            if (sres == 0) {
                printf("     section headers: %zu\n", shnum);
            }
            elf_end(elf);
        }
        close(fd);
    }

    printf("SUMMARY: executed=%d passed=%d failed=%d\n",
           executed, executed - failures, failures);
    return failures ? 1 : 0;
}
