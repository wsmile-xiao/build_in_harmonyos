/* Consumer test for the lib1541img package (C11).
 * Creates a D64 image in memory, adds a PRG file, writes it to disk, then
 * reads it back and verifies the file name and content. */
#include <1541img/cbmdosfile.h>
#include <1541img/cbmdosfs.h>
#include <1541img/cbmdosfsoptions.h>
#include <1541img/cbmdosvfs.h>
#include <1541img/d64.h>
#include <1541img/d64reader.h>
#include <1541img/d64writer.h>
#include <1541img/filedata.h>

#include <stdio.h>
#include <string.h>

static int g_checks = 0;

#define CHECK(cond)                                                            \
    do {                                                                       \
        ++g_checks;                                                            \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);    \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void) {
    const char *payload = "hello 1541";
    size_t plen = strlen(payload);

    D64 *disk = D64_create(D64_STANDARD);
    CHECK(disk != 0);
    CHECK(D64_tracks(disk) == 35);
    D64_destroy(disk);

    CbmdosFs *fs = CbmdosFs_create(CFO_DEFAULT);
    CHECK(fs != 0);
    CHECK(CbmdosFs_status(fs) == CFS_OK);
    CbmdosVfs *vfs = CbmdosFs_vfs(fs);
    CHECK(vfs != 0);

    CbmdosVfs_setName(vfs, "TESTDISK", 8);
    CbmdosVfs_setId(vfs, "01", 2);

    FileData *fd = FileData_create();
    CHECK(fd != 0);
    CHECK(FileData_append(fd, (const uint8_t *)payload, plen) >= 0);
    CHECK(FileData_size(fd) == plen);

    CbmdosFile *f = CbmdosFile_create();
    CHECK(f != 0);
    CHECK(CbmdosFile_setType(f, CFT_PRG) >= 0);
    CbmdosFile_setName(f, "HELLO", 5);
    CbmdosFile_setData(f, fd); /* takes ownership of fd */

    CHECK(CbmdosVfs_append(vfs, f) >= 0);
    CHECK(CbmdosFs_status(fs) == CFS_OK);
    CHECK(CbmdosVfs_fileCount(vfs) == 1);

    FILE *out = fopen("test-1541.d64", "wb");
    CHECK(out != 0);
    CHECK(writeD64(out, CbmdosFs_image(fs)) >= 0);
    fclose(out);
    CbmdosFs_destroy(fs); /* owns disk */

    FILE *in = fopen("test-1541.d64", "rb");
    CHECK(in != 0);
    D64 *disk2 = readD64(in);
    fclose(in);
    CHECK(disk2 != 0);

    CbmdosFs *fs2 = CbmdosFs_fromImage(disk2, CFO_DEFAULT);
    CHECK(fs2 != 0);
    CbmdosVfs *vfs2 = CbmdosFs_vfs(fs2);
    CHECK(CbmdosVfs_fileCount(vfs2) == 1);

    CbmdosFile *f2 = CbmdosVfs_file(vfs2, 0);
    CHECK(f2 != 0);
    uint8_t nlen = 0;
    const char *nm = CbmdosFile_name(f2, &nlen);
    CHECK(nm != 0 && nlen == 5 && memcmp(nm, "HELLO", 5) == 0);
    CHECK(CbmdosFile_type(f2) == CFT_PRG);

    const FileData *rd = CbmdosFile_rdata(f2);
    CHECK(rd != 0);
    CHECK(FileData_size(rd) == plen);
    CHECK(memcmp(FileData_rcontent(rd), payload, plen) == 0);

    CbmdosFs_destroy(fs2);

    printf("lib1541img consumer test PASS (%d checks)\n", g_checks);
    return 0;
}
