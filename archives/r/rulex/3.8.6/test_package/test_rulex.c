#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <lexdb.h>

static int checks = 0;

#define CHECK(condition, message)                                                \
  do {                                                                           \
    ++checks;                                                                     \
    if (!(condition)) {                                                           \
      fprintf(stderr, "check %d failed: %s\n", checks, message);                \
      return EXIT_FAILURE;                                                        \
    }                                                                             \
  } while (0)

int main(int argc, char **argv)
{
  const char key1[] = "\xC1";
  const char value1[] = "\xC1+";
  const char key2[] = "\xC5";
  const char value2[] = "\xC5+";
  char key[RULEXDB_BUFSIZE];
  char value[RULEXDB_BUFSIZE];
  RULEXDB *db;

  CHECK(argc == 2, "database path argument");
  db = rulexdb_open(argv[1], RULEXDB_CREATE);
  CHECK(db != NULL, "rulexdb_open create");
  CHECK(rulexdb_dataset_name(RULEXDB_EXCEPTION) != NULL, "dataset name");
  CHECK(strcmp(rulexdb_dataset_name(RULEXDB_EXCEPTION), "Exceptions") == 0,
        "exceptions dataset identity");
  CHECK(rulexdb_dataset_name(RULEXDB_DEFAULT) == NULL,
        "invalid dataset has no name");
  CHECK(rulexdb_subscribe_item(db, key1, value1, RULEXDB_EXCEPTION, 0) ==
            RULEXDB_SUCCESS,
        "subscribe first item");
  CHECK(rulexdb_subscribe_item(db, key1, value1, RULEXDB_EXCEPTION, 0) ==
            RULEXDB_SPECIAL,
        "duplicate rejection");
  CHECK(rulexdb_subscribe_item(db, key2, value2, RULEXDB_EXCEPTION, 0) ==
            RULEXDB_SUCCESS,
        "subscribe removable item");
  rulexdb_close(db);

  db = rulexdb_open(argv[1], RULEXDB_SEARCH);
  CHECK(db != NULL, "rulexdb_open search");
  CHECK(rulexdb_retrieve_item(db, key1, value, RULEXDB_EXCEPTION) ==
            RULEXDB_SUCCESS,
        "retrieve first item");
  CHECK(strcmp(value, value1) == 0, "retrieved pronunciation");
  CHECK(rulexdb_dataset_name(RULEXDB_LEXBASE) != NULL, "lexbase dataset name");
  CHECK(strcmp(rulexdb_dataset_name(RULEXDB_LEXBASE), "Lexbases") == 0,
        "lexbase dataset identity");
  CHECK(rulexdb_seq(db, key, value, RULEXDB_EXCEPTION_RAW, DB_FIRST) ==
            RULEXDB_SUCCESS,
        "sequential read");
  CHECK(strcmp(key, key1) == 0 && strcmp(value, value1) == 0,
        "sequential item content");
  rulexdb_close(db);

  db = rulexdb_open(argv[1], RULEXDB_UPDATE);
  CHECK(db != NULL, "rulexdb_open update");
  CHECK(rulexdb_remove_item(db, key2, RULEXDB_EXCEPTION) == RULEXDB_SUCCESS,
        "remove item");
  CHECK(rulexdb_retrieve_item(db, key2, value, RULEXDB_EXCEPTION) ==
            RULEXDB_SPECIAL,
        "removed item is absent");

  rulexdb_close(db);
  printf("rulex consumer API checks: %d passed\n", checks);
  return checks == 18 ? EXIT_SUCCESS : EXIT_FAILURE;
}
