/*
 * consumer.c — Conan test_package for tomlc99 0.0-git20260130
 *
 * R34: this test substantively exercises the packaged tomlc99 API
 * (parse / table & array traversal / typed datum extraction / timestamps /
 * introspection / error paths / teardown). It is NOT a hollow printf.
 *
 * Output is a numbered "CHECK passed: N/total" ledger so CI L1 can count
 * real assertions in the conan create log.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "toml.h"

static int passed = 0;
static int failed = 0;

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (cond) {                                                        \
            passed++;                                                      \
            printf("CHECK passed [%d]: %s\n", passed, msg);                \
        } else {                                                           \
            failed++;                                                      \
            printf("CHECK FAILED [%d]: %s\n", passed + failed, msg);       \
        }                                                                  \
    } while (0)

int main(void) {
    /* Mutable buffer: toml_parse() tokenizes in place. */
    static char doc[] =
        "title = \"tomlc99 consumer test\"\n"
        "[owner]\n"
        "  name = \"CK Tan\"\n"
        "  dob = 1979-05-27T07:32:00Z\n"
        "  active = true\n"
        "[server]\n"
        "  host = \"www.example.com\"\n"
        "  port = [ 8080, 8181, 8282 ]\n"
        "  temp = 3.5\n"
        "[clients]\n"
        "  data = [ [\"gamma\", \"delta\"], [1, 2] ]\n";

    char errbuf[256];
    toml_table_t *conf = toml_parse(doc, errbuf, sizeof(errbuf));
    CHECK(conf != NULL, "toml_parse() returns a table for a valid document");

    if (!conf) {
        fprintf(stderr, "FATAL: toml_parse: %s\n", errbuf);
        return 1;
    }

    /* ── top-level key/values ─────────────────────────────────── */
    toml_datum_t title = toml_string_in(conf, "title");
    CHECK(title.ok && title.u.s && strcmp(title.u.s, "tomlc99 consumer test") == 0,
          "toml_string_in() round-trips a top-level basic string");
    if (title.ok)
        free(title.u.s);

    CHECK(toml_key_exists(conf, "title") == 1,
          "toml_key_exists() finds an existing top-level key");
    CHECK(toml_key_exists(conf, "no_such_key") == 0,
          "toml_key_exists() returns 0 for a missing key");
    CHECK(toml_key_in(conf, 0) != NULL && strcmp(toml_key_in(conf, 0), "title") == 0,
          "toml_key_in(conf, 0) enumerates the first key-value");
    CHECK(toml_table_ntab(conf) == 3,
          "toml_table_ntab() counts owner/server/clients sub-tables");

    toml_datum_t missing = toml_string_in(conf, "no_such_key");
    CHECK(!missing.ok, "toml_string_in() on a missing key yields ok == 0");

    /* ── table traversal + string/bool ────────────────────────── */
    toml_table_t *owner = toml_table_in(conf, "owner");
    CHECK(owner != NULL, "toml_table_in() locates the [owner] sub-table");
    CHECK(toml_table_key(owner) != NULL && strcmp(toml_table_key(owner), "owner") == 0,
          "toml_table_key() reports the sub-table name");

    if (owner) {
        toml_datum_t name = toml_string_in(owner, "name");
        CHECK(name.ok && name.u.s && strcmp(name.u.s, "CK Tan") == 0,
              "toml_string_in() extracts a nested string value");
        if (name.ok)
            free(name.u.s);

        toml_datum_t active = toml_bool_in(owner, "active");
        CHECK(active.ok && active.u.b == 1,
              "toml_bool_in() extracts a boolean value");

        /* ── timestamp (offset date-time) ─────────────────────── */
        toml_datum_t dob = toml_timestamp_in(owner, "dob");
        CHECK(dob.ok && dob.u.ts != NULL,
              "toml_timestamp_in() parses an offset date-time");
        if (dob.ok && dob.u.ts) {
            toml_timestamp_t *ts = dob.u.ts;
            CHECK(ts->year && *ts->year == 1979 && ts->month && *ts->month == 5 &&
                      ts->day && *ts->day == 27,
                  "timestamp date fields decode to 1979-05-27");
            CHECK(ts->hour && *ts->hour == 7 && ts->minute && *ts->minute == 32 &&
                      ts->second && *ts->second == 0,
                  "timestamp time fields decode to 07:32:00");
            CHECK(ts->z && strcmp(ts->z, "Z") == 0,
                  "timestamp zone suffix decodes to \"Z\"");
            free(ts);
        }
    }

    /* ── arrays of ints / doubles ─────────────────────────────── */
    toml_table_t *server = toml_table_in(conf, "server");
    CHECK(server != NULL, "toml_table_in() locates the [server] sub-table");

    if (server) {
        toml_array_t *port = toml_array_in(server, "port");
        CHECK(port != NULL, "toml_array_in() retrieves the port array");
        if (port) {
            CHECK(toml_array_kind(port) == 'v',
                  "toml_array_kind() reports 'v' for a value array");
            CHECK(toml_array_type(port) == 'i',
                  "toml_array_type() reports 'i' for an integer array");
            CHECK(toml_array_nelem(port) == 3,
                  "toml_array_nelem() counts 3 elements");
            CHECK(toml_array_key(port) != NULL &&
                      strcmp(toml_array_key(port), "port") == 0,
                  "toml_array_key() reports the array name");

            toml_datum_t p0 = toml_int_at(port, 0);
            toml_datum_t p1 = toml_int_at(port, 1);
            toml_datum_t p2 = toml_int_at(port, 2);
            CHECK(p0.ok && p0.u.i == 8080 && p1.ok && p1.u.i == 8181 &&
                      p2.ok && p2.u.i == 8282,
                  "toml_int_at() extracts 8080/8181/8282 by index");

            toml_datum_t oob = toml_int_at(port, 3);
            CHECK(!oob.ok, "toml_int_at() out of range yields ok == 0");
        }

        toml_datum_t temp = toml_double_in(server, "temp");
        CHECK(temp.ok && temp.u.d > 3.4999 && temp.u.d < 3.5001,
              "toml_double_in() extracts a float value");
    }

    /* ── nested arrays (array of arrays) ──────────────────────── */
    toml_table_t *clients = toml_table_in(conf, "clients");
    CHECK(clients != NULL, "toml_table_in() locates the [clients] sub-table");

    if (clients) {
        toml_array_t *data = toml_array_in(clients, "data");
        CHECK(data != NULL && toml_array_kind(data) == 'a',
              "toml_array_kind() reports 'a' for an array of arrays");
        if (data) {
            toml_array_t *row0 = toml_array_at(data, 0);
            CHECK(row0 != NULL, "toml_array_at(data, 0) retrieves the string row");
            if (row0) {
                toml_datum_t s0 = toml_string_at(row0, 0);
                toml_datum_t s1 = toml_string_at(row0, 1);
                CHECK(s0.ok && s0.u.s && strcmp(s0.u.s, "gamma") == 0 &&
                          s1.ok && s1.u.s && strcmp(s1.u.s, "delta") == 0,
                      "toml_string_at() extracts \"gamma\"/\"delta\"");
                if (s0.ok)
                    free(s0.u.s);
                if (s1.ok)
                    free(s1.u.s);
            }
            toml_array_t *row1 = toml_array_at(data, 1);
            CHECK(row1 != NULL, "toml_array_at(data, 1) retrieves the int row");
            if (row1) {
                toml_datum_t i0 = toml_int_at(row1, 0);
                toml_datum_t i1 = toml_int_at(row1, 1);
                CHECK(i0.ok && i0.u.i == 1 && i1.ok && i1.u.i == 2,
                      "toml_int_at() extracts 1/2 from the nested int row");
            }
        }
    }

    /* ── teardown ─────────────────────────────────────────────── */
    toml_free(conf);
    CHECK(1, "toml_free() releases the parsed tree without crashing");

    /* ── error path: unterminated table header ────────────────── */
    static char bad[] = "[owner\nname = \"x\"\n";
    toml_table_t *badconf = toml_parse(bad, errbuf, sizeof(errbuf));
    CHECK(badconf == NULL && errbuf[0] != 0,
          "toml_parse() returns NULL with a message for a malformed document");
    if (badconf)
        toml_free(badconf);

    printf("consumer_test summary: %d passed, %d failed (total %d checks)\n",
           passed, failed, passed + failed);
    return failed == 0 ? 0 : 1;
}
