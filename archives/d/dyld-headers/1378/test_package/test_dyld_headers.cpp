#include <mach-o/fixup-chains.h>
#include <objc-shared-cache.h>

#include <cstdint>

int main()
{
    static_assert(DYLD_CHAINED_PTR_START_NONE == 0xFFFF);
    static_assert(DYLD_CHAINED_PTR_START_MULTI == 0x8000);
    static_assert(sizeof(dyld_chained_fixups_header) == 7 * sizeof(std::uint32_t));
    static_assert(objc_opt::VERSION == 16);
    static_assert(sizeof(objc_opt::objc_opt_t) % sizeof(void*) == 0);

    dyld_chained_fixups_header header{};
    header.fixups_version = 0;
    header.imports_count = 3;

    objc_opt::objc_opt_t objc_header{};
    objc_header.version = objc_opt::VERSION;

    if (header.fixups_version != 0 || header.imports_count != 3) {
        return 1;
    }
    if (objc_header.version != 16 || objc_header.selectorOpt() != nullptr) {
        return 2;
    }
    return 0;
}
