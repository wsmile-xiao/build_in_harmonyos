#include <cstring>
#include <iostream>

#include "database.hpp"
#include "generator.hpp"
#include "string_id.hpp"

namespace sid = foonathan::string_id;

namespace {
bool check(bool condition, const char *name, int &assertions)
{
    ++assertions;
    if (!condition)
        std::cerr << "FAILED: " << name << '\n';
    return condition;
}
} // namespace

int main()
{
    using namespace sid::literals;

    int assertions = 0;
    sid::default_database database;
    sid::string_id hello("Hello", database);
    sid::string_id world("World", database);

    if (!check(std::strcmp(hello.string(), "Hello") == 0,
               "database lookup returns the original string", assertions))
        return 1;
    if (!check(hello.hash_code() != 0, "hash code is populated", assertions))
        return 1;
    if (!check(hello == "Hello"_id, "compile-time literal compares equal", assertions))
        return 1;
    if (!check(&hello.database() == &database, "id retains its database", assertions))
        return 1;
    if (!check(hello != world, "different strings produce different ids", assertions))
        return 1;

    sid::string_id prefix("entity-", database);
    sid::counter_generator generator(prefix, 0, 2);
    sid::string_id first = generator();
    sid::string_id second = generator();
    generator.discard(1);
    sid::string_id fourth = generator();

    if (!check(std::strcmp(prefix.string(), "entity-") == 0,
               "prefix is stored", assertions))
        return 1;
    if (!check(std::strcmp(first.string(), "entity-00") == 0,
               "counter generator formats the first id", assertions))
        return 1;
    if (!check(std::strcmp(second.string(), "entity-01") == 0,
               "counter generator increments", assertions))
        return 1;
    if (!check(first != second, "generated ids are distinct", assertions))
        return 1;
    if (!check(std::strcmp(fourth.string(), "entity-03") == 0,
               "counter generator discard advances state", assertions))
        return 1;
    if (!check(&fourth.database() == &database,
               "generated id uses the prefix database", assertions))
        return 1;

    std::cout << "string_id consumer assertions: " << assertions << '\n';
    return assertions == 11 ? 0 : 1;
}
