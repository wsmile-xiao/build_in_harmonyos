#include <stdio.h>
#include <string.h>

#include <lizard_compress.h>
#include <lizard_decompress.h>

int main(void) {
    const char *source = "HarmonyOS lizard compression round-trip test.";
    char compressed[256];
    char restored[256];
    int source_size = (int)strlen(source);

    if (Lizard_versionNumber() != 20100) {
        printf("FAIL: unexpected Lizard version %d\n", Lizard_versionNumber());
        return 1;
    }

    int compressed_size = Lizard_compress(
        source, compressed, source_size, sizeof(compressed), 19
    );
    if (compressed_size <= 0) {
        printf("FAIL: Lizard_compress returned %d\n", compressed_size);
        return 1;
    }

    int restored_size = Lizard_decompress_safe(
        compressed, restored, compressed_size, sizeof(restored)
    );
    if (restored_size != source_size) {
        printf("FAIL: decompressed size %d != %d\n", restored_size, source_size);
        return 1;
    }

    restored[restored_size] = '\0';
    if (strcmp(source, restored) != 0) {
        printf("FAIL: round-trip payload mismatch\n");
        return 1;
    }

    printf("PASS: lizard version=%d compressed=%d\n", Lizard_versionNumber(), compressed_size);
    return 0;
}
