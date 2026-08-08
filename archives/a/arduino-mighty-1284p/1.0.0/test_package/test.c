/*
 * Test program for arduino-mighty-1284p package.
 *
 * Includes <binary.h> from the Arduino core library (cores/standard/),
 * which defines binary literal constants (B0, B1, B10, B11111111, etc.).
 * Verifies that several constants have the expected decimal values.
 *
 * This header has no AVR-specific dependencies — it is pure C preprocessor
 * definitions, making it safe to include on any platform.
 */
#include <stdio.h>
#include <binary.h>

int main(void) {
    int errors = 0;

    /* Verify binary literal constants from binary.h */
    if (B0 != 0) { fprintf(stderr, "FAIL: B0 != 0\n"); errors++; }
    if (B1 != 1) { fprintf(stderr, "FAIL: B1 != 1\n"); errors++; }
    if (B10 != 2) { fprintf(stderr, "FAIL: B10 != 2\n"); errors++; }
    if (B11 != 3) { fprintf(stderr, "FAIL: B11 != 3\n"); errors++; }
    if (B1000 != 8) { fprintf(stderr, "FAIL: B1000 != 8\n"); errors++; }
    if (B11111111 != 255) { fprintf(stderr, "FAIL: B11111111 != 255\n"); errors++; }
    if (B10000000 != 128) { fprintf(stderr, "FAIL: B10000000 != 128\n"); errors++; }

    if (errors > 0) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", errors);
        return 1;
    }

    printf("test arduino-mighty-1284p 1.0.0: OK (binary.h constants verified)\n");
    return 0;
}
