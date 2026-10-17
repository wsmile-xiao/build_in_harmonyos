#include <cassert>
#include <iostream>

#include <type_safe/boolean.hpp>
#include <type_safe/integer.hpp>
#include <type_safe/optional.hpp>

int main()
{
    type_safe::integer<int> count(41);
    count += 1;
    assert(static_cast<int>(count) == 42);

    type_safe::boolean enabled(true);
    assert(static_cast<bool>(enabled));

    type_safe::optional<int> value(42);
    assert(value.has_value());
    assert(value.value() == 42);

    std::cout << "type_safe consumer OK: " << static_cast<int>(count) << '\n';
    return 0;
}

