#include <refl.hpp>
#include <cassert>
#include <string>

// Real consumer test: use refl-cpp reflection API (R34: no empty shell).
struct Person {
    std::string name;
    int age;
    double score;
};

REFL_AUTO(
    type(Person),
    field(name),
    field(age),
    field(score)
)

static void test_reflect_fields()
{
    Person p{"alice", 30, 9.5};

    // Reflection type traits
    static_assert(refl::trait::is_reflectable<Person>::value,
                  "Person must be reflectable");

    // Compile-time member count via refl::util::for_each over type_list
    int field_count = 0;
    refl::util::for_each(refl::reflect<Person>().members,
                         [&](auto /*member*/) { ++field_count; });
    assert(field_count == 3);

    // Runtime debug string includes member names/values (upstream API)
    std::string dbg = refl::runtime::debug_str(p);
    assert(dbg.find("name = ") != std::string::npos);
    assert(dbg.find("age = ") != std::string::npos);
    assert(dbg.find("score = ") != std::string::npos);

    // Runtime invoke by member name: set age field
    assert(refl::runtime::invoke<int>(p, "age", 42) == 42);
}

int main()
{
    test_reflect_fields();
    return 0;
}