#include <dbi/dbi.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned int assertions;

#define CHECK(condition)                                                        \
    do {                                                                        \
        assertions++;                                                           \
        if (!(condition)) {                                                     \
            fprintf(stderr, "FAIL: %s at line %d\n", #condition, __LINE__);    \
            return 1;                                                           \
        }                                                                       \
    } while (0)

static void print_error(dbi_conn connection, const char *operation)
{
    const char *message = NULL;
    dbi_conn_error(connection, &message);
    fprintf(stderr, "%s failed: %s\n", operation, message ? message : "unknown error");
}

int main(int argc, char **argv)
{
    dbi_inst instance = NULL;
    dbi_driver driver;
    dbi_conn connection;
    dbi_result result;
    int loaded;

    if (argc != 3) {
        fprintf(stderr, "usage: %s <driver-directory> <database-directory>\n", argv[0]);
        return 2;
    }

    loaded = dbi_initialize_r(argv[1], &instance);
    CHECK(loaded == 1);
    CHECK(instance != NULL);

    driver = dbi_driver_open_r("sqlite3", instance);
    CHECK(driver != NULL);
    CHECK(strcmp(dbi_driver_get_name(driver), "sqlite3") == 0);
    CHECK(dbi_driver_get_filename(driver) != NULL);

    connection = dbi_conn_new_r("sqlite3", instance);
    CHECK(connection != NULL);
    CHECK(dbi_conn_set_option(connection, "sqlite3_dbdir", argv[2]) == 0);
    CHECK(dbi_conn_set_option(connection, "dbname", "libdbi-drivers-test.db") == 0);
    if (dbi_conn_connect(connection) < 0) {
        print_error(connection, "dbi_conn_connect");
        return 1;
    }

    result = dbi_conn_query(connection, "CREATE TABLE sample (value INTEGER, label TEXT)");
    CHECK(result != NULL);
    dbi_result_free(result);

    result = dbi_conn_query(connection, "INSERT INTO sample VALUES (42, 'ohos')");
    CHECK(result != NULL);
    dbi_result_free(result);

    result = dbi_conn_query(connection, "SELECT value, label FROM sample");
    CHECK(result != NULL);
    CHECK(dbi_result_get_numrows(result) == 1);
    CHECK(dbi_result_first_row(result) == 1);
    CHECK(dbi_result_get_longlong(result, "value") == 42);
    CHECK(strcmp(dbi_result_get_string(result, "label"), "ohos") == 0);
    dbi_result_free(result);

    dbi_conn_close(connection);
    dbi_shutdown_r(instance);
    printf("PASS: %u libdbi-drivers assertions\n", assertions);
    return 0;
}
