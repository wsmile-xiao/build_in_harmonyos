#include <stdio.h>
#include <string.h>

#include "minIni.h"

#define CHECK(expr) do { \
  if (!(expr)) { \
    fprintf(stderr, "CHECK failed at %s:%d: %s\n", __FILE__, __LINE__, #expr); \
    return 1; \
  } \
} while (0)

static int browse_count;

static int count_entry(const char *section, const char *key,
                       const char *value, void *userdata)
{
  (void)section;
  (void)key;
  (void)value;
  (void)userdata;
  browse_count++;
  return 1;
}
int main(void)
{
  const char *filename = "libminini-consumer-c.ini";
  char buffer[64];

  CHECK(ini_puts("app", "name", "HarmonyOS PC", filename));
  CHECK(ini_putl("app", "workers", 8, filename));
  CHECK(ini_putbool("app", "enabled", 1, filename));
  CHECK(ini_gets("app", "name", "", buffer, sizeof buffer, filename) == 12);
  CHECK(strcmp(buffer, "HarmonyOS PC") == 0);
  CHECK(ini_getl("app", "workers", -1, filename) == 8);
  CHECK(ini_getbool("app", "enabled", 0, filename) == 1);
  CHECK(ini_hassection("app", filename));
  CHECK(ini_haskey("app", "name", filename));
  CHECK(ini_getsection(0, buffer, sizeof buffer, filename) > 0);
  CHECK(strcmp(buffer, "app") == 0);
  CHECK(ini_getkey("app", 0, buffer, sizeof buffer, filename) > 0);
  CHECK(ini_browse(count_entry, NULL, filename));
  CHECK(browse_count == 3);
  CHECK(ini_puts("app", NULL, NULL, filename));
  CHECK(!ini_hassection("app", filename));
  CHECK(remove(filename) == 0);

  puts("libminini C consumer test passed");
  return 0;
}
