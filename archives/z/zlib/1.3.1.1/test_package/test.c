#include <zlib.h>
#include <stdio.h>
int main(void) {
    printf("zlib %s ok\n", zlibVersion());
    return 0;
}
