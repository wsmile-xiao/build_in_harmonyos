#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <kibi.h>

static int check_count = 0;

#define CHECK(cond, label) \
    do { \
        if (!(cond)) { \
            printf("CHECK %d FAILED: %s\n", check_count + 1, label); \
            return 1; \
        } \
        check_count++; \
        printf("CHECK %d OK: %s\n", check_count, label); \
    } while (0)

int main(void)
{
    char *s;
    char buf[64];
    int n;

    s = kibi_format_size(1024);
    CHECK(s != NULL && (strstr(s, "kB") != NULL || strstr(s, "KiB") != NULL || strstr(s, "KB") != NULL), "format_size(1024) has kilo unit");
    free(s);

    s = kibi_format_memory_size(536870912);
    CHECK(s != NULL && strstr(s, "512.0") != NULL, "format_memory_size(512MiB)");
    free(s);

    s = kibi_format_transfer_rate(12500000);
    CHECK(s != NULL && strlen(s) > 0, "format_transfer_rate non-empty");
    free(s);

    s = kibi_format_value(3830854, "X");
    CHECK(s != NULL && strlen(s) > 0, "format_value non-empty");
    free(s);

    CHECK(kibi_divide_size(9873498ULL, 1) > 9000.0, "divide_size level 1");
    CHECK(kibi_multiply_size(1.0, 2) == 1048576ULL || kibi_multiply_size(1.0, 2) == 1000000ULL,
        "multiply_size level 2 round-trips to mega");

    CHECK(kibi_get_unit_for_size(0) != NULL && strlen(kibi_get_unit_for_size(0)) > 0,
        "get_unit_for_size(0)");
    CHECK(kibi_get_unit_for_transfer_rate(1) != NULL
        && strlen(kibi_get_unit_for_transfer_rate(1)) > 0,
        "get_unit_for_transfer_rate(1)");

    n = kibi_n_format_size(buf, sizeof(buf), 4096);
    CHECK(n > 0 && strlen(buf) > 0, "n_format_size bounded call");

    printf("libkibi consumer: %d/9 checks passed\n", check_count);
    return 0;
}
