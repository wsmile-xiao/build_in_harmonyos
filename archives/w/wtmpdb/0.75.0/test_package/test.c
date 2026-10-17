/*
 * test_package consumer test for wtmpdb 0.75.0.
 * Exercises only version-script-exported public API (wtmpdb_login,
 * wtmpdb_logout, wtmpdb_read_all, wtmpdb_get_id) against a temp sqlite
 * database and asserts observable behavior: 6 checks, real assertions.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include "wtmpdb.h"

#define DB "hw3-consumer.db"
#define TTY "/dev/pts/hw9"

static int n_rows;
static int saw_login;      /* User+TTY+RemoteHost+Service all match, Logout NULL */
static int saw_logout_set; /* same row with non-NULL Logout field */

static int
row_cb(void *unused, int argc, char **argv, char **colnames)
{
  (void)unused; (void)colnames;
  if (argc != 8)
    return 1; /* ID Type User Login Logout TTY RemoteHost Service */
  n_rows++;
  if (strcmp(argv[2], "hw3user") == 0 && strcmp(argv[5], TTY) == 0)
    {
      if (argv[4] == NULL && strcmp(argv[6], "ohost") == 0
          && strcmp(argv[7], "svc-probe") == 0)
        saw_login++;
      if (argv[4] != NULL && atoi(argv[4]) > 0)
        saw_logout_set++;
    }
  return 0;
}

#define CHECK(cond, tag) do { \
    if (!(cond)) { fprintf(stderr, "FAIL %s\n", tag); return 1; } \
    printf("PASS %s\n", tag); } while (0)

int
main(void)
{
  char *error = NULL;
  remove(DB);

  int64_t id1 = wtmpdb_login(DB, USER_PROCESS, "hw3user",
                             1700000000000000ULL, TTY, "ohost",
                             "svc-probe", &error);
  CHECK(id1 >= 0, "1: wtmpdb_login returns valid id");

  int64_t got = wtmpdb_get_id(DB, TTY, &error);
  CHECK(got == id1, "2: wtmpdb_get_id finds open session id");

  n_rows = saw_login = 0;
  int rc = wtmpdb_read_all(DB, row_cb, &error);
  CHECK(rc == 0 && n_rows >= 1 && saw_login == 1,
        "3: read_all sees the login row with all fields");

  rc = wtmpdb_logout(DB, id1, 1700000009000000ULL, &error);
  CHECK(rc == 0, "4: wtmpdb_logout succeeds");

  got = wtmpdb_get_id(DB, TTY, &error);
  CHECK(got < 0, "5: get_id reports no open session after logout");

  n_rows = saw_logout_set = 0;
  rc = wtmpdb_read_all(DB, row_cb, &error);
  CHECK(rc == 0 && saw_logout_set == 1,
        "6: read_all row shows non-zero logout timestamp");

  remove(DB);
  printf("wtmpdb consumer test: 6/6 PASS\n");
  return 0;
}
