/* test_package for libhoel 1.4.29 — actually exercises the packaged library:
 * open a sqlite database file through hoel, create the fixture table, run a
 * json INSERT + SELECT round trip and verify the data round-trips. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <jansson.h>
#include <hoel.h>

int main(int argc, char ** argv) {
  struct _h_connection * conn = NULL;
  json_t * j_query = NULL, * j_result = NULL;
  const char * db_path = (argc > 1) ? argv[1] : "/tmp/test_hoel_pkg.db";
  int failed = 0;

  /* 1. connect (creates the sqlite file when missing) */
  conn = h_connect_sqlite(db_path);
  if (conn == NULL) {
    fprintf(stderr, "FAIL: h_connect_sqlite(%s)\n", db_path);
    return 1;
  }

  /* 2. fixture table (drop + create, hoel executes raw statements) */
  if (h_execute_query_sqlite(conn, "DROP TABLE IF EXISTS test_table;") != H_OK) {
    fprintf(stderr, "FAIL: drop table\n");
    return 1;
  }
  if (h_execute_query_sqlite(conn,
      "CREATE TABLE test_table (id_col INTEGER PRIMARY KEY AUTOINCREMENT,"
      " integer_col INTEGER, string_col TEXT);") != H_OK) {
    fprintf(stderr, "FAIL: create table\n");
    return 1;
  }

  /* 3. json INSERT */
  j_query = json_pack("{sss{siss}}",
                      "table", "test_table",
                      "values",
                        "integer_col", 4242,
                        "string_col", "hello harmonyos");
  if (h_insert(conn, j_query, NULL) != H_OK) {
    fprintf(stderr, "FAIL: h_insert\n");
    failed = 1;
    goto cleanup;
  }
  json_decref(j_query);

  /* 4. json SELECT and verify the round trip */
  j_query = json_pack("{sss[s]s{si}}",
                      "table", "test_table",
                      "columns", "string_col",
                      "where", "integer_col", 4242);
  if (h_select(conn, j_query, &j_result, NULL) != H_OK || j_result == NULL) {
    fprintf(stderr, "FAIL: h_select\n");
    failed = 1;
    goto cleanup;
  }
  if (!json_is_array(j_result) || json_array_size(j_result) != 1) {
    fprintf(stderr, "FAIL: unexpected result shape (rows=%d)\n",
            (int)(j_result ? json_array_size(j_result) : -1));
    failed = 1;
    goto cleanup;
  }
  {
    const char * value = json_string_value(
        json_object_get(json_array_get(j_result, 0), "string_col"));
    if (value == NULL || strcmp(value, "hello harmonyos") != 0) {
      fprintf(stderr, "FAIL: round trip value mismatch: %s\n",
              value ? value : "()");
      failed = 1;
      goto cleanup;
    }
    printf("round trip OK: integer_col=4242 string_col=%s\n", value);
  }
  json_decref(j_result);
  j_result = NULL;
  json_decref(j_query);
  j_query = NULL;

  /* 5. json DELETE + verify empty */
  j_query = json_pack("{sss{si}}", "table", "test_table", "where", "integer_col", 4242);
  if (h_delete(conn, j_query, NULL) != H_OK) {
    fprintf(stderr, "FAIL: h_delete\n");
    failed = 1;
    goto cleanup;
  }
  json_decref(j_query);
  j_query = json_pack("{sss[s]}", "table", "test_table", "columns", "string_col");
  if (h_select(conn, j_query, &j_result, NULL) != H_OK || j_result == NULL
      || json_array_size(j_result) != 0) {
    fprintf(stderr, "FAIL: table not empty after delete\n");
    failed = 1;
    goto cleanup;
  }
  printf("delete OK\n");

cleanup:
  if (j_query)  json_decref(j_query);
  if (j_result) json_decref(j_result);
  h_close_db(conn);
  h_clean_connection(conn);
  if (!failed) {
    printf("test_hoel: all checks passed\n");
    return 0;
  }
  return 1;
}
