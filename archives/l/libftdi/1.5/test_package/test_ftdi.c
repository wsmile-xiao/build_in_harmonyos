/* libftdi 1.5 consumer test — offline API verification (no USB hardware).
 *
 * Environment constraint: OHOS PC sandbox has no USB subsystem access,
 * libusb_init(NULL) returns -1 (LIBUSB_ERROR_IO), therefore ftdi_new() /
 * ftdi_init() (upstream test fixture) cannot succeed offline. This test
 * only exercises the offline API surface:
 *
 *   - convert_baudrate_UT_export(): the upstream unit-test export wrapper
 *     for the pure computation ftdi_convert_baudrate(), checked against the
 *     OFFICIAL upstream vectors from test/baudrate.cpp (libftdi1-1.5) for
 *     chip types AM, BM/2232C/R/230X and 2232H/4232H/232H. Same assertion
 *     semantics as upstream (actual_baudrate, divisor, fractional_bits,
 *     clock). The stack-allocated ftdi_context only needs .type set —
 *     ftdi_convert_baudrate touches no USB state.
 *   - ftdi_get_library_version(): must report 1.5.
 *   - ftdi_get_error_string(NULL): documented error path, non-NULL result.
 *   - NULL-guard error paths on the public API: must return negative
 *     error codes, not crash.
 *   - OHOS-specific self-audit: ELF64 AArch64 ELF header check.
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <elf.h>

#include <libftdi1/ftdi.h>

extern int convert_baudrate_UT_export(int baudrate, struct ftdi_context *ftdi,
                                      unsigned short *value, unsigned short *index);

static int failures = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (cond) {                                                 \
            printf("[ok] %s\n", msg);                               \
        } else {                                                    \
            printf("[FAIL] %s (line %d)\n", msg, __LINE__);         \
            failures++;                                             \
        }                                                           \
    } while (0)

/* Upstream test/baudrate.cpp calc_result(actual, divisor, fractional_bits,
 * clock) — verbatim official vectors. */
struct vec {
    int requested;
    int actual;
    unsigned short divisor;
    unsigned short frac;
    unsigned short clock;
};

/* TypeAMFixedBaudrates — official upstream table */
static const struct vec vec_am[] = {
    {     183,      183, 16383, 0,  48 },
    {     300,      300, 10000, 0,  48 },
    {     600,      600,  5000, 0,  48 },
    {    1200,     1200,  2500, 0,  48 },
    {    2400,     2400,  1250, 0,  48 },
    {    4800,     4800,   625, 0,  48 },
    {    9600,     9600,   312, 1,  48 },
    {   19200,    19200,   156, 2,  48 },
    {   38400,    38400,    78, 3,  48 },
    {   57600,    57554,    52, 3,  48 },
    {  115200,   115385,    26, 0,  48 },
    {  230400,   230769,    13, 0,  48 },
    {  460800,   461538,     6, 1,  48 },
    {  921600,   923077,     3, 2,  48 },
    { 1000000,  1000000,     3, 0,  48 },
    { 1090512,  1000000,     3, 0,  48 },
    { 1090909,  1000000,     3, 0,  48 },
    { 1090910,  1000000,     3, 0,  48 },
    { 1200000,  1200000,     2, 1,  48 },
    { 1333333,  1333333,     2, 2,  48 },
    { 1411764,  1411765,     2, 3,  48 },
    { 1500000,  1500000,     2, 0,  48 },
    { 2000000,  1500000,     2, 0,  48 },
    { 3000000,  3000000,     0, 0,  48 },
};

/* TypeBMFixedBaudrates — official upstream table (shared by TYPE_BM,
 * TYPE_2232C, TYPE_R, TYPE_230X; representative subsets incl. the
 * sub-integer boundary rows). */
