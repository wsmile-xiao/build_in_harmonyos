#include <cstdio>

#include <core_params.h>
#include <jane_common.h>

// core_params.h: the upstream I/O cutoff constant contract
static_assert(THREAD_IO_CUTOFF == 65536, "THREAD_IO_CUTOFF changed upstream");

// jane_common.h: the compiler-attribute shims must be installed for GCC/Clang
#if defined(__GNUC__) && !defined(__unused)
#error "jane_common.h did not install the __unused attribute shim"
#endif

int main()
{
    if (THREAD_IO_CUTOFF != 65536) {
        std::puts("FAIL: THREAD_IO_CUTOFF mismatch at runtime");
        return 1;
    }
    std::puts("jane-street-headers consumer ok");
    return 0;
}
