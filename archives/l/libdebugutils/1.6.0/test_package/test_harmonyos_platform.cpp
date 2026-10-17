#if !defined(__OHOS__)
#error "This test must be compiled by the HarmonyOS target toolchain"
#endif

// The HarmonyOS HNP compiler does not consistently predefine __MUSL__.
// __OHOS__ identifies the platform toolchain; the SDK supplies its musl sysroot.

#include <cstdio>

static_assert(sizeof(void*) == 8, "HarmonyOS PC test expects a 64-bit target");

int main()
{
    if (sizeof(void*) != 8)
        return 1;
    std::printf("CHECK-OK: HarmonyOS OHOS 64-bit target\n");
    return 0;
}
