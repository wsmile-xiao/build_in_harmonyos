/* Consumer program for the opari HarmonyOS-specific test.
 *
 * A trivial C OpenMP reduction. It is instrumented by the opari tool, then
 * compiled + linked against libpomp (opari runtime) and libomp (OHOS OpenMP
 * runtime). pomp_init() enables POMP region tracing so the instrumented events
 * actually fire on aarch64 OHOS — test_package/conanfile.py asserts those
 * events, which is what makes this case HarmonyOS-specific (and falsifiable)
 * rather than a generic OpenMP smoke test.
 */
#include <omp.h>
#include <stdio.h>
#include "pomp_lib.h"

int main() {
  pomp_init();
  int sum = 0;
#pragma omp parallel for reduction(+:sum)
  for (int i = 0; i < 100; i++) sum += i;
  printf("sum=%d\n", sum);
  return (sum == 4950) ? 0 : 1;
}
