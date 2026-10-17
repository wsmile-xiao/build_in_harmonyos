/*
 * test_package consumer test — flag 0.1.2
 *
 * Consumer-perspective validation (R34/L1): links against the installed
 * public header (flag.h) and static lib (libflag.a), and exercises the
 * public Go-style flag API — flagset_new/flagset_int/flagset_string/
 * flagset_bool/flagset_parse/flagset_free — with observable results.
 */
#include <stdio.h>
#include <string.h>
#include "flag.h"

static int failures = 0;

#define CHECK(cond, msg) \
  do { \
    if (!(cond)) { \
      printf("FAIL: %s\n", msg); \
      failures++; \
    } else { \
      printf("OK:   %s\n", msg); \
    } \
  } while (0)

int main(void) {
  /* flagset_parse(): int + string + bool flags */
  {
    int n = 0;
    bool v = false;
    const char *addr = NULL;
    const char *args[] = {"app", "--num", "42", "--enable", "--address", "127.0.0.1"};

    flagset_t *set = flagset_new();
    flagset_int(set, &n, "num", "Number");
    flagset_bool(set, &v, "enable", "Enable");
    flagset_string(set, &addr, "address", "Address");
    flag_error err = flagset_parse(set, 6, args);

    CHECK(err == FLAG_OK, "flagset_parse returns FLAG_OK");
    CHECK(n == 42, "int flag value parsed (n == 42)");
    CHECK(v == true, "bool flag value parsed (v == true)");
    CHECK(addr != NULL && strcmp(addr, "127.0.0.1") == 0, "string flag value parsed (addr == 127.0.0.1)");
    CHECK(set->argc == 1 && strcmp(set->argv[0], "app") == 0, "positional args preserved (argc/argv)");
    flagset_free(set);
  }

  /* unknown flag → FLAG_ERROR_UNDEFINED_FLAG */
  {
    const char *args[] = {"--nope"};
    flagset_t *set = flagset_new();
    flag_error err = flagset_parse(set, 1, args);
    CHECK(err == FLAG_ERROR_UNDEFINED_FLAG, "undefined flag returns FLAG_ERROR_UNDEFINED_FLAG");
    flagset_free(set);
  }

  /* singleton flag_parse() */
  {
    int n = 100;
    const char *args[] = {"prog", "--requests", "500"};
    flag_int(&n, "requests", "Requests");
    flag_parse(3, args, "1.0.0");
    CHECK(n == 500, "singleton flag_parse() parses value (n == 500)");
  }

  if (failures == 0) {
    printf("test_flag: ALL PASS (%d checks)\n", 7);
    return 0;
  }
  printf("test_flag: %d CHECK(S) FAILED\n", failures);
  return 1;
}