static const struct vec vec_bm[] = {
    {     183,      183, 16383, 7,  48 },
    {     184,      184, 16304, 4,  48 },
    {     300,      300, 10000, 0,  48 },
    {    9600,     9600,   312, 1,  48 },
    {  115200,   115385,    26, 0,  48 },
    { 1000000,  1000000,     3, 0,  48 },
    { 1050000,  1043478,     2, 7,  48 },
    { 1400000,  1411765,     2, 3,  48 },
    { 1500000,  1500000,     2, 0,  48 },
    { 2000000,  2000000,     1, 0,  48 },
    { 3000000,  3000000,     0, 0,  48 },
    /* sub-integer boundary rows: keys are the exact upstream C++ integer
     * expressions 3000000*16/(2*16+N) (and +/-1), values round(3000000/d) */
    { 1021275,  1000000,     3, 0,  48 }, /* (3000000*16/(2*16+15))-1 */
    { 1021276,  1000000,     3, 0,  48 }, /*  3000000*16/(2*16+15)    */
    { 1021277,  1043478,     2, 7,  48 }, /* +1                       */
    { 1066666,  1043478,     2, 7,  48 }, /*  3000000*16/(2*16+13)    */
    { 1066667,  1090909,     2, 6,  48 }, /* +1                       */
    { 1116279,  1090909,     2, 6,  48 }, /*  3000000*16/(2*16+11)    */
    { 1116280,  1142857,     2, 5,  48 }, /* +1                       */
    { 1170731,  1142857,     2, 5,  48 }, /*  3000000*16/(2*16+ 9)    */
    { 1170732,  1200000,     2, 1,  48 }, /* +1                       */
    { 1230769,  1200000,     2, 1,  48 }, /*  3000000*16/(2*16+ 7)    */
    { 1230770,  1263158,     2, 4,  48 }, /* +1                       */
    { 1297297,  1263158,     2, 4,  48 }, /*  3000000*16/(2*16+ 5)    */
    { 1297298,  1333333,     2, 2,  48 }, /* +1                       */
    { 1371428,  1333333,     2, 2,  48 }, /*  3000000*16/(2*16+ 3)    */
    { 1371429,  1411765,     2, 3,  48 }, /* +1                       */
    { 1454545,  1411765,     2, 3,  48 }, /*  3000000*16/(2*16+ 1)    */
    { 1454546,  1500000,     2, 0,  48 }, /* +1                       */
};

/* TypeHFixedBaudrates — official upstream table (TYPE_2232H, TYPE_4232H,
 * TYPE_232H; representative subset incl. 12 MHz boundary rows). */
static const struct vec vec_h[] = {
    {     183,      183, 16383, 7,  48 },
    {     184,      184, 16304, 4,  48 },
    {     300,      300, 10000, 0,  48 },
    {    1200,     1200, 10000, 0, 120 },
    {    9600,     9600,  1250, 0, 120 },
    {   57600,    57588,   208, 4, 120 },
    {  115200,   115246,   104, 3, 120 },
    { 1000000,  1000000,    12, 0, 120 },
    { 4173913,  4173913,     2, 7, 120 },
    { 6000000,  6000000,     2, 0, 120 },
    { 8000000,  8000000,     1, 0, 120 },
    {12000000, 12000000,     0, 0, 120 },
    /* sub-integer boundary rows: keys are the exact upstream C++ integer
     * expressions 12000000*16/(2*16+N) (and +/-1), values round(12000000/d) */
    { 4085105,  4000000,     3, 0, 120 }, /* (12000000*16/(2*16+15))-1 */
    { 4085106,  4000000,     3, 0, 120 }, /*  12000000*16/(2*16+15)    */
    { 4085107,  4173913,     2, 7, 120 }, /* +1                        */
    { 4266666,  4173913,     2, 7, 120 }, /*  12000000*16/(2*16+13)    */
    { 4266667,  4363636,     2, 6, 120 }, /* +1                        */
    { 4465116,  4363636,     2, 6, 120 }, /*  12000000*16/(2*16+11)    */
    { 4465117,  4571429,     2, 5, 120 }, /* +1                        */
    { 4682926,  4571429,     2, 5, 120 }, /*  12000000*16/(2*16+ 9)    */
    { 4682927,  4800000,     2, 1, 120 }, /* +1                        */
    { 4923076,  4800000,     2, 1, 120 }, /*  12000000*16/(2*16+ 7)    */
    { 4923077,  5052632,     2, 4, 120 }, /* +1                        */
    { 5189189,  5052632,     2, 4, 120 }, /*  12000000*16/(2*16+ 5)    */
    { 5189190,  5333333,     2, 2, 120 }, /* +1                        */
    { 5485714,  5333333,     2, 2, 120 }, /*  12000000*16/(2*16+ 3)    */
    { 5485715,  5647059,     2, 3, 120 }, /* +1                        */
    { 5818181,  5647059,     2, 3, 120 }, /*  12000000*16/(2*16+ 1)    */
    { 5818182,  6000000,     2, 0, 120 }, /* +1                        */
};

/* Replicates upstream test_baudrates() assertions (BOOST_CHECK_EQUAL x4)
 * for one chip type. */
