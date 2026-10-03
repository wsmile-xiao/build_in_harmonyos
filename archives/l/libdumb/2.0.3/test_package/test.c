/* libdumb 2.0.3 —— DUMBFILE 内存往返探针(非链接空壳)。
 *
 * 正向:dumbfile_open_memory 打开内存缓冲,dumbfile_getc 逐字节读回,
 *       文件尾语义(getc 越界返回负值),dumbfile_close;
 * 收尾:dumb_exit()。
 *
 * 注意:不要在探针里调 dumb_load_xm 等文件加载 helper 的"不存在文件"错误
 * 路径——上游 2.0.3 的 dumb_load_xm 对打开失败的 DUMBFILE 未做空指针防护,
 * 会段错误(真实上游缺陷,已记录 notes.md);消费者必须自行保证文件存在。
 */
#include <dumb.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(c, m) do { if (!(c)) { fprintf(stderr, "[FAIL] %s (%s:%d)\n", (m), __FILE__, __LINE__); ++failures; } \
                         else printf("[ok] %s\n", (m)); } while (0)

int main(void) {
    static const char payload[] = {0x01, 0x02, 0x03, 0x7F};
    DUMBFILE *f = dumbfile_open_memory(payload, sizeof(payload));
    CHECK(f != NULL, "dumbfile_open_memory");

    int bad = 0;
    for (size_t i = 0; i < sizeof(payload); ++i) {
        int c = dumbfile_getc(f);
        if (c != (unsigned char)payload[i]) ++bad;
    }
    CHECK(bad == 0, "dumbfile_getc roundtrip (4 bytes)");

    int eof = dumbfile_getc(f);
    CHECK(eof < 0, "getc past end returns negative (EOF)");

    dumbfile_close(f);
    CHECK(1, "dumbfile_close");

    dumb_exit();
    CHECK(1, "dumb_exit");

    printf("%s: libdumb probe (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
