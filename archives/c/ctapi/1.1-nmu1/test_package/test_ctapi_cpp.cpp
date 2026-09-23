#include <ctapi.h>

#include <cstdint>
#include <type_traits>

using InitSignature = std::int8_t (*)(std::uint16_t, std::uint16_t);
using CloseSignature = std::int8_t (*)(std::uint16_t);

static_assert(std::is_same_v<decltype(&CT_init), InitSignature>);
static_assert(std::is_same_v<decltype(&CT_close), CloseSignature>);

int main()
{
    if (CT_init(9U, 1U) != OK) {
        return 1;
    }
    if (CT_close(9U) != OK) {
        return 2;
    }
    return REMOTE_HOST == 0x05 ? 0 : 3;
}