static int check_vec(enum ftdi_chip_type type, const struct vec *vecs,
                     size_t n, const char *label)
{
    struct ftdi_context ctx;
    int vec_fail = 0;

    memset(&ctx, 0, sizeof ctx);
    ctx.type = type;

    for (size_t i = 0; i < n; i++) {
        unsigned short value = 0, index = 0;
        int calc_baud = convert_baudrate_UT_export(vecs[i].requested, &ctx,
                                                   &value, &index);
        unsigned short divisor = value & 0x3fff;
        unsigned short frac = (value >> 14);
        unsigned short clock = (index & 0x200) ? 120 : 48;

        switch (type) {
        case TYPE_232H:
        case TYPE_2232H:
        case TYPE_4232H:
            frac |= (index & 0x100) ? 4 : 0;
            break;
        case TYPE_R:
        case TYPE_2232C:
        case TYPE_BM:
        case TYPE_230X:
            frac |= (index & 0x001) ? 4 : 0;
            break;
        default:
            break;
        }

        if (vecs[i].actual != calc_baud || vecs[i].divisor != divisor ||
            vecs[i].frac != frac || vecs[i].clock != clock) {
            printf("[FAIL] %s baud %d: calc=(%d,%u,%u,%u) expect=(%d,%u,%u,%u)\n",
                   label, vecs[i].requested,
                   calc_baud, divisor, frac, clock,
                   vecs[i].actual, vecs[i].divisor, vecs[i].frac, vecs[i].clock);
            vec_fail++;
        }
    }
    printf("[baud] %-7s %zu official upstream vectors, %d mismatched\n",
           label, n, vec_fail);
    return vec_fail;
}

int main(int argc, char **argv)
{
    int self_check_elf = (argc > 1 && strcmp(argv[1], "--self-elf-check") == 0);

    if (self_check_elf) {
        /* OHOS-specific self-audit: parse own ELF header, require
         * ELFCLASS64 + EM_AARCH64. */
        int ok = 0;
        FILE *f = fopen("/proc/self/exe", "rb");
        if (f) {
            Elf64_Ehdr hdr;
            if (fread(&hdr, 1, sizeof hdr, f) == sizeof hdr) {
                int class_ok = hdr.e_ident[EI_CLASS] == ELFCLASS64;
                int machine_ok = hdr.e_machine == EM_AARCH64;
                printf("[elf] EI_CLASS=%d (expect 2/ELFCLASS64) e_machine=%d (expect %d/EM_AARCH64)\n",
                       hdr.e_ident[EI_CLASS], hdr.e_machine, EM_AARCH64);
                ok = class_ok && machine_ok;
            }
            fclose(f);
        }
        CHECK(ok, "OHOS: ELF64 AArch64 executable self-audit");
    }

    /* --- ftdi_get_library_version: offline, no USB --- */
    struct ftdi_version_info v = ftdi_get_library_version();
    printf("[ver] %d.%d.%d %s\n", v.major, v.minor, v.micro, v.version_str);
    CHECK(v.major == 1 && v.minor == 5, "ftdi_get_library_version reports 1.5");
    CHECK(v.version_str && strncmp(v.version_str, "1.5", 3) == 0,
          "version string starts with 1.5");

    /* --- ftdi_get_error_string: documented error path --- */
    const char *err = ftdi_get_error_string(NULL);
    CHECK(err != NULL, "ftdi_get_error_string(NULL) returns non-NULL message");

    /* --- official upstream baudrate vectors (pure computation) --- */
    int vec_fail = 0;
    vec_fail += check_vec(TYPE_AM, vec_am, sizeof vec_am / sizeof vec_am[0], "TYPE_AM");
    for (int t = 0; t < 4; t++) {
        static const enum ftdi_chip_type bm_types[4] =
            { TYPE_BM, TYPE_2232C, TYPE_R, TYPE_230X };
        static const char *bm_labels[4] =
            { "TYPE_BM", "TYPE_2232C", "TYPE_R", "TYPE_230X" };
        vec_fail += check_vec(bm_types[t], vec_bm,
                              sizeof vec_bm / sizeof vec_bm[0], bm_labels[t]);
    }
    for (int t = 0; t < 3; t++) {
        static const enum ftdi_chip_type h_types[3] =
            { TYPE_2232H, TYPE_4232H, TYPE_232H };
        static const char *h_labels[3] =
            { "TYPE_2232H", "TYPE_4232H", "TYPE_232H" };
        vec_fail += check_vec(h_types[t], vec_h,
                              sizeof vec_h / sizeof vec_h[0], h_labels[t]);
    }
    CHECK(vec_fail == 0, "all official upstream baudrate vectors match");

    /* --- error paths: NULL/invalid input must return negative codes --- */
    CHECK(ftdi_set_interface(NULL, INTERFACE_ANY) < 0,
          "ftdi_set_interface(NULL) returns negative");
    CHECK(ftdi_set_baudrate(NULL, 115200) < 0,
          "ftdi_set_baudrate(NULL) returns negative");
    CHECK(ftdi_write_data(NULL, (unsigned char *)"", 0) < 0,
          "ftdi_write_data(NULL) returns negative");
    CHECK(ftdi_read_data(NULL, (unsigned char *)"", 0) < 0,
          "ftdi_read_data(NULL) returns negative");
    CHECK(ftdi_write_data_get_chunksize(NULL, NULL) < 0,
          "ftdi_write_data_get_chunksize(NULL) returns negative");

    if (failures == 0) {
        printf("ALL OFFLINE TESTS PASSED\n");
        return 0;
    }
    printf("%d TEST FAILURE(S)\n", failures);
    return 1;
}
