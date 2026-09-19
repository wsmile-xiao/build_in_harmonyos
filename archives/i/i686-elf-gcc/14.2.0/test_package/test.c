/* Minimal freestanding i686-elf program: proves the cross-compiler emits
   correct i386 code without any standard library or runtime support. */
int _start(void)
{
    volatile int x = 42;
    volatile int y = x * 3;
    return y - 1; /* 125 */
}
