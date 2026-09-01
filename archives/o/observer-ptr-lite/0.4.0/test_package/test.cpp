// Consumer test for observer-ptr-lite 0.4.0 — exercises real observer_ptr APIs.
#include <nonstd/observer_ptr.hpp>
#include <cstdio>

using nonstd::observer_ptr;
using nonstd::make_observer;

static int g_checks = 0, g_failed = 0;
#define CHECK(cond) do { ++g_checks; if (!(cond)) { ++g_failed; std::printf("FAIL: %s\n", #cond); } } while(0)

int main() {
    int a = 7, b = 9;

    // make_observer + get
    observer_ptr<int> p1 = make_observer(&a);
    CHECK(p1.get() == &a);
    CHECK(*p1 == 7);

    // observer semantics: non-owning, does not affect lifetime
    observer_ptr<int> p2(&b);
    CHECK(p2.get() == &b);
    CHECK(*p2 == 9);

    // reset makes it null
    observer_ptr<int> p3 = make_observer(&a);
    CHECK(static_cast<bool>(p3));
    p3.reset();
    CHECK(!static_cast<bool>(p3));
    CHECK(p3.get() == nullptr);

    // comparison
    observer_ptr<int> pa = make_observer(&a);
    observer_ptr<int> pa2 = make_observer(&a);
    CHECK(pa == pa2);
    CHECK(pa != p2);

    std::printf("observer-ptr-lite test_package: %d checks, %d failed\n", g_checks, g_failed);
    return g_failed == 0 ? 0 : 1;
}
