#include <mjson.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

int main(void) {
  const char *json = "{\"name\":\"HarmonyOS\",\"values\":[1,2,3],\"ready\":true}";
  char name[32];
  double value = 0.0;
  int ready = 0;
  char output[64];

  if (mjson(json, (int) strlen(json), NULL, NULL) != (int) strlen(json)) return 1;
  if (mjson_get_string(json, (int) strlen(json), "$.name", name,
                       (int) sizeof(name)) != 9) return 2;
  if (strcmp(name, "HarmonyOS") != 0) return 3;
  if (!mjson_get_number(json, (int) strlen(json), "$.values[1]", &value)) return 4;
  if (fabs(value - 2.0) > 0.000001) return 5;
  if (!mjson_get_bool(json, (int) strlen(json), "$.ready", &ready) || ready != 1) return 6;
  if (mjson_snprintf(output, sizeof(output), "{%Q:%d}", "count", 3) <= 0) return 7;
  if (strcmp(output, "{\"count\":3}") != 0) return 8;

  puts("mjson consumer test passed");
  return 0;
}
