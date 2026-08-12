#include <stdio.h>

#include <sqlite3.h>

#include "module_path.h"

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
    char *error = NULL;
    int load_result;

    CHECK(sqlite3_open(":memory:", &database) == SQLITE_OK,
          "cannot open an in-memory SQLite database");
    CHECK(sqlite3_enable_load_extension(database, 1) == SQLITE_OK,
          "cannot enable SQLite extension loading");
    load_result = sqlite3_load_extension(database, VIRTUALPG_MODULE_PATH,
                                         "sqlite3_modvirtualpg_init", &error);
    if (load_result != SQLITE_OK && error != NULL) {
        fprintf(stderr, "module load error: %s\n", error);
    }
    sqlite3_free(error);
    CHECK(load_result == SQLITE_OK, "cannot load mod_virtualpg.so");
    CHECK(sqlite3_close(database) == SQLITE_OK,
          "cannot close the in-memory SQLite database");

    printf("virtualpg module assertions: %d/4\n", checks_run);
    return 0;
}
