#include <stdio.h>
#include <stdlib.h>
#include "duckdb.h"

int main(void) {
    duckdb_database db = NULL;
    duckdb_connection con = NULL;

    if (duckdb_open(NULL, &db) != DuckDBSuccess) {
        fprintf(stderr, "Failed to open database\n");
        return 1;
    }
    if (duckdb_connect(db, &con) != DuckDBSuccess) {
        fprintf(stderr, "Failed to connect\n");
        duckdb_close(&db);
        return 1;
    }

    duckdb_result res;
    if (duckdb_query(con, "SELECT 1 + 1 AS result", &res) != DuckDBSuccess) {
        fprintf(stderr, "Query failed: %s\n", duckdb_result_error(&res));
        duckdb_destroy_result(&res);
        duckdb_disconnect(&con);
        duckdb_close(&db);
        return 1;
    }

    int64_t val = duckdb_value_int64(&res, 0, 0);
    if (val != 2) {
        fprintf(stderr, "Expected 2, got %lld\n", (long long)val);
        duckdb_destroy_result(&res);
        duckdb_disconnect(&con);
        duckdb_close(&db);
        return 1;
    }

    duckdb_destroy_result(&res);

    /* Create table and insert data */
    if (duckdb_query(con, "CREATE TABLE t(id INTEGER, name VARCHAR)", &res) != DuckDBSuccess) {
        fprintf(stderr, "Create table failed: %s\n", duckdb_result_error(&res));
        duckdb_destroy_result(&res);
        duckdb_disconnect(&con);
        duckdb_close(&db);
        return 1;
    }
    duckdb_destroy_result(&res);

    if (duckdb_query(con, "INSERT INTO t VALUES (1, 'hello'), (2, 'world')", &res) != DuckDBSuccess) {
        fprintf(stderr, "Insert failed: %s\n", duckdb_result_error(&res));
        duckdb_destroy_result(&res);
        duckdb_disconnect(&con);
        duckdb_close(&db);
        return 1;
    }
    duckdb_destroy_result(&res);

    /* Query back */
    if (duckdb_query(con, "SELECT COUNT(*) FROM t", &res) != DuckDBSuccess) {
        fprintf(stderr, "Count query failed: %s\n", duckdb_result_error(&res));
        duckdb_destroy_result(&res);
        duckdb_disconnect(&con);
        duckdb_close(&db);
        return 1;
    }

    int64_t count = duckdb_value_int64(&res, 0, 0);
    if (count != 2) {
        fprintf(stderr, "Expected count 2, got %lld\n", (long long)count);
        duckdb_destroy_result(&res);
        duckdb_disconnect(&con);
        duckdb_close(&db);
        return 1;
    }

    duckdb_destroy_result(&res);
    duckdb_disconnect(&con);
    duckdb_close(&db);

    printf("DuckDB 1.2.0 test: PASS (all assertions passed)\n");
    return 0;
}
