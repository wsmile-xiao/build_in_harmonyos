#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <minizip/zip.h>
#include <minizip/unzip.h>

int main(void) {
    /* Test: create a zip file, then list its contents */
    const char *test_data = "Hello from minizip test!";
    const char *zip_name = "test_minizip.zip";
    const char *entry_name = "hello.txt";

    /* Create zip */
    zipFile zf = zipOpen(zip_name, APPEND_STATUS_CREATE);
    if (zf == NULL) {
        fprintf(stderr, "Failed to create zip file\n");
        return 1;
    }

    int err = zipOpenNewFileInZip(zf, entry_name, NULL, NULL, 0,
                                  NULL, 0, NULL,
                                  Z_DEFLATED, Z_DEFAULT_COMPRESSION);
    if (err != ZIP_OK) {
        fprintf(stderr, "Failed to add file to zip\n");
        zipClose(zf, NULL);
        return 1;
    }

    err = zipWriteInFileInZip(zf, test_data, (unsigned int)strlen(test_data));
    if (err != ZIP_OK) {
        fprintf(stderr, "Failed to write data to zip\n");
        zipCloseFileInZip(zf);
        zipClose(zf, NULL);
        return 1;
    }

    zipCloseFileInZip(zf);
    zipClose(zf, "minizip test comment");

    /* Read zip */
    unzFile uf = unzOpen(zip_name);
    if (uf == NULL) {
        fprintf(stderr, "Failed to open zip file\n");
        return 1;
    }

    err = unzGoToFirstFile(uf);
    if (err != UNZ_OK) {
        fprintf(stderr, "Failed to go to first file\n");
        unzClose(uf);
        return 1;
    }

    char filename_inzip[256];
    unz_file_info file_info;
    err = unzGetCurrentFileInfo(uf, &file_info, filename_inzip, sizeof(filename_inzip),
                                NULL, 0, NULL, 0);
    if (err != UNZ_OK) {
        fprintf(stderr, "Failed to get file info\n");
        unzClose(uf);
        return 1;
    }

    if (strcmp(filename_inzip, entry_name) != 0) {
        fprintf(stderr, "Unexpected filename: %s (expected %s)\n", filename_inzip, entry_name);
        unzClose(uf);
        return 1;
    }

    /* Read and verify content */
    err = unzOpenCurrentFile(uf);
    if (err != UNZ_OK) {
        fprintf(stderr, "Failed to open current file\n");
        unzClose(uf);
        return 1;
    }

    char buf[256];
    int bytes_read = unzReadCurrentFile(uf, buf, sizeof(buf) - 1);
    if (bytes_read < 0) {
        fprintf(stderr, "Failed to read file content\n");
        unzCloseCurrentFile(uf);
        unzClose(uf);
        return 1;
    }
    buf[bytes_read] = '\0';

    if (strcmp(buf, test_data) != 0) {
        fprintf(stderr, "Content mismatch: %s (expected %s)\n", buf, test_data);
        unzCloseCurrentFile(uf);
        unzClose(uf);
        return 1;
    }

    unzCloseCurrentFile(uf);
    unzClose(uf);
    remove(zip_name);  // cleanup test artifact

    printf("test minizip 1.3.1: OK (zip create + read round-trip)\n");
    return 0;
}
