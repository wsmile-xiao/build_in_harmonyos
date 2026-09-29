#include <stdio.h>

#include "extracted_disk.h"

int main(void) {
    unsigned int i;
    if (sizeof(disk_image) != 16384) {
        fprintf(stderr, "unexpected disk length: %zu\n", sizeof(disk_image));
        return 1;
    }
    for (i = 0; i < 8192; ++i) {
        if (disk_image[i] != (unsigned char)((i * 37 + i / 97) % 256) ||
            disk_image[i + 8192] != 'Z') {
            fprintf(stderr, "bad DMS extraction at byte %u\n", i);
            return 2;
        }
    }
    puts("OHOS consumer: stored and RLE tracks decoded; 16384 bytes verified");
    return 0;
}
