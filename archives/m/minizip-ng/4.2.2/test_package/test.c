/* minizip-ng 4.2.2 —— 真实 zip 建包/读回往返（非空壳）。
 *
 * 判据：用 mz_zip_writer/reader（handle API）在当前目录建 zip（写一条
 * deflate 压缩条目），关闭后重开 locate+open+read 逐字节比对。
 * 覆盖 mz_os/mz_strm/mz_zip/zlib 全链路，桩实现过不了。
 * 注意临时文件建在 CWD 而非 /tmp —— HarmonyOS 沙箱下 /tmp 不可写。
 */
#include <minizip/mz.h>
#include <minizip/mz_os.h>
#include <minizip/mz_strm.h>
#include <minizip/mz_zip.h>
#include <minizip/mz_zip_rw.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    const char* path = "mzn_probe.zip";
    const char* payload = "minizip-ng roundtrip on HarmonyOS PC";
    void* writer = NULL;
    void* reader = NULL;

    mz_os_unlink(path);

    /* ---------- 写侧：writer handle + add_buffer（deflate） ---------- */
    {
        mz_zip_file info;
        memset(&info, 0, sizeof(info));
        info.filename = "plain/hello.txt";
        info.compression_method = MZ_COMPRESS_METHOD_DEFLATE;

        writer = mz_zip_writer_create();
        CHECK(writer != NULL, "mz_zip_writer_create");
        CHECK(mz_zip_writer_open_file(writer, path, 0, 0) == MZ_OK, "writer_open_file");
        CHECK(mz_zip_writer_add_buffer(writer, payload, (int32_t)strlen(payload), &info) == MZ_OK,
              "add_buffer (deflate)");
        mz_zip_writer_close(writer);
        mz_zip_writer_delete(&writer);
    }

    /* ---------- 读侧：reader handle + locate/open/read ---------- */
    {
        char buf[256];
        int32_t n = 0;
        memset(buf, 0, sizeof(buf));

        reader = mz_zip_reader_create();
        CHECK(reader != NULL, "mz_zip_reader_create");
        CHECK(mz_zip_reader_open_file(reader, path) == MZ_OK, "reader_open_file");
        CHECK(mz_zip_reader_locate_entry(reader, "plain/hello.txt", 1) == MZ_OK,
              "locate_entry plain/hello.txt");
        CHECK(mz_zip_reader_entry_open(reader) == MZ_OK, "entry_open");
        n = mz_zip_reader_entry_read(reader, buf, sizeof(buf) - 1);
        CHECK(n == (int32_t)strlen(payload), "entry_read size");
        CHECK(strcmp(buf, payload) == 0, "deflate roundtrip content");
        mz_zip_reader_close(reader);
        mz_zip_reader_delete(&reader);
    }

    mz_os_unlink(path);
    printf("%s: minizip-ng probe (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
