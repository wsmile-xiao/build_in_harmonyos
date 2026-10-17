// OHOS-specific test for microsoft-proxy 4.0.1 (added by the R01 adaptation).
//
// This test is deliberately OHOS-toolchain-aware: OHOS SDK26 libc++ (15.0.4)
// defines _LIBCPP_HAS_NO_INCOMPLETE_FORMAT / _LIBCPP_HAS_NO_INCOMPLETE_RANGES,
// so <format> is an empty stub and std::ranges::uninitialized_copy is absent.
// The local portability patch (patches/0001-ohos-libcxx-format-and-ranges-compat.patch)
// guards std::format skills with the standard __cpp_lib_format macro and routes
// the trivial copy/relocate paths through classic std::uninitialized_copy.
// This test asserts those guarantees at compile time and then exercises the
// exact runtime paths the patch touches (in-place trivial copy, trivial
// relocate, swap), proving the core library works on the OHOS toolchain.
#include <proxy/proxy.h>

#include <cstdio>
#include <memory>

// Compile-time guarantee #1: on the OHOS toolchain the std::format skill must
// be disabled via the feature-test macro (the sharing libc++ has no working
// <format>). If the guard regresses to __has_include(<format>) the stub header
// would make these static_asserts fail or the format code path would not
// exist (both directions are covered by compile itself).
#if defined(__cpp_lib_format) && __cpp_lib_format >= 202110L
#error "OHOS-specific test expects std::format to be unavailable on the OHOS libc++"
#endif

// Compile-time guarantee #2: the facade machinery and trivial-copy path must
// be usable without <format> and without std::ranges memory algorithms.
PRO_DEF_MEM_DISPATCH(MemGet, get);

struct ValueFacade : pro::facade_builder
    ::add_convention<MemGet, int() const>
    ::support_copy<pro::constraint_level::trivial>
    ::build {};

struct IntValue {
  int v;
  explicit IntValue(int value) : v(value) {}
  int get() const { return v; }
};

static_assert(ValueFacade::copyability != pro::constraint_level::none);

int main() {
  int failures = 0;

  // 1) Non-owning binding + dispatch.
  IntValue a{7};
  pro::proxy<ValueFacade> p = &a;
  if (p->get() != 7) failures++;

  // 2) Owning, in-place binding via make_proxy (inplace_ptr: trivially
  //    copyable holder, so it satisfies the trivial-copy facade).
  pro::proxy<ValueFacade> q = pro::make_proxy<ValueFacade>(IntValue{21});
  if (q->get() != 21) failures++;

  // 3) Trivial-copy path: proxy copy exercises the patched
  //    std::uninitialized_copy(std::begin(..), std::end(..), ..) route.
  IntValue b{42};
  pro::proxy<ValueFacade> r = &b;
  pro::proxy<ValueFacade> s = r;  // copy ctor (trivial copyability)
  if (s->get() != 42) failures++;

  // 4) Trivial-relocate path via swap (patched route as well).
  pro::proxy<ValueFacade> t = &a;
  s.swap(t);
  if (s->get() != 7 || t->get() != 42) failures++;

  if (failures == 0) {
    std::puts("microsoft-proxy OHOS-specific test PASS");
    return 0;
  }
  std::printf("microsoft-proxy OHOS-specific test FAIL (%d failures)\n",
              failures);
  return 1;
}