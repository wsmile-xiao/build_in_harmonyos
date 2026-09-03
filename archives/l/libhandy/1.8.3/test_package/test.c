#include <handy.h>
#include <stdio.h>

int main(void) {
    printf("libhandy %d.%d.%d\n",
           HDY_MAJOR_VERSION, HDY_MINOR_VERSION, HDY_MICRO_VERSION);
    hdy_init();
    return 0;
}
