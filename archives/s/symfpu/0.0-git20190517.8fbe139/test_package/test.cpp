#include <cstdint>
#include <cstdio>

#include <symfpu/baseTypes/simpleExecutable.h>
#include <symfpu/core/add.h>
#include <symfpu/core/multiply.h>
#include <symfpu/core/packing.h>

typedef symfpu::simpleExecutable::traits Traits;

static int check(const char *name, uint32_t actual, uint32_t expected) {
    const bool passed = actual == expected;
    std::printf("%-16s %s (got 0x%08x, expected 0x%08x)\n",
                name, passed ? "PASS" : "FAIL",
                static_cast<unsigned int>(actual),
                static_cast<unsigned int>(expected));
    return passed ? 0 : 1;
}

int main() {
    const Traits::fpt format(8, 24);
    const Traits::rm rounding = Traits::RNE();

    const Traits::ubv oneBits(32, 0x3f800000u);
    const Traits::ubv twoBits(32, 0x40000000u);
    const Traits::ubv threeBits(32, 0x40400000u);
    const Traits::ubv fiveBits(32, 0x40a00000u);
    const Traits::ubv sixBits(32, 0x40c00000u);

    const symfpu::unpackedFloat<Traits> one =
        symfpu::unpack<Traits>(format, oneBits);
    const symfpu::unpackedFloat<Traits> two =
        symfpu::unpack<Traits>(format, twoBits);
    const symfpu::unpackedFloat<Traits> three =
        symfpu::unpack<Traits>(format, threeBits);

    int failures = 0;
    failures += check("unpack-pack 5.0",
                      symfpu::pack<Traits>(format, symfpu::unpack<Traits>(format, fiveBits)).contents(),
                      0x40a00000u);

    const symfpu::unpackedFloat<Traits> sum =
        symfpu::add<Traits>(format, rounding, one, two, Traits::prop(true));
    failures += check("add 1.0+2.0",
                      symfpu::pack<Traits>(format, sum).contents(),
                      0x40400000u);

    const symfpu::unpackedFloat<Traits> product =
        symfpu::multiply<Traits>(format, rounding, two, three);
    failures += check("multiply 2.0*3.0",
                      symfpu::pack<Traits>(format, product).contents(),
                      0x40c00000u);

    std::printf("SymFPU consumer assertions: %d/3 passed\n", 3 - failures);
    return failures == 0 ? 0 : 1;
}