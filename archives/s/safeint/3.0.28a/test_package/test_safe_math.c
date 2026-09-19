#include <limits.h>
#include <stdint.h>
#include <stdio.h>

#include <safe_math.h>

#define SAFE_MATH_CHECK(expression) \
  do { \
    if (!(expression)) { \
      fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #expression); \
      return 1; \
    } \
  } while (0)

int main(void) {
  int32_t result = 0;
  SAFE_MATH_CHECK(check_cast_int32_int64(INT64_C(42)) == 0);
  SAFE_MATH_CHECK(check_cast_int32_int64(INT64_MAX) != 0);
  SAFE_MATH_CHECK(safe_cast_int32_int64(INT64_C(42)) == 42);
  SAFE_MATH_CHECK(check_add_int32_int32(100, 23, &result) && result == 123);
  SAFE_MATH_CHECK(!check_add_int32_int32(INT32_MAX, 1, &result));
  SAFE_MATH_CHECK(check_sub_int32_int32(100, 23, &result) && result == 77);
  SAFE_MATH_CHECK(check_mul_int32_int32(12, 11, &result) && result == 132);
  SAFE_MATH_CHECK(check_div_int32_int32(144, 12, &result) && result == 12);
  printf("PASS: safe_math C consumer (8/8 checks)\n");
  return 0;
}
