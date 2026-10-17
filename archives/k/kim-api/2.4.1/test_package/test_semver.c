/* Installed-package contract test for kim-api 2.4.1: version API.
 *
 * Exercises the real KIM_SEM_VER C API: GetSemVer, ParseSemVer and
 * IsLessThan. Every CHECK below is a genuine assertion against library
 * behavior (9 checkpoints); any failure exits nonzero so the harness
 * records a real failure instead of a silent pass.
 */
#include <stdio.h>
#include <string.h>

#include "KIM_SemVer.h"

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                   \
  do {                                                     \
    ++checks;                                              \
    if (!(cond)) {                                         \
      printf("CHECK FAILED (%d): %s\n", checks, (msg));    \
      ++failures;                                          \
    }                                                      \
  } while (0)

int main(void)
{
  const char *version;
  int major = -1, minor = -1, patch = -1;
  char prerelease[64];
  char buildMetadata[64];
  int error;
  int isLessThan = -1;

  version = KIM_SEM_VER_GetSemVer();
  CHECK(version != NULL, "GetSemVer returns non-NULL");
  CHECK(version != NULL && version[0] != '\0', "GetSemVer returns non-empty");
  CHECK(version != NULL && strstr(version, "2.4.1") != NULL,
        "GetSemVer reports 2.4.1");

  memset(prerelease, 0, sizeof(prerelease));
  memset(buildMetadata, 0, sizeof(buildMetadata));
  error = KIM_SEM_VER_ParseSemVer("2.4.1", (int) sizeof(prerelease),
                                  (int) sizeof(buildMetadata), &major, &minor,
                                  &patch, prerelease, buildMetadata);
  CHECK(error == 0, "ParseSemVer accepts 2.4.1");
  CHECK(major == 2 && minor == 4 && patch == 1,
        "ParseSemVer yields 2/4/1");

  major = minor = patch = -1;
  error = KIM_SEM_VER_ParseSemVer("not-a-version", (int) sizeof(prerelease),
                                  (int) sizeof(buildMetadata), &major, &minor,
                                  &patch, prerelease, buildMetadata);
  CHECK(error != 0, "ParseSemVer rejects invalid version");

  error = KIM_SEM_VER_IsLessThan("2.4.0", "2.4.1", &isLessThan);
  CHECK(error == 0, "IsLessThan runs cleanly");
  CHECK(isLessThan != 0, "2.4.0 < 2.4.1");

  isLessThan = -1;
  error = KIM_SEM_VER_IsLessThan("2.4.1", "2.4.0", &isLessThan);
  CHECK(error == 0 && isLessThan == 0, "2.4.1 is not < 2.4.0");

  if (failures != 0) {
    printf("KIMAPI_SEMVER_CONTRACT: FAIL (%d/%d checks failed)\n", failures,
           checks);
    return 1;
  }
  printf("KIMAPI_SEMVER_CONTRACT: PASS (%d checks)\n", checks);
  return 0;
}
