// test_package — matchit 1.0.0 consumer smoke test.
// Exercises real matchit.cpp public API on HarmonyOS arm64: literal, wildcard,
// some/as (pointer downcast), ds (destructuring) and ooo (rest). The idioms
// below mirror the upstream test suite (test/matchit/*.cpp) which is compiled
// with -Werror on clang, so they are known-good for the OHOS toolchain.
#include <matchit.h>

#include <cassert>
#include <memory>

using namespace matchit;

static int classify(int x)
{
    return match(x)(
        pattern | 0 = expr(0),
        pattern | 1 = expr(1),
        pattern | _ = expr(-1));
}

int main()
{
    // Literal + wildcard
    assert(classify(0) == 0);
    assert(classify(1) == 1);
    assert(classify(42) == -1);

    // some / as downcast on polymorphic pointer (upstream TEST(App, someAs))
    struct Base
    {
        virtual ~Base() = default;
        virtual int32_t id() const { return 0; }
    };
    struct Derived : Base
    {
        int32_t id() const override { return 7; }
    };
    auto const x = std::unique_ptr<Base>{new Derived};
    assert(matched(x, some(as<Derived>(_))));

    // ds destructuring + ooo rest on a tuple (upstream TEST(Ds, ...) family)
    auto const t = std::make_tuple(1, 2, 3);
    assert(matched(t, ds(1, ooo, 3)));
    assert(!matched(t, ds(1, ooo, 4)));

    return 0;
}
