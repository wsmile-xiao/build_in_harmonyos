#include <gelf.h>
#include <stdio.h>

int main(void) {
    if (elf_version(EV_CURRENT) == EV_NONE) {
        fprintf(stderr, "elf_version failed\n");
        return 1;
    }
    if (elf_version(EV_NONE) != EV_NONE) {
        fprintf(stderr, "elf_version rejected invalid version incorrectly\n");
        return 1;
    }
    printf("libelf OK\n");
    return 0;
}
