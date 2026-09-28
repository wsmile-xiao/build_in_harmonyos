#include <cstddef>

using byte = unsigned char;
using vec_t = float;
using vec3_t = vec_t[3];

#include <qwprot/protocol.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#ifndef __aarch64__
#error "This test validates the HarmonyOS aarch64 ABI"
#endif

namespace {

int failures = 0;

void check(bool condition)
{
    if (!condition) {
        ++failures;
    }
}

} // namespace

int main()
{
    check(sizeof(void *) == 8);
    check(sizeof(long) == 8);
    check(sizeof(byte) == 1);
    check(sizeof(short) == 2);
    check(sizeof(int) == 4);
    check(sizeof(vec_t) == 4);
    check(sizeof(usercmd_t) == 24);
    check(offsetof(usercmd_t, angles) == 4);
    check(offsetof(usercmd_t, buttons) == 22);
    check(sizeof(entity_state_t) == 56);
    check(offsetof(entity_state_t, trans) == 52);
    check(PROTOCOL_VERSION_FTE == 0x58455446);

    return failures;
}
