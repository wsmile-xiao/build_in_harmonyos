#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <traildb.h>

/* 7 real checks against the public C API:
 * 1 cons_init, 2 cons_open, 3 cons_add, 4 cons_finalize,
 * 5 tdb_open, 6 num_trails, 7 cursor read + value check.
 *
 * NOTE: tdb_error is an enum type, not a getter function. All fallible
 * APIs return tdb_error directly; diagnostics use tdb_error_str(err).
 * There is no tdb_cons_error() nor tdb_error(db) in src/traildb.h /
 * src/tdb_error.h (verified against tag 0.6).
 *
 * NOTE: tdb_num_fields() counts the implicit "time" field plus user
 * fields (src/tdb.c fields_open: db->num_fields = num_ofields + 1).
 * With 2 ofields ("f1","f2") the correct expectation is 3, not 2.
 */
static void remove_stale_tdb(const char *path) {
    /* cons_open does mkdir(root) opportunistically and finalize
     * overwrites files, but a stale dir from a previous ctest run
     * (or a partially finalised DB) makes reruns non-hermetic.
     * Remove both "root" and "root.tdb" spellings before creating. */
    char cmd[2300];
    snprintf(cmd, sizeof(cmd), "rm -rf \"%s\" \"%s.tdb\"", path, path);
    (void)system(cmd);
    /* Also cover the case where path already ends in .tdb: the above
     * removes path itself; the second arg is harmless. */
}
int main(void) {
    const char *root = getenv("TDB_TEST_ROOT");
    char path[1024];
    if (root == NULL || root[0] == '\0') {
        root = "tdb_consumer_test";
    }
    snprintf(path, sizeof(path), "%s.tdb", root);
    remove_stale_tdb(path);

    static uint8_t uuid[16] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
    const char *fields[] = {"f1", "f2"};
    const char *values[] = {"hello", "world"};
    const uint64_t lengths[] = {5, 5};
    tdb_error err;

    /* 1: cons_init */
    tdb_cons *cons = tdb_cons_init();
    if (cons == NULL) {
        fprintf(stderr, "FAIL 1: tdb_cons_init returned NULL\n");
        return 1;
    }
    printf("PASS 1: tdb_cons_init\n");

    /* 2: cons_open */
    err = tdb_cons_open(cons, path, fields, 2);
    if (err != 0) {
        fprintf(stderr, "FAIL 2: tdb_cons_open %s: %s\n", path, tdb_error_str(err));
        return 1;
    }
    printf("PASS 2: tdb_cons_open %s\n", path);

    /* 3: cons_add */
    err = tdb_cons_add(cons, uuid, 1442421600, values, lengths);
    if (err != 0) {
        fprintf(stderr, "FAIL 3: tdb_cons_add: %s\n", tdb_error_str(err));
        return 1;
    }
    printf("PASS 3: tdb_cons_add\n");

    /* 4: cons_finalize */
    err = tdb_cons_finalize(cons);
    if (err != 0) {
        fprintf(stderr, "FAIL 4: tdb_cons_finalize: %s\n", tdb_error_str(err));
        return 1;
    }
    printf("PASS 4: tdb_cons_finalize\n");

    /* 5: tdb_open */
    tdb *db = tdb_init();
    if (db == NULL) {
        fprintf(stderr, "FAIL 5a: tdb_init returned NULL\n");
        return 1;
    }
    err = tdb_open(db, path);
    if (err != 0) {
        fprintf(stderr, "FAIL 5b: tdb_open: %s\n", tdb_error_str(err));
        return 1;
    }
    printf("PASS 5: tdb_open\n");

    /* 6: num_trails */
    if (tdb_num_trails(db) != 1) {
        fprintf(stderr, "FAIL 6: tdb_num_trails=%llu want 1\n",
                (unsigned long long)tdb_num_trails(db));
        return 1;
    }
    if (tdb_num_fields(db) != 3) {
        fprintf(stderr, "FAIL 6b: tdb_num_fields=%llu want 3 (time+f1+f2)\n",
                (unsigned long long)tdb_num_fields(db));
        return 1;
    }
    printf("PASS 6: num_trails=1 num_fields=3\n");

    /* 7: cursor read + value check */
    tdb_cursor *cursor = tdb_cursor_new(db);
    if (cursor == NULL) {
        fprintf(stderr, "FAIL 7a: tdb_cursor_new returned NULL\n");
        return 1;
    }
    err = tdb_get_trail(cursor, 0);
    if (err != 0) {
        fprintf(stderr, "FAIL 7b: tdb_get_trail: %s\n", tdb_error_str(err));
        return 1;
    }
    const tdb_event *event = tdb_cursor_next(cursor);
    if (event == NULL) {
        fprintf(stderr, "FAIL 7c: tdb_cursor_next returned NULL\n");
        return 1;
    }
    if (event->timestamp != 1442421600) {
        fprintf(stderr, "FAIL 7d: timestamp=%llu want 1442421600\n",
                (unsigned long long)event->timestamp);
        return 1;
    }
    if (event->num_items != 2) {
        fprintf(stderr, "FAIL 7e: num_items=%llu want 2\n",
                (unsigned long long)event->num_items);
        return 1;
    }
    uint64_t len = 0;
    const char *v0 = tdb_get_item_value(db, event->items[0], &len);
    if (v0 == NULL || len != 5 || memcmp(v0, "hello", 5) != 0) {
        fprintf(stderr, "FAIL 7f: item0 value mismatch\n");
        return 1;
    }
    printf("PASS 7: cursor read timestamp + hello/world\n");

    tdb_cursor_free(cursor);
    tdb_close(db);

    printf("test traildb 0.6: OK (7/7)\n");
    return 0;
}
