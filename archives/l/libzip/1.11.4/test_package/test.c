/* libzip 1.11.4 —— 真实建包/读回往返（非 dlopen 空壳）。
 *
 * 判据：在**当前目录**建一个 zip（写入一条已知内容的条目），关闭后重新打开读回，
 * 逐字节比对。这验证了压缩、目录写入、重新解析三条链路，桩实现过不了。
 *
 * 注意临时文件建在 CWD 而非 /tmp —— HarmonyOS 沙箱下 /tmp 不可写
 * （本仓 musl-fts 踩过同样的坑）。
 */
#include <zip.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    const char *path = "./_libzip_probe.zip";
    const char *payload = "harmony-pc libzip roundtrip";
    const size_t plen = strlen(payload);
    unlink(path);

    int err = 0;
    zip_t *z = zip_open(path, ZIP_CREATE | ZIP_TRUNCATE, &err);
    CHECK(z != NULL, "zip_open(CREATE) 成功");
    if (!z) return 1;

    zip_source_t *src = zip_source_buffer(z, payload, plen, 0);
    CHECK(src != NULL, "zip_source_buffer 成功");
    zip_int64_t idx = zip_file_add(z, "hello.txt", src, ZIP_FL_OVERWRITE);
    CHECK(idx >= 0, "zip_file_add 成功");
    CHECK(zip_close(z) == 0, "zip_close 写盘成功");

    zip_t *z2 = zip_open(path, ZIP_RDONLY, &err);
    CHECK(z2 != NULL, "重新 zip_open(RDONLY) 成功");
    if (z2) {
        CHECK(zip_get_num_entries(z2, 0) == 1, "包内恰好 1 个条目");
        zip_file_t *f = zip_fopen(z2, "hello.txt", 0);
        CHECK(f != NULL, "zip_fopen(hello.txt) 成功");
        if (f) {
            char buf[128];
            memset(buf, 0, sizeof(buf));
            zip_int64_t n = zip_fread(f, buf, sizeof(buf) - 1);
            printf("     读回 %lld 字节: %s\n", (long long)n, buf);
            CHECK((size_t)n == plen && memcmp(buf, payload, plen) == 0,
                  "读回内容与写入逐字节相同");
            zip_fclose(f);
        }
        zip_close(z2);
    }
    unlink(path);

    if (failures) { fprintf(stderr, "\nlibzip: %d 项断言失败\n", failures); return 1; }
    printf("\nlibzip 1.11.4: 全部断言通过（建包 → 读回往返）\n");
    return 0;
}
