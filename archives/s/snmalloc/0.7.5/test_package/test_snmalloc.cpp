// test_package for snmalloc 0.7.5: real API usage (R34).
// Exercises the library through its public C++ API: allocation,
// deallocation, and the libc-compatible entry points.
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <snmalloc/snmalloc.h>

int main()
{
  // 1. libc-compatible allocation / deallocation via snmalloc::libc.
  constexpr size_t kSize = 1024;
  void* p = snmalloc::libc::malloc(kSize);
  assert(p != nullptr);
  std::memset(p, 0xAB, kSize);
  // Verify the returned pointer is owned by snmalloc and usable.
  assert(snmalloc::is_owned(p));
  snmalloc::libc::free(p);

  // 2. Sized deallocation path.
  void* q = snmalloc::libc::malloc(256);
  assert(q != nullptr);
  std::memset(q, 0, 256);
  snmalloc::libc::free(q);

  // 3. malloc_usable_size sanity.
  void* s = snmalloc::libc::malloc(128);
  assert(s != nullptr);
  assert(snmalloc::libc::malloc_usable_size(s) >= 128);
  snmalloc::libc::free(s);

  std::printf("test snmalloc 0.7.5: OK\n");
  return 0;
}
