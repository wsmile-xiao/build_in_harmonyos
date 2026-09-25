/* test_l2tpns.c — l2tpns 2.5.0 OHOS test_package checker.
 *
 * OHOS-specific artifact assertions (this run's mandatory new test cases —
 * these do NOT reuse any upstream suite; l2tpns ships none, see
 * MANIFEST.yml). Takes the l2tpns package folder as argv[1] and verifies:
 *
 *   1. bin/l2tpns embeds "L2TPNS version 2.5.0" — the version the daemon
 *      logs at startup (l2tpns.h VERSION) matches the package version.
 *      This is the same assertion upstream scripts/ci-test.sh makes by
 *      grepping /var/log/l2tpns after starting the daemon on a real LNS,
 *      downgraded to a static scan because starting the daemon needs
 *      root + /dev/net/tun + kernel L2TP support (all absent on OHOS).
 *   2. bin/l2tpns references the epoll API — proves the run's Makefile
 *      patch branch (-DHAVE_EPOLL, replacing the fragile uname|perl probe)
 *      is actually effective in the shipped binary on OHOS.
 *   3. bin/l2tpns does NOT mention "libdl.so" — proves the recipe override
 *      l2tpns.LIBS dropped the standalone libdl (musl provides dlopen in
 *      libc); a stray -ldl would show up as a libdl.so DT_NEEDED string.
 *   4. lib/l2tpns/ contains the 8 CLI plugins, each a little-endian ELF
 *      shared object (ELFMAG + e_type == ET_DYN) — the plugin set dlopen()ed
 *      by the daemon at runtime is delivered intact for the OHOS layout.
 *   5. bin/nsctl is an ELF executable (loads on OHOS).
 *
 * Each CHECK prints a TAP-style line; any failure exits non-zero.
 *
 * Usage: test_l2tpns <package_folder>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check_no = 0;
static int failures = 0;

#define CHECK(cond, name)                     \
    do {                                      \
        check_no++;                           \
        if (cond) {                           \
            printf("ok %d - %s\n", check_no, name); \
        } else {                              \
            printf("not ok %d - %s\n", check_no, name); \
            failures++;                       \
        }                                     \
    } while (0)

static char *slurp(const char *path, size_t *len_out)
{
    FILE *f = fopen(path, "rb");
    char *buf;
    long len;
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0 || (len = ftell(f)) < 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    buf = malloc((size_t)len + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    if (fread(buf, 1, (size_t)len, f) != (size_t)len) {
        free(buf);
        fclose(f);
        return NULL;
    }
    fclose(f);
    buf[len] = '\0';
    *len_out = (size_t)len;
    return buf;
}

static int contains(const char *hay, size_t hay_len, const char *needle)
{
    size_t n = strlen(needle);
    if (n == 0 || hay_len < n)
        return 0;
    for (size_t i = 0; i + n <= hay_len; i++) {
        if (memcmp(hay + i, needle, n) == 0)
            return 1;
    }
    return 0;
}

static int is_elf_dyn_so(const char *path)
{
    unsigned char hdr[20];
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    if (fread(hdr, 1, sizeof(hdr), f) != sizeof(hdr)) {
        fclose(f);
        return 0;
    }
    fclose(f);
    /* ELFMAG */
    if (hdr[0] != 0x7f || hdr[1] != 'E' || hdr[2] != 'L' || hdr[3] != 'F')
        return 0;
    /* little-endian e_type at offset 16 == ET_DYN (3) */
    return hdr[16] == 0x03 && hdr[17] == 0x00;
}

int main(int argc, char *argv[])
{
    char path[4096];
    const char *pkg;
    size_t bin_len = 0;
    char *bin;

    if (argc < 2) {
        fprintf(stderr, "usage: test_l2tpns <package_folder>\n");
        return 2;
    }
    pkg = argv[1];

    /* ---- assertions against the packaged daemon binary ---- */
    snprintf(path, sizeof(path), "%s/bin/l2tpns", pkg);
    bin = slurp(path, &bin_len);
    CHECK(bin != NULL, "bin/l2tpns is readable");
    if (!bin) {
        printf("1..%d\n", check_no);
        return failures ? 1 : 0;
    }

    CHECK(contains(bin, bin_len, "L2TPNS version 2.5.0"),
          "daemon embeds VERSION 2.5.0 (upstream ci-test.sh assertion, "
          "statically scanned: daemon start needs root/TUN/L2TP kernel)");

    CHECK(contains(bin, bin_len, "epoll_ctl") || contains(bin, bin_len, "epoll_wait"),
          "daemon references the epoll API (Makefile -DHAVE_EPOLL patch "
          "branch effective on OHOS)");

    CHECK(!contains(bin, bin_len, "libdl.so"),
          "daemon carries no libdl.so dependency (musl dlopen is in libc; "
          "l2tpns.LIBS override dropped -ldl)");

    free(bin);

    /* ---- assertions against the delivered plugin set ---- */
    {
        const char *plugins[] = {
            "autosnoop.so", "autothrottle.so", "garden.so", "sessionctl.so",
            "setrxspeed.so", "snoopctl.so", "stripdomain.so", "throttlectl.so",
        };
        const int nplug = (int)(sizeof(plugins) / sizeof(plugins[0]));
        int all_ok = 1;

        for (int i = 0; i < nplug; i++) {
            snprintf(path, sizeof(path), "%s/lib/l2tpns/%s", pkg, plugins[i]);
            if (!is_elf_dyn_so(path)) {
                all_ok = 0;
                fprintf(stderr, "missing or not ET_DYN: %s\n", path);
            }
        }
        CHECK(all_ok, "all 8 CLI plugins delivered as ELF shared objects "
                      "under lib/l2tpns/");
    }

    /* ---- nsctl sanity ---- */
    {
        size_t nctl_len = 0;
        unsigned char hdr[6];
        FILE *f;
        int is_elf = 0;

        snprintf(path, sizeof(path), "%s/bin/nsctl", pkg);
        f = fopen(path, "rb");
        if (f) {
            if (fread(hdr, 1, sizeof(hdr), f) == sizeof(hdr))
                is_elf = (hdr[0] == 0x7f && hdr[1] == 'E' && hdr[2] == 'L' && hdr[3] == 'F');
            fclose(f);
        }
        CHECK(is_elf, "bin/nsctl is an ELF executable");
        (void)nctl_len;
    }

    printf("1..%d\n", check_no);
    if (failures == 0)
        printf("l2tpns OHOS test_package passed (%d/%d)\n", check_no, check_no);
    return failures ? 1 : 0;
}
