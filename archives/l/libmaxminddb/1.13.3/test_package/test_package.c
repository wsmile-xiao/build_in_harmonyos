/*
 * Conan test_package for libmaxminddb 1.13.3.
 *
 * Real MaxMind DB read flow, mirroring the upstream C test
 * t/basic_lookup_t.c (run_ipv4_tests -> test_one_ip -> test_one_result):
 *
 *   1. MMDB_open(data/MaxMind-DB-test-ipv4-28.mmdb, MMDB_MODE_MMAP, &mmdb)
 *   2. MMDB_lookup_string(&mmdb, "1.1.1.1", &gai_error, &mmdb_error)
 *        -> result.found_entry must be true
 *   3. MMDB_get_value(&result.entry, &value, "ip", NULL)
 *        -> the "ip" field of the found record == "1.1.1.1"
 *   4. MMDB_close(&mmdb)
 *
 * Every library call checks its return code against MMDB_SUCCESS; any
 * failure aborts with a non-zero exit code (so CI actually fails).
 */
#include <stdio.h>
#include <string.h>

#include "maxminddb.h"

#ifndef MMDB_TEST_DB_PATH
#define MMDB_TEST_DB_PATH "data/MaxMind-DB-test-ipv4-28.mmdb"
#endif

int main(void)
{
    MMDB_s mmdb;

    int status = MMDB_open(MMDB_TEST_DB_PATH, MMDB_MODE_MMAP, &mmdb);
    if (status != MMDB_SUCCESS) {
        fprintf(stderr, "FAIL: MMDB_open(%s) -> %s\n",
                MMDB_TEST_DB_PATH, MMDB_strerror(status));
        return 1;
    }

    int gai_error = 0;
    int mmdb_error = MMDB_SUCCESS;
    MMDB_lookup_result_s result =
        MMDB_lookup_string(&mmdb, "1.1.1.1", &gai_error, &mmdb_error);
    if (gai_error != 0) {
        fprintf(stderr, "FAIL: getaddrinfo(\"1.1.1.1\") -> %d\n", gai_error);
        MMDB_close(&mmdb);
        return 1;
    }
    if (mmdb_error != MMDB_SUCCESS) {
        fprintf(stderr, "FAIL: MMDB_lookup_string -> %s\n",
                MMDB_strerror(mmdb_error));
        MMDB_close(&mmdb);
        return 1;
    }
    if (!result.found_entry) {
        fprintf(stderr, "FAIL: IP 1.1.1.1 not found in the database\n");
        MMDB_close(&mmdb);
        return 1;
    }

    MMDB_entry_data_s value;
    status = MMDB_get_value(&result.entry, &value, "ip", NULL);
    if (status != MMDB_SUCCESS) {
        fprintf(stderr, "FAIL: MMDB_get_value(\"ip\") -> %s\n",
                MMDB_strerror(status));
        MMDB_close(&mmdb);
        return 1;
    }
    if (value.type != MMDB_DATA_TYPE_UTF8_STRING || value.data_size == 0) {
        fprintf(stderr, "FAIL: unexpected value type (%d) for field \"ip\"\n",
                (int)value.type);
        MMDB_close(&mmdb);
        return 1;
    }
    if (value.data_size != 7 ||
        strncmp(value.utf8_string, "1.1.1.1", (size_t)value.data_size) != 0) {
        fprintf(stderr, "FAIL: unexpected \"ip\" value: %.*s\n",
                (int)value.data_size, value.utf8_string);
        MMDB_close(&mmdb);
        return 1;
    }

    printf("libmaxminddb test PASSED: looked up 1.1.1.1 -> ip=%s\n",
           "1.1.1.1");

    MMDB_close(&mmdb);
    return 0;
}
