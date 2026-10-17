/* test_cmospwd.c: consumer tests for the packaged cmospwd 5 CLI on HarmonyOS PC.
 *
 * Upstream ships no test suite, so these tests drive the installed binary the
 * way a user would and assert on decoded output, not just on a banner. Three of
 * the cases are known-plaintext: a synthetic CMOS backup is built from the
 * inverse of the module's algorithm, so recovering "AB" proves the decode path
 * really ran on this target.
 *
 * argv[1] = path to the packaged bin/cmospwd
 * argv[2] = path to the package folder (for artifact presence checks)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int g_pass;
static int g_fail;

#define CHECK(cond, name)                                              \
    do {                                                               \
        if (cond) { g_pass++; printf("[PASS] %s\n", (name)); }         \
        else      { g_fail++; printf("[FAIL] %s\n", (name)); }         \
    } while (0)

#define OUT_CAP 65536

static const char *g_bin;

/* Run the packaged binary, merging stderr into stdout. stdin is /dev/null so no
 * code path can block on the upstream wait_key()/getchar() prompts. */
static int run(char *out, size_t cap, const char *args)
{
    char cmd[8192];
    FILE *p;
    size_t n = 0;
    int c;

    out[0] = '\0';
    snprintf(cmd, sizeof(cmd), "\"%s\" %s 2>&1 </dev/null", g_bin, args);
    p = popen(cmd, "r");
    if (!p)
        return -1;
    while ((c = fgetc(p)) != EOF && n + 1 < cap)
        out[n++] = (char)c;
    out[n] = '\0';
    return pclose(p);
}

static int has(const char *out, const char *needle)
{
    return strstr(out, needle) != NULL;
}

/* Copy the first line containing marker into line, so assertions can be scoped
 * to one module's output row instead of the whole transcript. */
static int line_with(const char *out, const char *marker, char *line, size_t cap)
{
    const char *hit = strstr(out, marker);
    const char *start, *end;

    if (!hit)
        return 0;
    for (start = hit; start > out && start[-1] != '\n'; start--)
        ;
    for (end = hit; *end && *end != '\n'; end++)
        ;
    if ((size_t)(end - start) + 1 > cap)
        return 0;
    memcpy(line, start, (size_t)(end - start));
    line[end - start] = '\0';
    return 1;
}

static int write_vector(const char *path, size_t size, const unsigned char *patch,
                        const int *offsets, int npatch)
{
    unsigned char *buf = calloc(size, 1);
    FILE *f;
    int i;

    if (!buf)
        return 0;
    for (i = 0; i < npatch; i++)
        buf[offsets[i]] = patch[i];
    f = fopen(path, "wb");
    if (!f) { free(buf); return 0; }
    if (fwrite(buf, 1, size, f) != size) { fclose(f); free(buf); return 0; }
    fclose(f);
    free(buf);
    return 1;
}

static int exists(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 && S_ISREG(st.st_mode);
}

