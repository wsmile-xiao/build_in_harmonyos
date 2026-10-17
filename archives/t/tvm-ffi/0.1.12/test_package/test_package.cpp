// Consumer test for tvm-ffi 0.1.12: exercises the real public C/C++ API.
// 6 explicit checks; prints "CHECK n/6 ..." per check and "RESULT 6/6" only
// when all pass. Returns 0 on 6/6, 1 otherwise, so ctest exit status is the
// pass/fail evidence (no empty-shell test).

#include <cstdint>
#include <cstdio>

#include <tvm/ffi/any.h>
#include <tvm/ffi/container/array.h>
#include <tvm/ffi/c_api.h>
#include <tvm/ffi/container/shape.h>
#include <tvm/ffi/string.h>

int main() {
  int passed = 0;

  // 1. Version macros match the recipe version 0.1.12.
  if (TVM_FFI_VERSION_MAJOR == 0 && TVM_FFI_VERSION_MINOR == 1 &&
      TVM_FFI_VERSION_PATCH == 12) {
    ++passed;
    std::printf("CHECK 1/6 version-macros 0.1.12 ok\n");
  } else {
    std::printf("CHECK 1/6 version-macros FAIL %d.%d.%d\n", TVM_FFI_VERSION_MAJOR,
                TVM_FFI_VERSION_MINOR, TVM_FFI_VERSION_PATCH);
  }

  // 2. C version API reports the same version.
  {
    TVMFFIVersion v{0, 0, 0};
    TVMFFIGetVersion(&v);
    if (v.major == 0 && v.minor == 1 && v.patch == 12) {
      ++passed;
      std::printf("CHECK 2/6 c-version-api %u.%u.%u ok\n", v.major, v.minor, v.patch);
    } else {
      std::printf("CHECK 2/6 c-version-api FAIL %u.%u.%u\n", v.major, v.minor, v.patch);
    }
  }

  // 3. AnyView int roundtrip through the C++ Any layer.
  {
    tvm::ffi::AnyView view = 42;
    int v = view.cast<int>();
    if (v == 42) {
      ++passed;
      std::printf("CHECK 3/6 any-int-roundtrip ok\n");
    } else {
      std::printf("CHECK 3/6 any-int-roundtrip FAIL got %d\n", v);
    }
  }

  // 4. String roundtrip (heap + comparison ops).
  {
    tvm::ffi::String s{"hello"};
    tvm::ffi::String t = s + " world";
    if (s.size() == 5 && t.compare("hello world") == 0) {
      ++passed;
      std::printf("CHECK 4/6 string-roundtrip ok\n");
    } else {
      std::printf("CHECK 4/6 string-roundtrip FAIL size=%zu\n", s.size());
    }
  }

  // 5. Array of int64: size and element sum.
  {
    tvm::ffi::Array<int64_t> arr{int64_t{1}, int64_t{2}, int64_t{3}};
    int64_t sum = 0;
    for (int64_t x : arr) {
      sum += x;
    }
    if (arr.size() == 3 && sum == 6) {
      ++passed;
      std::printf("CHECK 5/6 array-sum ok\n");
    } else {
      std::printf("CHECK 5/6 array-sum FAIL size=%zu sum=%lld\n",
                  arr.size(), static_cast<long long>(sum));
    }
  }

  // 6. Shape container holds expected dimensions.
  {
    tvm::ffi::Shape shape{int64_t{2}, int64_t{3}};
    if (shape.size() == 2 && shape[0] == 2 && shape[1] == 3) {
      ++passed;
      std::printf("CHECK 6/6 shape-dims ok\n");
    } else {
      std::printf("CHECK 6/6 shape-dims FAIL size=%zu\n", shape.size());
    }
  }

  std::printf("RESULT %d/6\n", passed);
  return passed == 6 ? 0 : 1;
}
