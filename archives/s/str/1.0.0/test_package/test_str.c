#include <assert.h>
#include <string.h>

#include "str.h"

int main(void) {
  char buf[64];
  double value = 0;
  const char *json = "{\"name\":\"ohos\",\"value\":1.25}";
  int len = (int) strlen(json);

  assert(xsnprintf(buf, sizeof(buf), "%s %d", "str", 42) == 6);
  assert(strcmp(buf, "str 42") == 0);
  assert(json_get_num(json, len, "$.value", &value) == 1);
  assert(value == 1.25);
  assert(json_get_str(json, len, "$.name", buf, (int) sizeof(buf)) == 4);
  assert(strcmp(buf, "ohos") == 0);
  return 0;
}
