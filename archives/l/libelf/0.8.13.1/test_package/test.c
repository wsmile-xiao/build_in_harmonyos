#include <libelf.h>
#include <stdio.h>

int main() {
    long int ver = elf_version(EV_CURRENT);
    if (ver == EV_NONE) {
        fprintf(stderr, "elf_version failed\n");
        return 1;
    }
    printf("libelf initialized, version=%ld (EV_CURRENT=%d)\n", ver, EV_CURRENT);
    return 0;
}
