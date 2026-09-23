/* libzippp 7.1-1.10.1 —— 真实 zip 建包/读回往返（非 dlopen 空壳）。
 *
 * 判据：用 libzippp 的 ZipArchive 在**当前目录**建一个 zip（写入一条已知内容
 * 的条目），关闭后重新打开读回逐字节比对。这验证了 C++ 封装层 → libzip C 层
 * → zlib 压缩链路，桩实现过不了。
 *
 * 注意临时文件建在 CWD 而非 /tmp —— HarmonyOS 沙箱下 /tmp 不可写。
 */
#include <libzippp/libzippp.h>

#include <cstdio>
#include <cstring>
#include <string>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main() {
    const char* path = "lzpp_probe.zip";
    remove(path);

    /* ---------- 写侧：创建归档并写两条目 ---------- */
    {
        libzippp::ZipArchive z(path);
        CHECK(z.open(libzippp::ZipArchive::New), "open(New)");
        const char* payload = "hello libzippp on OHOS";
        CHECK(z.addData("dir/hello.txt", payload, strlen(payload)), "addData(dir/hello.txt)");
        z.close();
        CHECK(!z.isOpen(), "close after write");
    }

    /* ---------- 读侧：重新打开并读回 ---------- */
    {
        libzippp::ZipArchive z(path);
        CHECK(z.open(libzippp::ZipArchive::ReadOnly), "open(ReadOnly)");
        libzippp_int64 n = z.getNbEntries();
        CHECK(n >= 1, "getNbEntries>=1");
        libzippp::ZipEntry entry = z.getEntry("dir/hello.txt");
        CHECK(!entry.isNull(), "getEntry(dir/hello.txt)");
        if (!entry.isNull()) {
            std::string content = entry.readAsText();
            CHECK(content == std::string("hello libzippp on OHOS"), "readAsText roundtrip");
        }
        z.close();
    }

    remove(path);
    printf("%s: libzippp probe (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
