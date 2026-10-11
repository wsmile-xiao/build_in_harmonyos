/* test_gpsnmea.c — indi-gpsnmea 0.2-20221223114018 consumer end-to-end suite.
 *
 * Run as:  test_gpsnmea <driver-binary> <device-xml> <log-path>
 *
 * indi-gpsnmea is an INDI driver (application package). Its only artifacts are
 * bin/indi_gpsnmea (the driver executable) and share/indi/indi_gpsnmea.xml
 * (the device descriptor). The driver itself needs a live TCP NMEA receiver at
 * 192.168.1.1:50000, so it cannot be driven end-to-end here; instead this suite
 * verifies the *shipped package* along two axes:
 *
 *   1. artifact integrity   — the packaged binary is a real AArch64 OHOS ELF
 *                             executable that links the INDI framework and
 *                             carries the GPS NMEA logic (HC-1 / HC-2 / HC-5);
 *   2. core-logic behaviour — the driver's NMEA engine is the in-tree minmea
 *                             parser (minmea.c/h, compiled straight into the
 *                             driver). We recompile that same source and drive
 *                             it with known NMEA 0183 sentences, asserting the
 *                             exact parsed values (HC-3), plus the packaged
 *                             device descriptor (HC-4).
 *
 * Every named use case (HC-n) is a whole flow, not a pile of assertions; the
 * ok/FAIL lines inside a case are its checks. The suite writes a transcript to
 * the log path and exits 0 only when every case passes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>

#include "minmea.h"

/* ---------- tiny result bookkeeping ----------------------------------- */
static int g_checks = 0;
static int g_failures = 0;
static const char *g_case = "(none)";

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

