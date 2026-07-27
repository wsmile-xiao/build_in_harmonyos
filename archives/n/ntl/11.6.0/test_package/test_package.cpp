#include <NTL/ZZ.h>

int main() {
    const NTL::ZZ left = NTL::conv<NTL::ZZ>(123456789L);
    const NTL::ZZ right = NTL::conv<NTL::ZZ>(987654321L);
    const NTL::ZZ expected = NTL::conv<NTL::ZZ>(121932631112635269L);
    return left * right == expected ? 0 : 1;
}
