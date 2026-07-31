#include <stdio.h>
#include <magic.h>

int main(void) {
    magic_t magic = magic_open(MAGIC_NONE);
    if (magic == NULL) {
        fprintf(stderr, "magic_open failed\n");
        return 1;
    }
    magic_close(magic);
    printf("libmagic 5.48: OK\n");
    return 0;
}
