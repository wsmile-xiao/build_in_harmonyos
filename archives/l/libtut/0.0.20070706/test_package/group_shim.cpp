// test_package/group_shim.cpp - exercises the root-level backward-compat
// shim <tut.h> (Debian libtut-dev installs it next to include/tut/).
//
// Also proves a second test group in a separate compilation unit
// self-registers with the tut::runner singleton defined in main.cpp.

#include <tut.h>
#include <string>
#include <vector>

namespace tut
{

struct shim_data
{
};

typedef test_group<shim_data> shim_tf;
typedef shim_tf::object object;
namespace { shim_tf shim_group("root shim include"); }

template<> template<>
void object::test<1>()
{
    set_test_name("STL works under shim include");
    std::vector<int> v;
    v.push_back(40);
    v.push_back(2);
    ensure_equals("vector size", v.size(), static_cast<size_t>(2));
    ensure_equals("vector sum", v[0] + v[1], 42);
}

template<> template<>
void object::test<2>()
{
    set_test_name("tut::fail throws tut::failure with message");
    bool caught = false;
    try
    {
        tut::fail("expected-failure-marker");
    }
    catch (const tut::failure& ex)
    {
        caught = std::string(ex.what()).find("expected-failure-marker") !=
                 std::string::npos;
    }
    ensure("failure message preserved", caught);
}

} // namespace tut
