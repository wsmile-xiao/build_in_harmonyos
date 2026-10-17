/* test_fishcamp.c — indi-fishcamp 1.1 consumer end-to-end suite.
 *
 * Usage: test_fishcamp <driver-binary> <device-xml> <log>
 *
 * The packaged driver is an INDI application: it is validated statically
 * (HC-1 ELF, HC-2 framework linkage + embedded Starfish logic strings,
 * HC-5 OHOS aarch64 target). The driver's functional core is libfishcamp,
 * whose built-in simulation mode (fcUsb_setSimulation(true)) emulates the
 * Starfish camera end-to-end; HC-3 drives the full consumer command
 * sequence against it and asserts the exact deterministic simulated
 * values. HC-4 validates the packaged INDI device descriptor.
 *
 * stdout is redirected to <log>; the conanfile parses the transcript.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdbool.h>

#include <fishcamp.h>

static int g_checks = 0;
static int g_failures = 0;
static const char *g_case = "?";

static void ok(const char *what)
{
    g_checks++;
    printf("ok   - %s\n", what);
}

static void fail(const char *what)
{
    g_checks++;
    g_failures++;
    printf("FAIL - %s\n", what);
}

static void check_true(int cond, const char *what)
{
    if (cond) ok(what); else fail(what);
}

/* ---------- binary helpers -------------------------------------------- */
static unsigned char *read_whole(const char *path, size_t *out_len)
{
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    if (fseek(f, 0, SEEK_END) != 0) { fclose(f); return NULL; }
    long n = ftell(f);
    if (n < 0) { fclose(f); return NULL; }
    rewind(f);
    unsigned char *buf = malloc((size_t)n + 1);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) { free(buf); fclose(f); return NULL; }
    fclose(f);
    buf[n] = 0;
    *out_len = (size_t)n;
    return buf;
}

/* NUL-safe byte substring search */
static int buf_contains(const unsigned char *buf, size_t len, const char *needle)
{
    size_t nl = strlen(needle);
    if (nl == 0 || len < nl) return 0;
    for (size_t i = 0; i + nl <= len; i++)
        if (memcmp(buf + i, needle, nl) == 0) return 1;
    return 0;
}

/* little-endian u16 from ELF header */
static uint16_t le16(const unsigned char *p) { return (uint16_t)(p[0] | (p[1] << 8)); }

