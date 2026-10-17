/* hello.c — consumer test source for fastbuild test_package.
 * Compiled *by fbuild itself* (Compiler/ObjectList in hello.bff) to prove
 * the packaged binary can drive a real compilation on HarmonyOS aarch64. */
#include <stdio.h>

int fb_hello_add(int a, int b)
{
    return a + b;
}

int main(void)
{
    printf("hello from fbuild consumer test: %d\n", fb_hello_add(40, 2));
    return 0;
}
