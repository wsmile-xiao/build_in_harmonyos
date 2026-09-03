#include "v7.h"

#include <math.h>
#include <stdio.h>

int main(void) {
  struct v7 *engine = v7_create();
  v7_val_t result;

  if (engine == NULL) {
    fprintf(stderr, "v7_create returned NULL\n");
    return 1;
  }

  if (v7_exec(engine, "1 + 2 * 3", &result) != V7_OK ||
      !v7_is_number(result) ||
      fabs(v7_get_double(engine, result) - 7.0) > 1e-9) {
    fprintf(stderr, "numeric JavaScript evaluation failed\n");
    v7_destroy(engine);
    return 1;
  }

  if (v7_exec(engine, "var value = 6; value * value", &result) != V7_OK ||
      !v7_is_number(result) ||
      fabs(v7_get_double(engine, result) - 36.0) > 1e-9) {
    fprintf(stderr, "stateful JavaScript evaluation failed\n");
    v7_destroy(engine);
    return 1;
  }

  v7_destroy(engine);
  puts("v7 consumer test: PASS");
  return 0;
}
