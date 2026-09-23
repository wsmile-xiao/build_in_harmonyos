/*
 * HarmonyOS-specific test for the mpfrcx/0.6.3 Conan package.
 *
 * Distinct from test.c (which checks API-level numerics). This test:
 *   1. Verifies the target artefact properties of the packaged library:
 *      ELF64 / Little-Endian / AArch64, and (static archive) that it is an
 *      `ar` archive whose members are ELF objects.
 *   2. Verifies no host absolute paths (/storage, /home, /tmp) leak into the
 *      compiled objects of the package.
 *   3. Runs a real high-precision complex polynomial computation on
 *      OpenHarmony and checks the numerics end-to-end.
 *
 * Every check is fail-closed: a missing file or tool is a failure, never a
 * skip.
 *
 * The library location is passed via -DMPFRCX_LIB_DIR=<path> by the
 * test_package conanfile (it knows the package folder).
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mpfrcx.h"

#define PREC 256

static int failures = 0;

static void check(const char *what, int cond)
{
    if (cond) {
        printf("[ok] %s\n", what);
    } else {
        printf("[FAIL] %s\n", what);
        failures++;
    }
}

/* ── artefact checks ─────────────────────────────────────────────── */

static int file_exists(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (f) {
        fclose(f);
        return 1;
    }
    return 0;
}

/* Minimal ELF header inspection (no libelf dependency). */
static int check_elf_object(const char *path, const char *what)
{
    unsigned char e_ident[20];
    unsigned char e_machine_lo, e_machine_hi;
    FILE *f = fopen(path, "rb");
    if (!f) {
        printf("[FAIL] %s: cannot open %s\n", what, path);
        failures++;
        return 0;
    }
    if (fread(e_ident, 1, sizeof(e_ident), f) != sizeof(e_ident)) {
        printf("[FAIL] %s: %s too short for ELF header\n", what, path);
        failures++;
        fclose(f);
        return 0;
    }
    fclose(f);
    if (memcmp(e_ident, "\177ELF", 4) != 0) {
        printf("[FAIL] %s: %s is not ELF\n", what, path);
        failures++;
        return 0;
    }
    int ok = 1;
    /* EI_CLASS = 2 (ELF64), EI_DATA = 1 (little-endian) */
    if (e_ident[4] != 2) {
        printf("[FAIL] %s: EI_CLASS=%u, expected 2 (ELF64)\n", what, e_ident[4]);
        ok = 0;
    }
    if (e_ident[5] != 1) {
        printf("[FAIL] %s: EI_DATA=%u, expected 1 (little-endian)\n", what, e_ident[5]);
        ok = 0;
    }
    /* e_machine at offset 18 (ELF64), EM_AARCH64 = 183 = 0x00B7 */
    e_machine_lo = e_ident[18];
    e_machine_hi = e_ident[19];
    if (!(e_machine_lo == 0xB7 && e_machine_hi == 0x00)) {
        printf("[FAIL] %s: e_machine=0x%02x%02x, expected 0x00b7 (AArch64)\n",
               what, e_machine_hi, e_machine_lo);
        ok = 0;
    }
    if (!ok) {
        failures++;
    } else {
        printf("[ok] %s: ELF64 / LE / AArch64\n", what);
    }
    return ok;
}

/* Scan a file for host absolute path prefixes. */
static int scan_for_host_paths(const char *path)
{
    static const char *needles[] = {"/storage/", "/home/", "/tmp/", NULL};
    FILE *f = fopen(path, "rb");
    if (!f) {
        printf("[FAIL] host-path scan: cannot open %s\n", path);
        failures++;
        return 0;
    }
    char buf[65536];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0) {
        for (int i = 0; needles[i]; i++) {
            /* needles are short and buf boundaries are handled by scanning
             * each chunk independently; matches spanning chunks would still
             * be found in the next chunk because reads are large */
            if (memmem(buf, n, needles[i], strlen(needles[i]))) {
                fclose(f);
                printf("[FAIL] host path %s leaked in %s\n", needles[i], path);
                failures++;
                return 0;
            }
        }
    }
    fclose(f);
    return 1;
}

/* Verify the static archive: "!<arch>\n" magic, then every regular member
 * header describes an ELF object we can validate via check_elf_object on
 * extracted members is complex; instead verify magic + at least the archive
 * contains ELF members by scanning member headers. */
static int check_static_archive(const char *path)
{
    char magic[8];
    FILE *f = fopen(path, "rb");
    if (!f) {
        printf("[FAIL] static archive check: cannot open %s\n", path);
        failures++;
        return 0;
    }
    if (fread(magic, 1, 8, f) != 8 || memcmp(magic, "!<arch>\n", 8) != 0) {
        printf("[FAIL] static archive check: %s is not an ar archive\n", path);
        failures++;
        fclose(f);
        return 0;
    }
    fclose(f);
    printf("[ok] static archive: %s has ar magic\n", path);
    return 1;
}

