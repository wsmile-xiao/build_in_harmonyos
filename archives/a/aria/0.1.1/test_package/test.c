#include <stdio.h>
#include <string.h>

#include "aria.h"

static int failures;

#define CHECK(condition, message) \
  do { \
    if (!(condition)) { \
      fprintf(stderr, "FAIL: %s\n", message); \
      failures++; \
    } \
  } while (0)

int main(void) {
  ar_State *state = ar_new_state(NULL, NULL);
  ar_Value *value;
  ar_Value *pair;

  CHECK(state != NULL, "ar_new_state returned NULL");
  if (!state) {
    return 1;
  }

  value = ar_do_string(state, "(+ 2 3)");
  CHECK(value != NULL, "ar_do_string returned NULL for arithmetic");
  CHECK(value && ar_type(value) == AR_TNUMBER, "arithmetic result is not a number");
  if (value && ar_type(value) == AR_TNUMBER) {
    CHECK(ar_to_number(state, value) == 5.0, "arithmetic result is not 5");
  }

  value = ar_do_string(state, "(string \"aria\" \"-\" \"ohos\")");
  CHECK(value != NULL, "ar_do_string returned NULL for string concatenation");
  if (value && ar_type(value) == AR_TSTRING) {
    CHECK(strcmp(ar_to_string(state, value), "aria-ohos") == 0,
          "string concatenation result is incorrect");
  }

  pair = ar_new_pair(state, ar_new_number(state, 1.0), ar_new_number(state, 2.0));
  CHECK(pair != NULL && ar_type(pair) == AR_TPAIR, "ar_new_pair did not create a pair");
  CHECK(pair && ar_type(ar_car(pair)) == AR_TNUMBER, "pair car is not a number");
  CHECK(pair && ar_type(ar_cdr(pair)) == AR_TNUMBER, "pair cdr is not a number");

  ar_close_state(state);
  if (failures) {
    fprintf(stderr, "%d aria consumer checks failed\n", failures);
    return 1;
  }
  puts("aria consumer checks passed");
  return 0;
}
