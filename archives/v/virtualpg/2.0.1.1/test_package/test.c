#include <stdio.h>
#include <string.h>

#include <sqlite3.h>
#include <libpq-fe.h>
#include <virtualpg.h>

static int checks_run = 0;

#define CHECK(expression, message)                                             \
    do {                                                                       \
        ++checks_run;                                                          \
        if (!(expression)) {                                                   \
            fprintf(stderr, "check %d failed: %s\n", checks_run, (message)); \
            return checks_run;                                                 \
        }                                                                      \
    } while (0)

int main(void)
{
    sqlite3 *database = NULL;
    virtualPQ api = {
        .PQclear = PQclear,
        .PQconnectdb = PQconnectdb,
        .PQerrorMessage = PQerrorMessage,
        .PQexec = PQexec,
        .PQfinish = PQfinish,
        .PQgetisnull = PQgetisnull,
        .PQgetvalue = PQgetvalue,
        .PQlibVersion = PQlibVersion,
        .PQnfields = PQnfields,
        .PQntuples = PQntuples,
        .PQresultStatus = PQresultStatus,
        .PQstatus = PQstatus,
    };

    CHECK(strcmp(virtualpg_version(), "2.0.1") == 0,
          "unexpected VirtualPG version");
    CHECK(sqlite3_open(":memory:", &database) == SQLITE_OK,
          "cannot open an in-memory SQLite database");
    CHECK(virtualpg_extension_init(database, NULL) == SQLITE_ERROR,
          "NULL libpq vtable must be rejected");
    CHECK(virtualpg_extension_init(database, &api) == SQLITE_OK,
          "cannot register the VirtualPostgres module");
    CHECK(vpgPQlibVersion() == PQlibVersion(),
          "VirtualPG did not forward PQlibVersion");
    CHECK(PQlibVersion() >= 180000, "libpq 18.x or newer is required");
    CHECK(sqlite3_close(database) == SQLITE_OK,
          "cannot close the in-memory SQLite database");

    printf("virtualpg assertions: %d/7\n", checks_run);
    return 0;
}
