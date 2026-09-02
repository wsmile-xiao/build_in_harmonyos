#include <cstdlib>

#include <forkunion.h>
#include <forkunion.hpp>

int main() {
    static_assert(FORKUNION_VERSION_MAJOR == 3, "unexpected ForkUnion major version");
    static_assert(FORKUNION_VERSION_MINOR == 0, "unexpected ForkUnion minor version");
    static_assert(FORKUNION_VERSION_PATCH == 2, "unexpected ForkUnion patch version");

    if (fu_version_major() != 3 || fu_version_minor() != 0 || fu_version_patch() != 2)
        return EXIT_FAILURE;
    if (fu_comptime_capabilities() == 0 && fu_runtime_capabilities() != 0)
        return EXIT_FAILURE;

    return EXIT_SUCCESS;
}
