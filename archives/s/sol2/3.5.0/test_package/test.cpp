#include <sol/optional.hpp>
#include <sol/version.hpp>

int main() {
    static_assert(SOL_VERSION_MAJOR == 3, "unexpected sol2 major version");
    static_assert(SOL_VERSION_MINOR == 5, "unexpected sol2 minor version");
    static_assert(SOL_VERSION_PATCH == 0, "unexpected sol2 patch version");
    sol::optional<int> value = 42;
    sol::optional<int> empty;
    return value && *value == 42 && !empty ? 0 : 1;
}
