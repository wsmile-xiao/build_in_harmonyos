/* test_package consumer test for symfpu (HarmonyOS PC).
 *
 * Uses only the installed public headers and the packaged static library:
 *   - symfpu/baseTypes/simpleExecutable.h   (concrete bit-vector back-end)
 *   - symfpu/applications/implementations.h (single-precision implementation)
 * and calls the public API (unpack/add/pack on IEEE-754 bit-vectors),
 * comparing against native float arithmetic.
 */
#include <stdint.h>
#include <stdio.h>
#include <fenv.h>

#include <symfpu/baseTypes/simpleExecutable.h>
#include <symfpu/applications/implementations.h>

typedef symfpu::simpleExecutable::traits traits;
static traits::fpt singlePrecisionFormatObject(8, 24);
typedef sympfuImplementation<uint32_t, traits> singlePrecisionExecutableSymfpu;

static uint32_t floatToBits(float f) {
  uint32_t b;
  __builtin_memcpy(&b, &f, sizeof(b));
  return b;
}

static float bitsToFloat(uint32_t b) {
  float f;
  __builtin_memcpy(&f, &b, sizeof(f));
  return f;
}

static int checkOp(const char *name, int ok) {
  printf("%-12s : %s\n", name, ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}

int main(void) {
  int failures = 0;

  singlePrecisionExecutableSymfpu::setFormat(singlePrecisionFormatObject);
  singlePrecisionExecutableSymfpu::setRoundingMode(FE_TONEAREST);

  /* 1.0f + 2.0f == 3.0f via SymFPU bit-vector arithmetic */
  uint32_t sum = singlePrecisionExecutableSymfpu::add(
      floatToBits(1.0f), floatToBits(2.0f));
  failures += checkOp("add 1+2", bitsToFloat(sum) == 3.0f);

  /* 2.0f * 3.0f == 6.0f */
  uint32_t prod = singlePrecisionExecutableSymfpu::multiply(
      floatToBits(2.0f), floatToBits(3.0f));
  failures += checkOp("mul 2*3", bitsToFloat(prod) == 6.0f);

  /* unpack/pack round-trip preserves bits */
  uint32_t rt = singlePrecisionExecutableSymfpu::unpackPack(0x40a00000u); /* 5.0f */
  failures += checkOp("unpackPack", rt == 0x40a00000u);

  /* isNaN detects NaN bit pattern */
  failures += checkOp("isNaN", singlePrecisionExecutableSymfpu::isNaN(0x7fc00000u));

  singlePrecisionExecutableSymfpu::destroyFormat();

  if (failures == 0) {
    printf("symfpu consumer test: all checks passed\n");
  } else {
    printf("symfpu consumer test: %d check(s) FAILED\n", failures);
  }
  return failures == 0 ? 0 : 1;
}