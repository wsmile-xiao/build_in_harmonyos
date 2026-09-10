// test_boost_type_erasure.cpp — boost1.84-type_erasure 1.84.0 L1 smoke test.
//
// Substantive verification of Boost.TypeErasure core capabilities
// (R34: calls the tested package's real APIs, no print-only stub):
//   1. any<> with copy_constructible + typeid_ + ostreamable: store
//      heterogeneous values (int / std::string / double), stream them,
//      any_cast them back.
//   2. Callable concept: any holding lambdas/functors invoked through the
//      erased call interface.
//   3. Member concept: erased type with a member function requirement.
//   4. Dynamic binding registry (libboost_type_erasure): register_binding
//      + dynamic_any_cast across separately compiled concept maps.
//
// Runtime: HarmonyOS PC (aarch64, clang 15, libc++), C++17.

#include <boost/type_erasure/any.hpp>
#include <boost/type_erasure/any_cast.hpp>
#include <boost/type_erasure/binding.hpp>
#include <boost/type_erasure/builtin.hpp>
#include <boost/type_erasure/callable.hpp>
#include <boost/type_erasure/member.hpp>
#include <boost/type_erasure/operators.hpp>
#include <boost/type_erasure/relaxed.hpp>
#include <boost/type_erasure/register_binding.hpp>
#include <boost/type_erasure/dynamic_binding.hpp>
#include <boost/type_erasure/dynamic_any_cast.hpp>
#include <boost/mpl/vector.hpp>

#include <cassert>
#include <sstream>
#include <string>

// ── 1. Heterogeneous printable values ──────────────────────────────
using printable = boost::mpl::vector<
    boost::type_erasure::copy_constructible<>,
    boost::type_erasure::typeid_<>,
    boost::type_erasure::ostreamable<>
>;

static std::string to_string_printable(boost::type_erasure::any<printable> x) {
    std::ostringstream oss;
    oss << x;
    return oss.str();
}

// ── 2. Erased callable: int(int) ───────────────────────────────────
using int_fn = boost::mpl::vector<
    boost::type_erasure::copy_constructible<>,
    boost::type_erasure::callable<int(int)>
>;

static int apply_int_fn(boost::type_erasure::any<int_fn> f, int v) {
    return f(v);
}

// ── 3. Erased member function requirement ──────────────────────────
BOOST_TYPE_ERASURE_MEMBER((has_bump), bump, 0)
using bumper = boost::mpl::vector<
    boost::type_erasure::copy_constructible<>,
    boost::type_erasure::typeid_ <>,
    has_bump<void()>
>;

struct counter {
    counter() : n(0) {}
    void bump() { ++n; }
    int n;
};

static int bump_twice(boost::type_erasure::any<bumper> x) {
    x.bump();
    x.bump();
    return boost::type_erasure::any_cast<counter>(x).n;
}

// ── 4. Dynamic binding across concept maps ─────────────────────────
// Uses the compiled libboost_type_erasure registry: register the
// std::string model for the source concept, then cross-cast with
// dynamic_any_cast (same pattern as upstream test_dynamic_any_cast.cpp).
// Note: relaxed is a plain struct (vector0), not a template, so it is
// named without <> (relaxed<> does not compile).
using concept_a = boost::mpl::vector<
    boost::type_erasure::copy_constructible<>,
    boost::type_erasure::typeid_<>,
    boost::type_erasure::ostreamable<>
>;
using concept_b = boost::mpl::vector<
    boost::type_erasure::copy_constructible<>,
    boost::type_erasure::typeid_<>,
    boost::type_erasure::relaxed
>;

int main() {
    // 1. heterogeneous any: stream + any_cast round-trip
    assert(to_string_printable(42) == "42");
    assert(to_string_printable(std::string("hi")) == "hi");
    boost::type_erasure::any<printable> v(2.5);
    assert(boost::type_erasure::any_cast<double>(v) == 2.5);
    std::ostringstream oss;
    oss << v;
    assert(oss.str() == "2.5");

    // 2. erased callable holds different functor types
    auto doubler = [](int x) { return x * 2; };
    struct adder {
        int k;
        int operator()(int x) const { return x + k; }
    };
    assert(apply_int_fn(doubler, 21) == 42);
    assert(apply_int_fn(adder{100}, 1) == 101);

    // 3. erased member function dispatches to the concrete type
    assert(bump_twice(counter()) == 2);

    // 4. dynamic binding: same object viewed through another concept map
    // (registry lives in libboost_type_erasure, so this also proves the
    // compiled library links and works).
    boost::type_erasure::any<concept_a> a(std::string("dyn"));
    boost::type_erasure::register_binding<concept_a, std::string>();
    boost::type_erasure::register_binding<concept_b, std::string>();
    boost::type_erasure::any<concept_b> b =
        boost::type_erasure::dynamic_any_cast<
            boost::type_erasure::any<concept_b> >(a);
    assert(boost::type_erasure::any_cast<std::string>(b) == "dyn");

    return 0;
}
