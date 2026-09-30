/* Installed-package contract test for kim-api 2.4.1: object lifecycle.
 *
 * Exercises the real KIM Collections and Log C APIs: Create/Destroy
 * round-trips. Every CHECK below is a genuine assertion against library
 * behavior (7 checkpoints); any failure exits nonzero so the harness
 * records a real failure instead of a silent pass.
 */
#include <stdio.h>

#include "KIM_Collections.h"
#include "KIM_Log.h"

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                \
  do {                                                  \
    ++checks;                                           \
    if (!(cond)) {                                      \
      printf("CHECK FAILED (%d): %s\n", checks, (msg)); \
      ++failures;                                       \
    }                                                   \
  } while (0)

int main(void)
{
  KIM_Collections *collections = NULL;
  KIM_Log *log = NULL;
  int error;

  error = KIM_Collections_Create(&collections);
  CHECK(error == 0, "Collections_Create returns success");
  CHECK(collections != NULL, "Collections_Create yields an object");

  KIM_Collections_Destroy(&collections);
  CHECK(collections == NULL, "Collections_Destroy nulls the handle");

  error = KIM_Log_Create(&log);
  CHECK(error == 0, "Log_Create returns success");
  CHECK(log != NULL, "Log_Create yields an object");

  KIM_Log_Destroy(&log);
  CHECK(log == NULL, "Log_Destroy nulls the handle");

  /* A second cycle proves the library state stays consistent. */
  error = KIM_Collections_Create(&collections);
  CHECK(error == 0 && collections != NULL, "Collections re-create works");
  KIM_Collections_Destroy(&collections);

  if (failures != 0) {
    printf("KIMAPI_COLLECTIONS_CONTRACT: FAIL (%d/%d checks failed)\n",
           failures, checks);
    return 1;
  }
  printf("KIMAPI_COLLECTIONS_CONTRACT: PASS (%d checks)\n", checks);
  return 0;
}