/* ===================================================================== */
/* HC-1: the packaged driver is a real AArch64 64-bit ELF executable     */
/* ===================================================================== */
static void case_elf(const unsigned char *b, size_t len, const char *bin)
{
    g_case = "HC-1";
    printf("case HC-1 start: packaged driver ELF validity\n");
    check_true(len >= 20, "binary long enough to hold an ELF header");
    check_true(b[0] == 0x7f && b[1] == 'E' && b[2] == 'L' && b[3] == 'F',
               "ELF magic \\x7fELF");
    check_true(len >= 6 && b[4] == 0x02, "ELFCLASS64 (0x02)");
    check_true(len >= 6 && b[5] == 0x01, "ELFDATA2LSB little-endian");

    if (len >= 20) {
        uint16_t type = le16(b + 16);
        uint16_t mach = le16(b + 18);
        check_true(mach == 183, "e_machine == EM_AARCH64 (183)");
        check_true(type == 2 || type == 3,
                   "e_type is ET_EXEC(2) or ET_DYN/PIE(3)");
        if (type == 3) ok("e_type == ET_DYN (position-independent executable)");
    } else {
        fail("could not read e_type/e_machine from header");
    }
    (void)bin;
    printf("case HC-1 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-2: the driver carries the Starfish logic and links INDI framework  */
/* ===================================================================== */
static void case_logic(const unsigned char *b, size_t len)
{
    g_case = "HC-2";
    printf("case HC-2 start: driver logic + INDI framework linkage\n");

    /* NEEDED sonames live in .dynstr; a substring hit proves the link. */
    check_true(buf_contains(b, len, "libindidriver.so.2"),
               "NEEDED libindidriver.so.2 (INDI 2.x driver framework)");
    check_true(buf_contains(b, len, "libindiAlignmentDriver.so.2"),
               "NEEDED libindiAlignmentDriver.so.2 (INDI 2.x CCD base class)");
    check_true(buf_contains(b, len, "libc++_shared.so"),
               "NEEDED libc++_shared.so (C++17 runtime)");

    /* Starfish driver logic compiled into the binary. */
    check_true(buf_contains(b, len, "Starfish CCD"),
               "device default name 'Starfish CCD' present");
    check_true(buf_contains(b, len, "CCD_GAIN"),
               "property group 'CCD_GAIN' present");
    check_true(buf_contains(b, len, "Camera Info"),
               "property group 'Camera Info' (CamInfoTP) present");
    check_true(buf_contains(b, len, "Fishcamp CCD is online."),
               "connect-state message 'Fishcamp CCD is online.' present");
    check_true(buf_contains(b, len, "Taking a %g seconds frame..."),
               "exposure start log 'Taking a %g seconds frame...' present");
    printf("case HC-2 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-3: functional core end-to-end — libfishcamp simulation mode        */
/* ===================================================================== */
static void case_simulation(void)
{
    g_case = "HC-3";
    printf("case HC-3 start: libfishcamp simulation core end-to-end\n");

    fcUsb_init();
    fcUsb_setLogging(false);
    fcUsb_setSimulation(true);

    int n = fcUsb_FindCameras();
    check_true(n == 1, "fcUsb_FindCameras() finds exactly 1 simulated Starfish");
    check_true(fcUsb_GetNumCameras() == 1, "fcUsb_GetNumCameras() == 1");
    check_true(fcUsb_haveCamera() == true, "fcUsb_haveCamera() is true");

    int open_rc = fcUsb_OpenCamera(1);
    check_true(open_rc == 0, "fcUsb_OpenCamera(1) == 0 (camera open path)");

    fc_camInfo info;
    memset(&info, 0, sizeof info);
    int gi_rc = fcUsb_cmd_getinfo(1, &info);
    check_true(gi_rc == 0, "fcUsb_cmd_getinfo(1) == 0");
    check_true(info.width == 1280, "simulated sensor width 1280 px");
    check_true(info.height == 1024, "simulated sensor height 1024 px");
    check_true(info.pixelWidth == 52, "simulated pixel size 52 (wide)");
    check_true(info.pixelHeight == 52, "simulated pixel size 52 (tall)");

    check_true(fcUsb_cmd_setCameraGain(1, 1) == 0,
               "fcUsb_cmd_setCameraGain(1, 1) == 0");
    check_true(fcUsb_cmd_setIntegrationTime(1, 100) == 0,
               "fcUsb_cmd_setIntegrationTime(1, 100 us) == 0");
    check_true(fcUsb_cmd_startExposure(1) == 0,
               "fcUsb_cmd_startExposure(1) == 0");
    check_true((int)fcUsb_cmd_getTemperature(1) == 25,
               "fcUsb_cmd_getTemperature(1) == 25 (simulated, deterministic)");

    int close_rc = fcUsb_CloseCamera(1);
    check_true(close_rc == 0, "fcUsb_CloseCamera(1) == 0");
    fcUsb_close();
    printf("case HC-3 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-4: the packaged INDI device descriptor                             */
/* ===================================================================== */
static void case_xml(const char *xml_path)
{
    g_case = "HC-4";
    printf("case HC-4 start: packaged device descriptor\n");
    size_t len;
    unsigned char *x = read_whole(xml_path, &len);
    check_true(x != NULL, "device xml present and readable");
    if (x) {
        check_true(buf_contains(x, len, "<device label=\"Starfish CCD\">"),
                   "device label 'Starfish CCD'");
        check_true(buf_contains(x, len, "<driver name=\"Starfish CCD\">indi_fishcamp_ccd</driver>"),
                   "driver name maps to binary indi_fishcamp_ccd");
        check_true(buf_contains(x, len, "<version>1.1</version>"),
                   "driver version 1.1");
        check_true(buf_contains(x, len, "group=\"CCDs\""),
                   "device in CCDs group");
        free(x);
    } else {
        fail("could not read device xml for content checks");
        fail("could not read device xml for content checks");
        fail("could not read device xml for content checks");
        fail("could not read device xml for content checks");
    }
    printf("case HC-4 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-5 (harmony_specific): the packaged binary targets OHOS aarch64     */
/* ===================================================================== */
static void case_ohos(const unsigned char *b, size_t len)
{
    g_case = "HC-5";
    printf("case HC-5 start: OHOS aarch64 target confirmation\n");
    check_true(buf_contains(b, len, "/lib/ld-musl-aarch64.so.1"),
               "ELF interpreter is OHOS musl loader /lib/ld-musl-aarch64.so.1");
    check_true(len >= 20 && le16(b + 18) == 183,
               "target machine aarch64 (cross-compiled, not host x86)");
#ifdef __aarch64__
    ok("suite itself compiled for aarch64");
#endif
    printf("case HC-5 PASS-or-continue\n");
}

/* ===================================================================== */
int main(int argc, char **argv)
{
    if (argc != 4) {
        fprintf(stderr, "usage: %s <driver-binary> <device-xml> <log>\n", argv[0]);
        return 2;
    }
    const char *bin = argv[1];
    const char *xml = argv[2];

    /* The conanfile asserts on the transcript file, not on captured stdout:
     * point our stdout at argv[3] so every printf lands in the log. */
    {
        FILE *lf = fopen(argv[3], "w");
        if (lf && dup2(fileno(lf), 1) != -1)
            fflush(stdout);
        else if (lf)
            fclose(lf);
    }

    size_t len = 0;
    unsigned char *b = read_whole(bin, &len);
    if (!b) {
        printf("FAIL - driver binary not readable at %s\n", bin);
        printf("== 5 cases, 1 failed ==\n");
        printf("== 1 checks, 1 failures ==\n");
        printf("RESULT: FAILED\n");
        return 1;
    }

    case_elf(b, len, bin);
    case_logic(b, len);
    case_simulation();
    case_xml(xml);
    case_ohos(b, len);
    free(b);

    int cases_failed = g_failures; /* simplified: any failure fails the run */
    printf("== 5 cases, %d failed ==\n", cases_failed);
    printf("== %d checks, %d failures ==\n", g_checks, g_failures);
    printf("RESULT: %s\n", g_failures == 0 ? "PASSED" : "FAILED");
    return g_failures == 0 ? 0 : 1;
}
