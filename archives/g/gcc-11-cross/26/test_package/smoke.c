/* smoke.c - libc-free C17 smoke source for the gcc-11-cross arm-none-eabi
 * bare-metal toolchain (--enable-languages=c --with-newlib --without-headers).
 *
 * No standard headers are available, so fixed-width integer types are spelled
 * with the plain C builtin. The volatile 32-bit unsigned division below cannot
 * be folded away by the optimizer and, on a target without a hardware divide
 * unit, forces the linker to pull a libgcc helper (__aeabi_uidiv / __udivsi3)
 * out of the packaged libgcc.a.
 *
 * _start is the freestanding entry point used by the test link step
 * (-nostdlib -nostartfiles -Wl,-e,_start).
 */

typedef unsigned int uint32_t;

volatile uint32_t smoke_dividend = 1000000u;
volatile uint32_t smoke_divisor = 7u;
volatile uint32_t smoke_result;

void _start(void)
{
    smoke_result = smoke_dividend / smoke_divisor;
    for (;;) {
        /* bare-metal entry point never returns */
    }
}
