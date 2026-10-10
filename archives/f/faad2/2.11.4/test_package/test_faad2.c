#include <neaacdec.h>

#include <stdio.h>

int main(void) {
    NeAACDecHandle decoder = NeAACDecOpen();
    if (decoder == NULL) {
        fputs("NeAACDecOpen failed\n", stderr);
        return 1;
    }

    if (NeAACDecGetCapabilities() == 0) {
        fputs("decoder reports no capabilities\n", stderr);
        NeAACDecClose(decoder);
        return 2;
    }

    NeAACDecClose(decoder);
    puts("FAAD2 installed decoder API passed");
    return 0;
}
