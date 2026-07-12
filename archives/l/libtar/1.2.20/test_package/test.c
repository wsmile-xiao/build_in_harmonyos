#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <libtar.h>

int main(void) {
    TAR *t;
    const char *testfile = "test_input.txt";
    const char *tarfile = "test.tar";

    /* Create a test file */
    FILE *f = fopen(testfile, "w");
    if (!f) {
        fprintf(stderr, "Failed to create test file\n");
        return 1;
    }
    fprintf(f, "libtar test content\n");
    fclose(f);

    /* Create a tar archive containing the test file */
    if (tar_open(&t, tarfile, NULL, O_WRONLY | O_CREAT, 0644, 0) != 0) {
        fprintf(stderr, "tar_open (write) failed\n");
        return 1;
    }
    if (tar_append_file(t, (char *)testfile, (char *)testfile) != 0) {
        fprintf(stderr, "tar_append_file failed\n");
        tar_close(t);
        return 1;
    }
    if (tar_append_eof(t) != 0) {
        fprintf(stderr, "tar_append_eof failed\n");
        tar_close(t);
        return 1;
    }
    if (tar_close(t) != 0) {
        fprintf(stderr, "tar_close (write) failed\n");
        return 1;
    }

    /* Read the tar archive back and extract */
    if (tar_open(&t, tarfile, NULL, O_RDONLY, 0, 0) != 0) {
        fprintf(stderr, "tar_open (read) failed\n");
        return 1;
    }
    if (tar_extract_all(t, ".") != 0) {
        fprintf(stderr, "tar_extract_all failed\n");
        tar_close(t);
        return 1;
    }
    if (tar_close(t) != 0) {
        fprintf(stderr, "tar_close (read) failed\n");
        return 1;
    }

    /* Verify the extracted file content */
    f = fopen(testfile, "r");
    if (!f) {
        fprintf(stderr, "Failed to open extracted file\n");
        return 1;
    }
    char buf[64];
    if (fgets(buf, sizeof(buf), f) == NULL) {
        fprintf(stderr, "Failed to read extracted file\n");
        fclose(f);
        return 1;
    }
    fclose(f);

    if (strcmp(buf, "libtar test content\n") != 0) {
        fprintf(stderr, "Content mismatch: %s\n", buf);
        return 1;
    }

    printf("libtar test: OK\n");
    return 0;
}
