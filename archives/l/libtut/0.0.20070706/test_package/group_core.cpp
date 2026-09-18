// test_package/group_core.cpp - exercises <tut/tut.hpp> (canonical path)
//
// 4 tests: 3 must pass, test<4> deliberately fails via ensure() so the
// main.cpp counting callback can assert the framework reports result
// types exactly (ok vs fail, not a crash or a silent pass).

#include <tut/tut.hpp>
#include <string>

namespace tut
{

struct core_data
{
};

typedef test_group<core_data> core_tf;
typedef core_tf::object object;
namespace { core_tf core_group("core API"); }

template<> template<>
void object::test<1>()
{
    set_test_name("ensure / ensure_not");
    ensure("true condition", 1 + 1 == 2);
    ensure_not("false condition rejected", 1 + 1 == 3);
}

template<> template<>
void object::test<2>()
{
    set_test_name("ensure_equals numeric");
    ensure_equals("2*21 == 42", 2 * 21, 42);
}

template<> template<>
void object::test<3>()
{
    set_test_name("ensure_equals string + ensure_distance");
    std::string s = "tut";
    s += "-framework";
    ensure_equals("string concat", s, std::string("tut-framework"));
    // 2007 semantics: bounds are EXCLUSIVE (expected +/- distance),
    // so actual must fall strictly inside (31, 37) here
    ensure_distance("strictly within", 35, 34, 3);
}

template<> template<>
void object::test<4>()
{
    set_test_name("deliberate failure is reported as fail");
    ensure("this failure is intentional", 0 == 1);
}

} // namespace tut
