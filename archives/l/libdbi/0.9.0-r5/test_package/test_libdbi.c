#include <dbi/dbi.h>

#include <stdio.h>
#include <string.h>

static int assertions = 0;

#define CHECK(condition)                                                        \
    do {                                                                        \
        assertions++;                                                           \
        if (!(condition)) {                                                     \
            fprintf(stderr, "FAIL: %s at line %d\n", #condition, __LINE__);    \
            return 1;                                                           \
        }                                                                       \
    } while (0)

int main(int argc, char **argv) {
    dbi_inst instance = NULL;
    dbi_date date = {12, 31, 2026};
    dbi_time time = {23, 59, 58, 999, 28800};
    int loaded;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <empty-driver-directory>\n", argv[0]);
        return 2;
    }

    CHECK(strcmp(dbi_version(), "libdbi v0.9.0") == 0);
    CHECK(dbi_version_numeric() == 900U);
    CHECK(LIBDBI_VERSION == 900);
    CHECK(LIBDBI_LIB_CURRENT == 2);
    CHECK(LIBDBI_LIB_REVISION == 0);
    CHECK(LIBDBI_LIB_AGE == 1);
    CHECK(DBI_ERROR_USER == -10);
    CHECK(DBI_ERROR_NONE == 0);
    CHECK(DBI_TYPE_INTEGER == 1);
    CHECK(DBI_TYPE_DATETIME == 5);
    CHECK((DBI_INTEGER_SIZEMASK & DBI_INTEGER_SIZE8) != 0);

    loaded = dbi_initialize_r(argv[1], &instance);
    CHECK(loaded == 0);
    CHECK(instance != NULL);
    CHECK(dbi_set_verbosity_r(0, instance) == 1);
    CHECK(dbi_set_verbosity_r(1, instance) == 0);
    CHECK(dbi_driver_list_r(NULL, instance) == NULL);
    CHECK(dbi_driver_open_r("missing", instance) == NULL);
    CHECK(dbi_conn_new_r("missing", instance) == NULL);
    CHECK(dbi_driver_get_instance(NULL) == NULL);
    CHECK(dbi_driver_is_reserved_word(NULL, "select") == 0);
    CHECK(dbi_driver_specific_function(NULL, "missing") == NULL);

    CHECK(date.month == 12);
    CHECK(date.day == 31);
    CHECK(date.year == 2026);
    CHECK(time.hour == 23);
    CHECK(time.minute == 59);
    CHECK(time.second == 58);
    CHECK(time.millisecond == 999);
    CHECK(time.utc_offset == 28800);

    dbi_shutdown_r(instance);
    printf("PASS: %d libdbi API assertions\n", assertions);
    return 0;
}