int main(int argc, char *argv[])
{
    static char out[OUT_CAP];
    char line[4096];
    char path[4096];
    int rc;

    if (argc < 3) {
        printf("usage: test_cmospwd <bin/cmospwd> <package_folder>\n");
        return 2;
    }
    g_bin = argv[1];
    printf("== cmospwd 5 consumer tests ==\n");

    /* Artifacts. */
    CHECK(access(g_bin, X_OK) == 0, "bin/cmospwd is installed and executable");
    snprintf(path, sizeof(path), "%s/licenses/COPYING", argv[2]);
    CHECK(exists(path), "licenses/COPYING shipped");
    snprintf(path, sizeof(path), "%s/licenses/cmospwd.txt", argv[2]);
    CHECK(exists(path), "licenses/cmospwd.txt shipped");

    /* Usage path: an unrecognised option selects the help branch. */
    rc = run(out, sizeof(out), "--help");
    CHECK(rc == 0, "--help exits 0");
    CHECK(has(out, "Usage:"), "--help prints the option table");
    CHECK(line_with(out, "CmosPwd", line, sizeof(line)) &&
          has(line, "CmosPwd - BIOS Cracker 5.0"),
          "banner self-labels upstream 5.0 (task version 5)");

    /* Plain zeroed backup: module 1 (acer) runs, decodes nothing. */
    CHECK(write_vector("cmospwd_zero128.bin", 128, NULL, NULL, 0), "zero128 vector written");
    rc = run(out, sizeof(out), "-l cmospwd_zero128.bin -m1");
    CHECK(rc == 0, "-l zero128 -m1 exits 0");
    CHECK(has(out, "load_backup(cmospwd_zero128.bin)"), "backup file is opened by load_backup()");
    CHECK(has(out, "Read a 128 byte cmos backup"), "128-byte backup size recognised");
    CHECK(has(out, "Acer/IBM"), "module 1 (acer) ran for -m1");
    CHECK(has(out, "Keyboard : US"), "default keyboard layout is US");

    /* -m is a digit mask, not an index: only '1' enables a module. */
    rc = run(out, sizeof(out), "-l cmospwd_zero128.bin -m2");
    CHECK(rc == 0, "-m2 exits 0");
    CHECK(!has(out, "Acer/IBM"), "-m2 runs no module (mask semantics)");

    rc = run(out, sizeof(out), "-l cmospwd_zero128.bin -m01");
    CHECK(rc == 0 && has(out, "AMI BIOS") && !has(out, "Acer/IBM"),
          "-m01 dispatches to module 2 (ami_old) only");

    rc = run(out, sizeof(out), "-l cmospwd_zero128.bin -m11");
    CHECK(rc == 0 && has(out, "Acer/IBM") && has(out, "AMI BIOS"),
          "-m11 runs modules 1 and 2");

    rc = run(out, sizeof(out), "-l cmospwd_zero128.bin -m1 -kfr");
    CHECK(rc == 0 && has(out, "Keyboard : FR"), "-kfr switches the keyboard layout");

    /* Known plaintext 1: acer() reads 7 bytes at 0x100, shr 1, ASCII mode. */
    {
        const unsigned char bytes[2] = { 0x82, 0x84 };   /* 'A'<<1, 'B'<<1 */
        const int offsets[2] = { 0x100, 0x101 };
        CHECK(write_vector("cmospwd_acer512.bin", 512, bytes, offsets, 2),
              "acer512 vector written");
    }
    rc = run(out, sizeof(out), "-l cmospwd_acer512.bin -m1");
    CHECK(rc == 0 && line_with(out, "Acer/IBM", line, sizeof(line)) &&
          has(line, "[AB]"),
          "ALGO_ACER recovers 'AB' from a crafted backup");

    /* Known plaintext 2: phoenix_1_03() reads cmos[0x61] bytes at 0x62, +0x20. */
    {
        const unsigned char bytes[4] = { 0x00, 0x02, 0x21, 0x22 };
        const int offsets[4] = { 0x60, 0x61, 0x62, 0x63 };
        CHECK(write_vector("cmospwd_phx128.bin", 128, bytes, offsets, 4),
              "phx128 vector written");
    }
    rc = run(out, sizeof(out),
             "-l cmospwd_phx128.bin -m0000000000000000001");
    CHECK(rc == 0 && line_with(out, "Phoenix a486 1.03", line, sizeof(line)) &&
          has(line, "[AB]"),
          "ALGO_PHOENIX_ADD recovers 'AB' from a crafted backup");

    /* Control: the same file decoded through acer's offsets must not yield the
     * phoenix result, so the two vectors above cannot pass by echoing. */
    rc = run(out, sizeof(out), "-l cmospwd_phx128.bin -m1");
    CHECK(rc == 0 && line_with(out, "Acer/IBM", line, sizeof(line)) &&
          !has(line, "[AB]"),
          "decode is offset sensitive (phx vector gives no 'AB' under -m1)");

    /* Error path. */
    rc = run(out, sizeof(out), "-l cmospwd_missing.bin -m1");
    CHECK(rc != 0 && has(out, "Unable to read"), "unreadable backup exits non-zero");

    /* HarmonyOS PC (aarch64) specific: the portability patch turns the direct
     * CMOS path into a diagnostic that points at backup files. */
    rc = run(out, sizeof(out), "");
#if defined(__i386__) || defined(__x86_64__)
    CHECK(has(out, "Acer/IBM") || has(out, "root"),
          "x86: direct CMOS read path reached");
#else
    CHECK(rc != 0 && has(out, "x86 I/O ports") && has(out, "-l/-r"),
          "aarch64/OHOS: hardware access reports guidance and exits non-zero");
#endif

    remove("cmospwd_zero128.bin");
    remove("cmospwd_acer512.bin");
    remove("cmospwd_phx128.bin");

    printf("TOTAL=%d PASS=%d FAIL=%d\n", g_pass + g_fail, g_pass, g_fail);
    if (g_fail == 0) {
        printf("ALL TESTS PASSED\n");
        return 0;
    }
    return 1;
}
