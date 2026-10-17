#include <cstddef>
#include <cstdint>
#include <cstdio>

#include "hwy/contrib/sort/vqsort.h"
#include "hwy/highway.h"
#include "hwy/targets.h"

namespace {

int Check(bool condition, const char* message) {
  if (!condition) {
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
  }
  return 0;
}

template <typename Less>
bool IsOrdered(const int32_t* keys, size_t n, Less less) {
  for (size_t i = 1; i < n; ++i) {
    if (!less(keys[i - 1], keys[i])) {
      return false;
    }
  }
  return true;
}

}  // namespace

int main() {
  int failures = 0;

  failures += Check(hwy::SupportedTargets() != 0,
                    "highway core dependency reports a non-zero target mask");

  int32_t keys[257];
  const size_t n = sizeof(keys) / sizeof(keys[0]);
  for (size_t i = 0; i < n; ++i) {
    keys[i] = static_cast<int32_t>((i * 1103515245u + 12345u) % 1000u) - 500;
  }

  hwy::VQSort(keys, n, hwy::SortAscending());
  failures +=
      Check(IsOrdered(keys, n, [](int32_t a, int32_t b) { return a <= b; }),
            "VQSort ascending orders all keys");
  failures += Check(keys[0] <= keys[n - 1], "ascending endpoints are consistent");

  for (size_t i = 0; i < n; ++i) {
    keys[i] = static_cast<int32_t>((i * 69069u + 1u) % 997u) - 400;
  }
  hwy::VQSort(keys, n, hwy::SortDescending());
  failures +=
      Check(IsOrdered(keys, n, [](int32_t a, int32_t b) { return a >= b; }),
            "VQSort descending orders all keys");

  if (failures != 0) {
    return 1;
  }

  std::printf("libhwy_contrib consumer checks passed\n");
  return 0;
}
