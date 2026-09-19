/* libsmartcols consumer test (R34): really exercise the table API —
 * scols_new_table → scols_table_new_column ×2 → scols_table_new_line ×2
 * → scols_line_sprintf (fill cells) → scols_print_table_to_string,
 * then assert the rendered table contains the expected cell strings.
 * Also checks scols_get_library_version (version consistency). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libsmartcols.h>

int main(void) {
    struct libscols_table *tb;
    struct libscols_column *cl0, *cl1;
    struct libscols_line *ln0, *ln1;
    char *data = NULL;
    const char *ver = NULL;
    int rc;

    /* 1) version API — scols_get_library_version() returns the numeric
     * release version (e.g. 2423 for 2.42.3), NOT an error code */
    rc = scols_get_library_version(&ver);
    if (rc < 0 || !ver) {
        fprintf(stderr, "FAIL: scols_get_library_version rc=%d\n", rc);
        return 1;
    }
    printf("libsmartcols version: %s (numeric %d)\n", ver, rc);
    if (rc < 2000 || rc > 2999) {
        fprintf(stderr, "FAIL: unexpected version number %d\n", rc);
        return 1;
    }

    /* 2) build a 2x2 table */
    tb = scols_new_table();
    if (!tb) { fprintf(stderr, "FAIL: scols_new_table\n"); return 1; }
    scols_table_set_name(tb, "ohos-tp-test");

    cl0 = scols_table_new_column(tb, "NAME", 0.3, 0);
    cl1 = scols_table_new_column(tb, "STATE", 0.7, 0);
    if (!cl0 || !cl1) { fprintf(stderr, "FAIL: new_column\n"); return 1; }

    ln0 = scols_table_new_line(tb, NULL);
    if (!ln0) { fprintf(stderr, "FAIL: new_line 0\n"); return 1; }
    if (scols_line_sprintf(ln0, 0, "%s", "libsmartcols") != 0 ||
        scols_line_sprintf(ln0, 1, "%s", "ok-on-ohos") != 0) {
        fprintf(stderr, "FAIL: scols_line_sprintf 0\n"); return 1;
    }

    ln1 = scols_table_new_line(tb, NULL);
    if (!ln1) { fprintf(stderr, "FAIL: new_line 1\n"); return 1; }
    if (scols_line_sprintf(ln1, 0, "%s", "consumer-test") != 0 ||
        scols_line_sprintf(ln1, 1, "%s", "passed") != 0) {
        fprintf(stderr, "FAIL: scols_line_sprintf 1\n"); return 1;
    }

    /* 3) render to string and assert */
    rc = scols_print_table_to_string(tb, &data);
    if (rc != 0 || !data) {
        fprintf(stderr, "FAIL: scols_print_table_to_string rc=%d\n", rc);
        return 1;
    }
    printf("---- rendered table ----\n%s------------------------\n", data);

    if (!strstr(data, "libsmartcols") || !strstr(data, "ok-on-ohos") ||
        !strstr(data, "consumer-test") || !strstr(data, "passed") ||
        !strstr(data, "NAME") || !strstr(data, "STATE")) {
        fprintf(stderr, "FAIL: rendered table missing expected cells\n");
        return 1;
    }

    free(data);
    scols_unref_table(tb);
    printf("OK: libsmartcols table render roundtrip on OHOS\n");
    return 0;
}
