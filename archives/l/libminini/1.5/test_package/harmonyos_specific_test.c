#include <stdio.h>
#include <string.h>

#include "minIni.h"

#if !defined(__OHOS__)
#error "This test must be compiled by the OHOS toolchain"
#endif
#if !defined(__aarch64__)
#error "HarmonyOS PC package must target AArch64"
#endif

#define CHECK(expr) do { \
  if (!(expr)) { \
    fprintf(stderr, "OHOS CHECK failed at %s:%d: %s\n", \
            __FILE__, __LINE__, #expr); \
    return 1; \
  } \
} while (0)

int main(void)
{
  const char *filename = "鸿蒙配置.ini";
  const char *section = "鸿蒙电脑";
  const char *key = "问候";
  const char *value = "你好，HarmonyOS PC";
  char buffer[128];
  unsigned char raw[512];
  size_t length;
  FILE *stream;

  CHECK(ini_puts(section, key, value, filename));
  CHECK(ini_gets(section, key, "", buffer, sizeof buffer, filename) > 0);
  CHECK(strcmp(buffer, value) == 0);
  CHECK(ini_hassection(section, filename));
  CHECK(ini_haskey(section, key, filename));

  stream = fopen(filename, "rb");
  CHECK(stream != NULL);
  length = fread(raw, 1, sizeof raw, stream);
  CHECK(ferror(stream) == 0);
  CHECK(fclose(stream) == 0);
  CHECK(length > 0);
  CHECK(memchr(raw, '\n', length) != NULL);
  CHECK(memchr(raw, '\r', length) == NULL);

  CHECK(ini_puts(section, NULL, NULL, filename));
  CHECK(remove(filename) == 0);
  puts("HarmonyOS-specific UTF-8 and LF semantics test passed");
  return 0;
}