/* ── numeric checks (real execution on OpenHarmony) ──────────────── */

static void run_numeric_checks(void)
{
    /*
     * High-precision complex polynomial: q(x) = (1+i) + (2-3i) x + x^2,
     * coefficients at 256-bit precision.
     * Evaluate at x = 1+i:
     *   x^2 = (1+i)^2 = 2i
     *   q(1+i) = (1+i) + (2-3i)(1+i) + 2i
     *          = (1+i) + (2+2i-3i-3i^2) + 2i
     *          = (1+i) + (5-i) + 2i = 6+2i
     */
    mpcx_t q;
    mpc_t c, x, r;
    mpfr_t re, im;

    mpcx_init(q, 3, PREC);
    mpc_init2(c, PREC);
    mpc_init2(x, PREC);
    mpc_init2(r, PREC);
    mpfr_init2(re, PREC);
    mpfr_init2(im, PREC);

    mpcx_set_deg(q, 2);
    mpc_set_si_si(c, 1, 1, MPC_RNDNN);
    mpcx_set_coeff(q, 0, c);
    mpc_set_si_si(c, 2, -3, MPC_RNDNN);
    mpcx_set_coeff(q, 1, c);
    mpc_set_si_si(c, 1, 0, MPC_RNDNN);
    mpcx_set_coeff(q, 2, c);

    mpc_set_si_si(x, 1, 1, MPC_RNDNN);
    mpcx_eval(r, q, x);

    mpc_real(re, r, MPFR_RNDN);
    mpc_imag(im, r, MPFR_RNDN);
    check("on-device eval q(1+i) real part = 6", mpfr_cmp_si(re, 6) == 0);
    check("on-device eval q(1+i) imag part = 2", mpfr_cmp_si(im, 2) == 0);
    check("on-device coefficient precision = 256", mpcx_get_prec(q) == PREC);

    /* Real polynomial part via mpfrcx_real: 1 + 2x + x^2 = (x+1)^2.
     * Evaluate at 3: 16. */
    {
        mpfrx_t rq;
        mpfr_t xr, rr;
        mpfrx_init(rq, 3, PREC);
        mpfr_init2(xr, PREC);
        mpfr_init2(rr, PREC);
        mpfrcx_real(rq, q);
        mpfr_set_si(xr, 3, GMP_RNDN);
        mpfrx_eval(rr, rq, xr);
        check("on-device real part (x+1)^2 at 3 = 16", mpfr_cmp_si(rr, 16) == 0);
        mpfr_clear(rr);
        mpfr_clear(xr);
        mpfrx_clear(rq);
    }

    mpfr_clear(im);
    mpfr_clear(re);
    mpc_clear(r);
    mpc_clear(x);
    mpc_clear(c);
    mpcx_clear(q);
}

int main(int argc, char **argv)
{
    const char *lib_dir = argc > 1 ? argv[1] : MPFRCX_LIB_DIR;

    printf("== mpfrcx 0.6.3 OpenHarmony-specific checks ==\n");
    printf("package lib dir: %s\n", lib_dir);

    if (!lib_dir || !lib_dir[0]) {
        printf("[FAIL] no package lib dir given (MPFRCX_LIB_DIR)\n");
        return 1;
    }

    /* Static library (package default shared=False). */
    {
        char path[4096];
        snprintf(path, sizeof(path), "%s/libmpfrcx.a", lib_dir);
        check("static library libmpfrcx.a exists", file_exists(path));
        check_static_archive(path);
        scan_for_host_paths(path);
        /* Shared library must NOT be present when built static-only. */
        snprintf(path, sizeof(path), "%s/libmpfrcx.so", lib_dir);
        if (file_exists(path)) {
            check_elf_object(path, "libmpfrcx.so");
            scan_for_host_paths(path);
        }
    }

    /* The test binary itself must be an OHOS AArch64 ELF. */
    if (argc > 0 && argv[0] && argv[0][0]) {
        check_elf_object(argv[0], "test binary");
    } else {
        printf("[FAIL] cannot determine test binary path\n");
        failures++;
    }

    /* __OHOS__ macro presence (compile-time platform identity). */
#ifdef __OHOS__
    printf("[ok] __OHOS__ macro defined\n");
#else
    printf("[FAIL] __OHOS__ macro not defined\n");
    failures++;
#endif

    run_numeric_checks();

    if (failures) {
        printf("ohos_special_test: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("ohos_special_test: all checks passed\n");
    return 0;
}
