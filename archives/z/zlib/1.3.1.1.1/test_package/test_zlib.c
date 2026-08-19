#include <stdio.h>
#include <string.h>
#include <zlib.h>

int main(void) {
    const char input[] = "OpenHarmony zlib consumer test";
    unsigned char compressed[128];
    unsigned char restored[128];
    uLongf compressed_size = sizeof(compressed);
    uLongf restored_size = sizeof(restored);
    if (compress(compressed, &compressed_size, (const Bytef *)input, strlen(input) + 1) != Z_OK) return 1;
    if (uncompress(restored, &restored_size, compressed, compressed_size) != Z_OK) return 2;
    if (strcmp(input, (const char *)restored) != 0) return 3;
    puts("zlib consumer test passed");
    return 0;
}
