/*
 * test_silo_llnl.c — Silo 4.12.1 consumers smoke test.
 *
 * Exercises the real Silo public C API as a consumer would:
 *   - DBCreate / DBPutCurve / DBClose (write a curve)
 *   - DBOpen / DBGetCurve / DBFreeCurve / DBClose (read it back)
 *   - Verify the returned curve points byte-for-byte.
 *
 * This build is configured with SILO_ENABLE_HDF5=OFF (see conanfile.py: no
 * published conan HDF5 package is resolvable on the HarmonyOS build hosts),
 * so the round-trip runs on the PDB driver, which is always built into
 * libsilo.a.
 *
 * test 1: PDB driver (always built into libsilo)
 */

#include <stdio.h>
#include <stdlib.h>

#include <silo.h>

#define NPT 5

static int tests_run = 0;
static int tests_failed = 0;

static void fail_msg(const char *label)
{
    fprintf(stderr, "FAIL: %s\n", label);
    tests_failed++;
}

/* One curve write + read-back round-trip on the given driver + filename. */
static void run_roundtrip(int driver, const char *ext, const char *label)
{
    static const float x[NPT] = {0.0f, 1.0f, 2.0f, 3.0f, 4.0f};
    static const float y[NPT] = {0.0f, 1.0f, 4.0f, 9.0f, 16.0f};
    char fname[256];
    DBfile *dbfile;
    DBcurve *curve;
    int i;

    snprintf(fname, sizeof(fname), "test_%s.silo", ext);

    /* --- write --- */
    dbfile = DBCreate(fname, DB_CLOBBER, DB_LOCAL,
                      "silo-llnl 4.12.1 test_package", driver);
    if (!dbfile) {
        fail_msg(label);
        fprintf(stderr, "     DBCreate failed for %s\n", fname);
        return;
    }
    if (DBPutCurve(dbfile, "curve1", x, y, DB_FLOAT, NPT, NULL) < 0) {
        fail_msg(label);
        fprintf(stderr, "     DBPutCurve failed for %s\n", fname);
        DBClose(dbfile);
        return;
    }
    if (DBClose(dbfile) < 0) {
        fail_msg(label);
        fprintf(stderr, "     DBClose(write) failed for %s\n", fname);
        return;
    }

    /* --- read back --- */
    dbfile = DBOpen(fname, driver, DB_READ);
    if (!dbfile) {
        fail_msg(label);
        fprintf(stderr, "     DBOpen(read) failed for %s\n", fname);
        return;
    }
    curve = DBGetCurve(dbfile, "curve1");
    if (!curve) {
        fail_msg(label);
        fprintf(stderr, "     DBGetCurve failed for %s\n", fname);
        DBClose(dbfile);
        return;
    }
    if (curve->npts != NPT) {
        fail_msg(label);
        fprintf(stderr, "     npts mismatch (%d != %d) for %s\n",
                curve->npts, NPT, fname);
        DBFreeCurve(curve);
        DBClose(dbfile);
        return;
    }
    for (i = 0; i < NPT; i++) {
        float xv = ((float *)curve->x)[i];
        float yv = ((float *)curve->y)[i];
        if (xv != x[i] || yv != y[i]) {
            fail_msg(label);
            fprintf(stderr, "     point %d mismatch (x=%g y=%g) for %s\n",
                    i, xv, yv, fname);
            DBFreeCurve(curve);
            DBClose(dbfile);
            return;
        }
    }
    DBFreeCurve(curve);
    DBClose(dbfile);

    printf("PASS: %s curve round-trip (%s)\n", label, fname);
    tests_run++;   /* only counted on success, mirroring the summary */
}

int main(void)
{
    printf("silo-llnl 4.12.1 test_package\n");

    /* test 1: PDB driver (always built in) */
    run_roundtrip(DB_PDB, "pdb", "PDB");

    printf("Results: %d tests run, %d failed\n", tests_run, tests_failed);

    printf("HMBS_TEST_PACKAGE_RESULT="
           "{\"executed\":true,\"passed\":%s,"
           "\"command\":\"./test_silo_llnl\","
           "\"discovered\":1,\"passedCount\":%d}\n",
           (tests_failed == 0) ? "true" : "false",
           tests_run);

    return (tests_failed == 0) ? 0 : 1;
}
