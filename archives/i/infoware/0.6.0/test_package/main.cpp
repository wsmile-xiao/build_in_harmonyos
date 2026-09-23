#include <infoware/cpu.hpp>
#include <infoware/system.hpp>

// Consumer smoke test: call real infoware APIs from the installed package and
// assert the returned platform facts are sane on this host.
int main() {
    // At least one logical CPU must be reported.
    const auto quantities = iware::cpu::quantities();
    if (quantities.logical < 1)
        return 1;

    // Total physical memory must be reported as a non-zero byte count.
    const auto memory = iware::system::memory();
    if (memory.physical_total == 0)
        return 2;

    // The host is little-endian aarch64.
    if (iware::cpu::endianness() != iware::cpu::endianness_t::little)
        return 3;

    return 0;
}
