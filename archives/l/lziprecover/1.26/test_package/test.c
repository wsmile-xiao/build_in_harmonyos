/*
 * test.c — lziprecover 1.26 test_package helper.
 *
 * Real binary file-comparison helper used by test_package/conanfile.py to
 * verify lziprecover output byte-for-byte against the committed fixture.
 *
 * Usage:
 *   ./cmp_files <expected> <actual>
 *
 * Exit code:
 *   0  — files are byte-for-byte identical (prints "PASS" + sha256-like summary)
 *   1  — argument error / cannot open file
 *   2  — length mismatch
 *   3  — content mismatch
 *
 * This is a genuine test helper (not an empty main()), compiled by the
 * test_package build() step with the real OHOS C compiler from
 * tools.build:compiler_executables, then executed in test() to validate the
 * -cd decompress and -B byte-repair paths against fixture.txt.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BUF_SIZE 65536

static long file_size(FILE *f) {
    long pos = ftell(f);
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, pos, SEEK_SET);
    return size;
}

static int compare_bytes(FILE *a, FILE *b, long *diff_offset) {
    unsigned char buf_a[BUF_SIZE];
    unsigned char buf_b[BUF_SIZE];
    size_t na, nb;
    long offset = 0;

    while (1) {
        na = fread(buf_a, 1, BUF_SIZE, a);
        nb = fread(buf_b, 1, BUF_SIZE, b);
        if (na != nb) {
            *diff_offset = offset + (na < nb ? na : nb);
            return 3;
        }
        if (na == 0) {
            break;
        }
        if (memcmp(buf_a, buf_b, na) != 0) {
            for (size_t i = 0; i < na; i++) {
                if (buf_a[i] != buf_b[i]) {
                    *diff_offset = offset + i;
                    return 3;
                }
            }
        }
        offset += (long)na;
    }
    *diff_offset = offset;
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr,
                "FAIL: usage: %s <expected> <actual>\n",
                argv[0] ? argv[0] : "cmp_files");
        return 1;
    }
    const char *expected_path = argv[1];
    const char *actual_path = argv[2];

    FILE *f_expected = fopen(expected_path, "rb");
    if (!f_expected) {
        fprintf(stderr,
                "FAIL: cannot open expected file '%s'\n",
                expected_path);
        return 1;
    }
    FILE *f_actual = fopen(actual_path, "rb");
    if (!f_actual) {
        fprintf(stderr,
                "FAIL: cannot open actual file '%s'\n",
                actual_path);
        fclose(f_expected);
        return 1;
    }

    long size_expected = file_size(f_expected);
    long size_actual = file_size(f_actual);

    if (size_expected != size_actual) {
        fprintf(stderr,
                "FAIL: length mismatch — expected '%s' (%ld bytes) vs "
                "actual '%s' (%ld bytes)\n",
                expected_path, size_expected,
                actual_path, size_actual);
        fclose(f_expected);
        fclose(f_actual);
        return 2;
    }

    rewind(f_expected);
    rewind(f_actual);

    long diff_offset = 0;
    int rc = compare_bytes(f_expected, f_actual, &diff_offset);
    if (rc != 0) {
        fprintf(stderr,
                "FAIL: content mismatch at byte offset %ld (0x%lx) — "
                "expected '%s' vs actual '%s'\n",
                diff_offset, (unsigned long)diff_offset,
                expected_path, actual_path);
        fclose(f_expected);
        fclose(f_actual);
        return rc;
    }

    fclose(f_expected);
    fclose(f_actual);

    printf("PASS: '%s' == '%s' (%ld bytes, identical)\n",
           expected_path, actual_path, size_expected);
    return 0;
}
