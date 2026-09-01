#include "sqlite3.h"
#include <stdio.h>
int main(void) {
    sqlite3 *db = NULL;
    int rc = sqlite3_open("test_analyzer.db", &db);
    if (rc != SQLITE_OK) { fprintf(stderr, "Cannot open: %s\n", sqlite3_errmsg(db)); return 1; }
    rc = sqlite3_exec(db, "CREATE TABLE t (id INTEGER, name TEXT); INSERT INTO t VALUES (1,'hello'), (2,'world'), (3,'sqlite');", NULL, NULL, NULL);
    if (rc != SQLITE_OK) { fprintf(stderr, "SQL error: %s\n", sqlite3_errmsg(db)); sqlite3_close(db); return 1; }
    sqlite3_close(db);
    printf("test_analyzer.db created successfully\n");
    return 0;
}
