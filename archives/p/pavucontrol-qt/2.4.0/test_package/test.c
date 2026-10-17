#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    /* R34: test must actually depend on the tested package.
     * pavucontrol-qt is a GUI application, so we verify:
     * 1. The binary exists in the package bin directory
     * 2. It is a valid ELF executable (file header check)
     */
    if (argc < 2) {
        fprintf(stderr, "FAIL: usage: test_pavucontrol_qt <binary_path>\n");
        return 1;
    }

    const char *path = argv[1];
    if (access(path, F_OK) != 0) {
        fprintf(stderr, "FAIL: pavucontrol-qt binary not found at %s\n", path);
        return 1;
    }

    /* Check ELF magic (valid executable) */
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", path);
        return 1;
    }
    unsigned char magic[4];
    if (fread(magic, 1, 4, f) != 4) {
        fclose(f);
        fprintf(stderr, "FAIL: cannot read ELF header\n");
        return 1;
    }
    fclose(f);

    if (magic[0] != 0x7f || magic[1] != 'E' || magic[2] != 'L' || magic[3] != 'F') {
        fprintf(stderr, "FAIL: not a valid ELF binary\n");
        return 1;
    }

    printf("test pavucontrol-qt: OK (binary found and is valid ELF)\n");
    return 0;
}
