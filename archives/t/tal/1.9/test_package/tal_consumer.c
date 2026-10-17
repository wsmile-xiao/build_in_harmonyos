/*
 * tal_consumer.c - HarmonyOS PC consumer program for tal 1.9.
 *
 * Build pipeline (test_package/conanfile.py):
 *   1. a ragged X-macro header is generated,
 *   2. the packaged bin/tal aligns its continuation backslashes,
 *   3. this program is compiled against the tal output with the OHOS
 *      toolchain, and
 *   4. run with the path of that header.
 *
 * At run time the program lints the header it was built from (every
 * continuation backslash in one column, no line split), then uses the
 * compiled-in error table: counts entries, sums values, and looks up
 * E_BLOB, whose value is the length of a string on a 3000-column line.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#include "error_table.h"

struct error_entry {
    const char *name;
    long value;
};

#define AS_ENTRY(name, value) { #name, (long)(value) },
static const struct error_entry table[] = { ERROR_TABLE(AS_ENTRY) };

static int lint_header(const char *path, size_t *continuations, size_t *column)
{
    FILE *fp = fopen(path, "r");
    char *line = NULL;
    size_t cap = 0, lineno = 0, misaligned = 0;
    ssize_t len;

    if (fp == NULL) {
        perror(path);
        return 1;
    }
    *continuations = 0;
    *column = 0;
    while ((len = getline(&line, &cap, fp)) != -1) {
        ++lineno;
        if (len > 0 && line[len - 1] == '\n')
            line[--len] = '\0';
        if (len == 0 || line[len - 1] != '\\')
            continue;
        if (*continuations == 0) {
            *column = (size_t) len;
        } else if ((size_t) len != *column && misaligned++ == 0) {
            fprintf(stderr, "%s:%zu: continuation at column %zd, expected %zu\n",
                    path, lineno, len, *column);
        }
        ++*continuations;
    }
    free(line);
    fclose(fp);
    if (misaligned != 0)
        fprintf(stderr, "%zu misaligned continuation lines\n", misaligned);
    return misaligned != 0;
}

int main(int argc, char *argv[])
{
    const size_t count = sizeof(table) / sizeof(table[0]);
    size_t continuations, column, i;
    long sum = 0, blob = -1;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <aligned error_table.h>\n", argv[0]);
        return 2;
    }
    if (lint_header(argv[1], &continuations, &column) != 0)
        return 1;

    for (i = 0; i < count; i++) {
        sum += table[i].value;
        if (strcmp(table[i].name, "E_BLOB") == 0)
            blob = table[i].value;
    }

    printf("tal consumer: header %zu continuation lines aligned at column %zu\n",
           continuations, column);
    printf("tal consumer: %zu error codes, value sum %ld, E_BLOB=%ld\n", count, sum, blob);

    if (continuations != EXPECTED_CONTINUATIONS || column <= EXPECTED_MIN_COLUMN) {
        fprintf(stderr, "header layout unexpected (want %d lines past column %d)\n",
                EXPECTED_CONTINUATIONS, EXPECTED_MIN_COLUMN);
        return 1;
    }
    if (count != EXPECTED_COUNT || sum != EXPECTED_SUM || blob != EXPECTED_BLOB) {
        fprintf(stderr, "error table unexpected (want %d / %ld / %d)\n",
                EXPECTED_COUNT, (long) EXPECTED_SUM, EXPECTED_BLOB);
        return 1;
    }
    printf("tal consumer: OK\n");
    return 0;
}
