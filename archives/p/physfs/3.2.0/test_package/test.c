#include <stdio.h>
#include <physfs.h>

int main(void) {
    if (!PHYSFS_init(NULL)) {
        fprintf(stderr, "PHYSFS_init failed: %s\n", PHYSFS_getLastError());
        return 1;
    }

    PHYSFS_Version compiled, linked;
    PHYSFS_VERSION(&compiled);
    PHYSFS_getLinkedVersion(&linked);
    printf("physfs test: compiled=%d.%d.%d linked=%d.%d.%d\n",
           compiled.major, compiled.minor, compiled.patch,
           linked.major, linked.minor, linked.patch);

    if (linked.major != 3 || linked.minor != 2) {
        fprintf(stderr, "Unexpected physfs version\n");
        PHYSFS_deinit();
        return 1;
    }

    PHYSFS_deinit();
    printf("physfs test: OK\n");
    return 0;
}
