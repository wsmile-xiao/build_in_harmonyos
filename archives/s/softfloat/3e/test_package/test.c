#include <stdint.h>
#include <softfloat.h>

int main(void)
{
    float32_t one = { UINT32_C(0x3F800000) };
    float32_t two = { UINT32_C(0x40000000) };
    return f32_add(one, two).v == UINT32_C(0x40400000) ? 0 : 1;
}