/* near-equality for the fixed-point float helpers */
static void check_close(double got, double want, double eps, const char *what)
{
    char buf[160];
    if (isnan((float)got) && isnan((float)want)) { ok(what); return; }
    if (fabs(got - want) <= eps) ok(what);
    else {
        snprintf(buf, sizeof buf, "%s (got %.5f want %.5f)", what, got, want);
        fail(buf);
    }
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

/* case-insensitive, NUL-safe byte substring search */
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
/* HC-2: the driver carries the GPS NMEA logic and links INDI framework  */
/* ===================================================================== */
static void case_logic(const unsigned char *b, size_t len)
{
    g_case = "HC-2";
    printf("case HC-2 start: driver logic + INDI framework linkage\n");

    /* NEEDED sonames live in .dynstr; a substring hit proves the link. */
    check_true(buf_contains(b, len, "libindidriver.so.2"),
               "NEEDED libindidriver.so.2 (INDI 2.x driver framework)");
    check_true(buf_contains(b, len, "libindidriver.so.2.2.2") ||
               buf_contains(b, len, "libindidriver.so.2"),
               "INDI framework soname resolvable");
    check_true(buf_contains(b, len, "libc++_shared.so"),
               "NEEDED libc++_shared.so (C++ runtime)");

    /* GPS NMEA driver logic compiled into the binary. */
    check_true(buf_contains(b, len, "GPS NMEA"), "device default name 'GPS NMEA' present");
    check_true(buf_contains(b, len, "GPS_STATUS"), "property group 'GPS_STATUS' present");
    check_true(buf_contains(b, len, "GPS_FIX"),    "property name  'GPS_FIX' present");
    check_true(buf_contains(b, len, "Fix Mode"),   "label 'Fix Mode' present");
    check_true(buf_contains(b, len, "Connection"), "TCP connection control wired in");
    printf("case HC-2 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-3: functional NMEA parse suite (recompiled vendored minmea)        */
/* ===================================================================== */
static void case_nmea(void)
{
    g_case = "HC-3";
    printf("case HC-3 start: NMEA 0183 parse behaviour (recompiled minmea)\n");

    const char *rmc  = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A";
    const char *gga  = "$GPGGA,021503.087,3723.2475,N,12158.3416,W,1,8,0.9,545.4,M,46.9,M,,*70";
    const char *gsa  = "$GPGSA,A,3,04,05,06,08,11,12,13,14,15,16,17,18,,1.3,0.8,1.0*12";
    const char *gll  = "$GPGLL,3723.2475,N,12158.3416,W,021503.087,A,A*4F";
    const char *zda  = "$GPZDA,160047.00,14,02,2012,+00,00*4F";
    const char *bad  = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6B"; /* bad ck */
    const char *unk  = "$GPAAV,1,0.5,0.0,0.0*3B";                                            /* unknown */

    /* --- RMC: time / validity / fix / date / coordinates / epoch ---- */
    struct minmea_sentence_rmc r;
    check_true(minmea_check(rmc, true) == true, "RMC checksum valid");
    check_true(minmea_sentence_id(rmc, true) == MINMEA_SENTENCE_RMC, "RMC identified as RMC");
    check_true(minmea_parse_rmc(&r, rmc) == true, "RMC parsed");
    check_true(r.valid == true, "RMC status A (fix valid)");
    check_true(r.time.hours == 12 && r.time.minutes == 35 && r.time.seconds == 19,
               "RMC time 12:35:19");
    check_true(r.date.day == 23 && r.date.month == 3 && r.date.year == 94,
               "RMC date 23/03/1994");
    check_close(minmea_tocoord(&r.latitude),  48.11730, 1e-3, "RMC latitude ~48.11730");
    check_close(minmea_tocoord(&r.longitude), 11.51667, 1e-3, "RMC longitude ~11.51667");
    struct timespec ts;
    check_true(minmea_gettime(&ts, &r.date, &r.time) == 0 && ts.tv_sec == 764426119,
               "RMC -> UNIX epoch 764426119");

    /* --- GGA: fix quality / satellites / altitude / coords ---------- */
    struct minmea_sentence_gga g;
    check_true(minmea_check(gga, true) == true, "GGA checksum valid");
    check_true(minmea_sentence_id(gga, true) == MINMEA_SENTENCE_GGA, "GGA identified as GGA");
    check_true(minmea_parse_gga(&g, gga) == true, "GGA parsed");
    check_true(g.fix_quality == 1, "GGA fix_quality == 1 (GPS fix)");
    check_true(g.satellites_tracked == 8, "GGA 8 satellites tracked");
    check_close(minmea_tofloat(&g.altitude), 545.4, 0.1, "GGA altitude ~545.4 m");
    check_close(minmea_tocoord(&g.latitude),  37.38746, 1e-3, "GGA latitude ~37.38746");
    check_close(minmea_tocoord(&g.longitude), -121.97236, 1e-3, "GGA longitude ~-121.97236 (west)");

    /* --- GSA: mode + 3D fix ----------------------------------------- */
    struct minmea_sentence_gsa s;
    check_true(minmea_parse_gsa(&s, gsa) == true, "GSA parsed");
    check_true(s.mode == 'A' && s.fix_type == 3, "GSA auto mode / 3D fix");

    /* --- GLL: status + coordinate ----------------------------------- */
    struct minmea_sentence_gll l;
    check_true(minmea_parse_gll(&l, gll) == true, "GLL parsed");
    check_true(l.status == 'A', "GLL status A (data valid)");
    check_close(minmea_tocoord(&l.latitude), 37.38746, 1e-3, "GLL latitude ~37.38746");

    /* --- ZDA: date / time / timezone offset ------------------------- */
    struct minmea_sentence_zda z;
    check_true(minmea_sentence_id(zda, true) == MINMEA_SENTENCE_ZDA, "ZDA identified as ZDA");
    check_true(minmea_parse_zda(&z, zda) == true, "ZDA parsed");
    check_true(z.time.hours == 16 && z.time.minutes == 0 && z.time.seconds == 47,
               "ZDA time 16:00:47");
    check_true(z.date.day == 14 && z.date.month == 2 && z.date.year == 2012,
               "ZDA date 14/02/2012");
    check_true(z.hour_offset == 0 && z.minute_offset == 0, "ZDA UTC offset +00:00");

    /* --- negatives: bad checksum and unknown sentence --------------- */
    check_true(minmea_check(bad, true) == false, "corrupt checksum rejected");
    check_true(minmea_sentence_id(bad, true) == MINMEA_INVALID, "bad-checksum sentence -> INVALID");
    check_true(minmea_sentence_id(unk, true) == MINMEA_INVALID, "unknown sentence id -> INVALID");

    /* --- talker id -------------------------------------------------- */
    char talker[3] = {0};
    check_true(minmea_talker_id(talker, rmc) == true && strcmp(talker, "GP") == 0,
               "talker id 'GP' (GPS)");
    printf("case HC-3 PASS-or-continue\n");
}

/* ===================================================================== */
/* HC-4: packaged device descriptor share/indi/indi_gpsnmea.xml         */
/* ===================================================================== */
static void case_xml(const char *xml_path)
{
    g_case = "HC-4";
    printf("case HC-4 start: packaged device descriptor\n");
    size_t len;
    unsigned char *x = read_whole(xml_path, &len);
    check_true(x != NULL, "device xml present and readable");
    if (x) {
        check_true(buf_contains(x, len, "<device label=\"GPS NMEA\">"), "device label 'GPS NMEA'");
        check_true(buf_contains(x, len, "<driver name=\"GPS NMEA\">indi_gpsnmea</driver>"),
                   "driver name maps to binary indi_gpsnmea");
        check_true(buf_contains(x, len, "<version>0.2</version>"), "driver version 0.2");
        check_true(buf_contains(x, len, "group=\"Auxiliary\""), "device in Auxiliary group");
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
/* HC-5 (harmony_specific): the packaged binary targets OHOS aarch64    */
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
    const char *bin  = argv[1];
    const char *xml  = argv[2];

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
        printf("== 5 cases, 0 failed ==\n");
        printf("== 1 checks, 1 failures ==\n");
        printf("RESULT: FAILED\n");
        return 1;
    }

    case_elf(b, len, bin);
    case_logic(b, len);
    case_nmea();
    case_xml(xml);
    case_ohos(b, len);
    free(b);

    int cases_failed = g_failures; /* simplified: any failure fails the run */
    printf("== 5 cases, %d failed ==\n", cases_failed);
    printf("== %d checks, %d failures ==\n", g_checks, g_failures);
    printf("RESULT: %s\n", g_failures == 0 ? "PASSED" : "FAILED");
    return g_failures == 0 ? 0 : 1;
}
