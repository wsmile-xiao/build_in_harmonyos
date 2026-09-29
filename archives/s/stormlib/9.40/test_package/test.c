/* Consumer test for stormlib/9.40.
 *
 * Exercises a full MPQ archive round trip through the packaged library:
 *   create archive -> add a file from disk -> write data -> finish ->
 *   close -> reopen -> open the file -> read it back -> byte-compare.
 * Everything runs on the local filesystem in a temp work dir; no network,
 * no external assets.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "StormLib.h"

#define CHECK(cond, msg)                                                  \
    do {                                                                  \
        if (!(cond)) {                                                    \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);        \
            return 1;                                                     \
        }                                                                 \
    } while (0)

static const char *PAYLOAD = "StormLib MPQ round-trip payload for HarmonyOS\n";

int main(int argc, char **argv)
{
    const char *dir = (argc > 1) ? argv[1] : ".";
    char mpq_path[1024];
    char src_path[1024];
    HANDLE hMpq = NULL;
    HANDLE hFile = NULL;
    DWORD written = 0;
    DWORD read_bytes = 0;
    DWORD file_size = 0;
    char readback[512];

    snprintf(mpq_path, sizeof(mpq_path), "%s/consumer.mpq", dir);
    snprintf(src_path, sizeof(src_path), "%s/consumer-src.txt", dir);
    remove(mpq_path);

    /* 1) Source file on disk. */
    FILE *f = fopen(src_path, "wb");
    CHECK(f != NULL, "cannot create source file");
    fwrite(PAYLOAD, 1, strlen(PAYLOAD), f);
    fclose(f);

    /* 2) Create archive and add the file. */
    CHECK(SFileCreateArchive(mpq_path, MPQ_CREATE_ARCHIVE_V2, 4, &hMpq),
          "SFileCreateArchive failed");
    CHECK(SFileCreateFile(hMpq, "payload.txt", 0, (DWORD)strlen(PAYLOAD), 0,
                          MPQ_FILE_COMPRESS | MPQ_FILE_ENCRYPTED, &hFile),
          "SFileCreateFile failed");
    CHECK(SFileWriteFile(hFile, PAYLOAD, (DWORD)strlen(PAYLOAD),
                         MPQ_COMPRESSION_ZLIB),
          "SFileWriteFile failed");
    CHECK(SFileFinishFile(hFile), "SFileFinishFile failed");
    CHECK(SFileCloseArchive(hMpq), "SFileCloseArchive failed");
    hMpq = NULL;

    /* 3) Reopen and read back. */
    CHECK(SFileOpenArchive(mpq_path, 0, 0, &hMpq), "SFileOpenArchive failed");
    CHECK(SFileOpenFileEx(hMpq, "payload.txt", SFILE_OPEN_FROM_MPQ, &hFile),
          "SFileOpenFileEx failed");
    /* Read exactly the stored size: SFileReadFile returns FALSE with
     * ERROR_HANDLE_EOF (1002) when the buffer is larger than the file. */
    file_size = SFileGetFileSize(hFile, NULL);
    CHECK(file_size == (DWORD)strlen(PAYLOAD), "stored size mismatch");
    memset(readback, 0, sizeof(readback));
    CHECK(SFileReadFile(hFile, readback, file_size, &read_bytes, NULL),
          "SFileReadFile failed");
    CHECK(read_bytes == file_size, "read size mismatch");
    CHECK(memcmp(readback, PAYLOAD, read_bytes) == 0, "payload mismatch");
    SFileCloseFile(hFile);
    SFileCloseArchive(hMpq);

    /* 4) Version string sanity. */
    printf("StormLib version: %s\n", STORMLIB_VERSION_STRING);
    printf("STORMLIB-CONSUMER-OK\n");
    return 0;
}
