/*
 * crossdb 0.14.0 — consumer test_package (HarmonyOS PC).
 *
 * Drives the installed package exactly like a downstream consumer: connect,
 * DDL, DML, aggregation, ORDER BY, LIKE, UPDATE/DELETE plus two negative
 * cases, asserting on the row counts / column metadata / values that the
 * public API reports.
 *
 * Every CHECK() is counted and the process exits non-zero when any check
 * fails, so the Conan L1 gate and CI both see a real result instead of an
 * unconditional pass.
 */
#include <crossdb.h>
#include <stdio.h>
#include <string.h>

static int g_checks;
static int g_failed;

#define CHECK(cond, msg)                                                     \
	do {                                                                    \
		++g_checks;                                                       \
		if (cond) {                                                       \
			printf("[ ok ] %s\n", (msg));                              \
		} else {                                                          \
			++g_failed;                                                 \
			printf("[FAIL] %s (%s:%d)\n", (msg), __FILE__, __LINE__);   \
		}                                                                 \
	} while (0)

int main(void)
{
	xdb_conn_t *conn;
	xdb_res_t *res;
	xdb_row_t *row;
	const char *ver = xdb_version();
	int col_id, col_name;

	printf("crossdb consumer test (xdb_version=%s)\n", ver ? ver : "(null)");
	CHECK(ver != NULL && strcmp(ver, "0.14.0") == 0,
	      "xdb_version() reports 0.14.0");

	conn = xdb_open(":memory:");
	CHECK(conn != NULL, "xdb_open(\":memory:\") returns a connection");
	if (NULL == conn) {
		printf("consumer checks: %d/%d passed\n", g_checks - g_failed,
		       g_checks);
		return 1;
	}

	res = xdb_exec(conn,
	               "CREATE TABLE emp (id INT PRIMARY KEY, name CHAR(16), age TINYINT)");
	CHECK(xdb_errcode(res) == XDB_OK, "CREATE TABLE emp succeeds");

	res = xdb_exec(conn,
	               "CREATE TABLE emp (id INT PRIMARY KEY, name CHAR(16), age TINYINT)");
	CHECK(xdb_errcode(res) != XDB_OK, "duplicate CREATE TABLE is rejected");

	res = xdb_exec(conn, "INSERT INTO emp VALUES(1,'alice',31)");
	CHECK(xdb_errcode(res) == XDB_OK, "INSERT row 1");
	res = xdb_exec(conn, "INSERT INTO emp VALUES(2,'bob',28)");
	CHECK(xdb_errcode(res) == XDB_OK, "INSERT row 2");
	res = xdb_exec(conn, "INSERT INTO emp VALUES(3,'carol',35)");
	CHECK(xdb_errcode(res) == XDB_OK, "INSERT row 3");
	res = xdb_exec(conn, "INSERT INTO emp VALUES(4,'dave',28)");
	CHECK(xdb_errcode(res) == XDB_OK, "INSERT row 4");

	/* crossdb rejects a duplicate PRIMARY KEY by touching 0 rows (upstream
	 * test/xdb_smoke_dml.c:insert_dup asserts CHECK_AFFECT(pRes, 0)). */
	res = xdb_exec(conn, "INSERT INTO emp VALUES(1,'eve',22)");
	CHECK(xdb_affected_rows(res) == 0,
	      "duplicate PRIMARY KEY insert affects 0 rows");
	res = xdb_exec(conn, "SELECT COUNT(*) FROM emp");
	row = xdb_fetch_row(res);
	CHECK(row != NULL && xdb_column_int(res, row, 0) == 4,
	      "table still holds 4 rows after the rejected insert");

	res = xdb_exec(conn, "SELECT * FROM emp");
	CHECK(xdb_errcode(res) == XDB_OK, "SELECT * FROM emp succeeds");
	CHECK(xdb_row_count(res) == 4, "SELECT returns 4 rows");
	CHECK(xdb_column_count(res) == 3, "SELECT reports 3 columns");
	col_id = xdb_column_id(res, "id");
	col_name = xdb_column_id(res, "name");
	CHECK(col_id == 0 && col_name == 1, "column id/name resolve to 0/1");
	row = xdb_fetch_row(res);
	CHECK(row != NULL, "xdb_fetch_row returns the first row");
	if (row != NULL) {
		CHECK(xdb_column_int(res, row, col_id) == 1,
		      "first row id == 1");
		CHECK(strcmp(xdb_column_str(res, row, col_name), "alice") == 0,
		      "first row name == alice");
	}

	res = xdb_exec(conn, "SELECT id FROM emp ORDER BY id DESC");
	row = xdb_fetch_row(res);
	CHECK(row != NULL && xdb_column_int(res, row, 0) == 4,
	      "ORDER BY id DESC starts with id 4");

	res = xdb_exec(conn, "SELECT * FROM emp WHERE age = 28");
	CHECK(xdb_row_count(res) == 2, "WHERE age = 28 matches 2 rows");

	res = xdb_exec(conn, "SELECT * FROM emp WHERE name LIKE 'a%'");
	CHECK(xdb_row_count(res) == 1, "LIKE 'a%' matches 1 row");

	res = xdb_exec(conn, "SELECT * FROM emp WHERE name LIKE '%a%'");
	CHECK(xdb_row_count(res) == 3, "LIKE '%a%' matches 3 rows");

	res = xdb_exec(conn, "SELECT * FROM emp WHERE name LIKE 'da__'");
	CHECK(xdb_row_count(res) == 1, "LIKE 'da__' (underscore = one char) matches 1 row");

	res = xdb_exec(conn, "SELECT COUNT(*) FROM emp");
	row = xdb_fetch_row(res);
	CHECK(row != NULL && xdb_column_int(res, row, 0) == 4,
	      "COUNT(*) reports 4 rows");

	res = xdb_exec(conn, "UPDATE emp SET age = 40 WHERE id = 1");
	CHECK(xdb_affected_rows(res) == 1, "UPDATE affects 1 row");
	res = xdb_exec(conn, "SELECT age FROM emp WHERE id = 1");
	row = xdb_fetch_row(res);
	CHECK(row != NULL && xdb_column_int(res, row, 0) == 40,
	      "UPDATE persisted age = 40");

	res = xdb_exec(conn, "DELETE FROM emp WHERE age = 28");
	CHECK(xdb_affected_rows(res) == 2, "DELETE affects 2 rows");

	res = xdb_exec(conn, "SELECT * FROM emp");
	CHECK(xdb_row_count(res) == 2, "SELECT after DELETE returns 2 rows");

	res = xdb_exec(conn, "SELECT * FROM no_such_table");
	CHECK(xdb_errcode(res) != XDB_OK, "SELECT on a missing table fails");

	xdb_close(conn);

	printf("consumer checks: %d/%d passed\n", g_checks - g_failed, g_checks);
	return g_failed ? 1 : 0;
}
