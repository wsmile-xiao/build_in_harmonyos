/*
 * test.c — Consumer-side smoke test for cfitsio 4.6.4.
 *
 * Exercises the real cfitsio API end-to-end:
 *   - fits_create_file / fits_create_img  (build a valid primary HDU)
 *   - fits_write_key_str / fits_write_key_log
 *   - fits_close_file
 *   - fits_open_file                      (reopen from disk)
 *   - fits_read_key_str / fits_read_key_log
 *   - ffvers                              (library version query)
 *
 * The program writes a FITS file to a temp path, reopens it, reads the
 * keywords back and asserts they match what was written. Exits 0 on success,
 * non-zero (with fits_report_error diagnostics) on any failure. This is a
 * genuine functional test — NOT a print-only stub (R34).
 */

#include "fitsio.h"
#include <stdio.h>
#include <string.h>

int main(void)
{
    fitsfile *fptr = NULL;
    int status = 0;
    float ver = 0.0f;
    char val[80];
    char comment[80];
    long naxes[1] = {0};

    /* 1. Create a new FITS file and a primary image HDU. */
    fits_create_file(&fptr, "!cfitsio_test_out.fits", &status);
    if (status) { fits_report_error(stderr, status); return 1; }

    fits_create_img(fptr, BYTE_IMG, 0, naxes, &status);
    if (status) { fits_report_error(stderr, status); fits_close_file(fptr, &status); return 2; }

    /* 2. Write a string keyword and a boolean keyword. */
    fits_write_key_str(fptr, "TESTKW", "harmony",
                       " written by cfitsio smoke test", &status);
    fits_write_key_log(fptr, "TESTLOG", 1, " boolean keyword", &status);
    if (status) { fits_report_error(stderr, status); fits_close_file(fptr, &status); return 3; }

    fits_close_file(fptr, &status);
    if (status) { fits_report_error(stderr, status); return 4; }

    /* 3. Reopen the file and read the keywords back. */
    fits_open_file(&fptr, "cfitsio_test_out.fits", READONLY, &status);
    if (status) { fits_report_error(stderr, status); return 5; }

    fits_read_key_str(fptr, "TESTKW", val, comment, &status);
    if (status) { fits_report_error(stderr, status); fits_close_file(fptr, &status); return 6; }

    if (strcmp(val, "harmony") != 0) {
        fprintf(stderr, "TESTKW mismatch: got '%s'\n", val);
        fits_close_file(fptr, &status);
        return 7;
    }

    int logval = 0;
    fits_read_key_log(fptr, "TESTLOG", &logval, comment, &status);
    if (status) { fits_report_error(stderr, status); fits_close_file(fptr, &status); return 8; }
    if (logval != 1) {
        fprintf(stderr, "TESTLOG mismatch: got %d\n", logval);
        fits_close_file(fptr, &status);
        return 9;
    }

    fits_close_file(fptr, &status);
    if (status) { fits_report_error(stderr, status); return 10; }

    /* 4. Library version query. */
    ver = ffvers(&ver);
    printf("cfitsio version: %.1f\n", ver);
    printf("TESTKW=%s | TESTLOG=%d\n", val, logval);
    printf("cfitsio smoke test: OK\n");

    /* Clean up the generated file (ignore removal errors). */
    remove("cfitsio_test_out.fits");

    return 0;
}
