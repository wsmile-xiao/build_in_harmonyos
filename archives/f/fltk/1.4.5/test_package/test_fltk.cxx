// test_fltk.cxx — fltk 消费者行为验证（真实运行，非仅链接）
//
// 覆盖 4 组非 GUI 行为 + 1 组平台（OHOS/Linux）特有行为。全部断言只依赖
// 不接触 X display 的 API，因此在无显示设备的沙箱里可直接运行：
//
//   A 版本标识      FL_MAJOR/MINOR/PATCH_VERSION、FL_API_VERSION、
//                   Fl::version()/Fl::api_version()
//   B UTF-8 编解码  fl_utf8encode/fl_utf8decode 往返、fl_utf8len、
//                   fl_utf_nb_char、fl_utf8test 的非法序列拒绝
//   C 文件名语义    fl_filename_name/fl_filename_ext 的 Unix 分隔符行为
//                   （含"反斜杠不是分隔符"这一平台差异，见组内注释）
//   D 文本缓冲      Fl_Text_Buffer 的插入/长度/行数/查找/删除
//   E 平台特有      fl_utf8locale() 是纯 getenv 启发式（见 --expect-utf8locale）
//
// 退出码：全部通过 0，任一失败 1。

#include <FL/Fl.H>
#include <FL/Enumerations.H>
#include <FL/filename.H>
#include <FL/fl_utf8.h>
#include <FL/Fl_Text_Buffer.H>

#include <cstdio>
#include <cstring>
#include <cstdlib>

static int g_pass = 0;
static int g_fail = 0;

static void check(bool ok, const char *what) {
    if (ok) {
        ++g_pass;
        std::printf("  PASS  %s\n", what);
    } else {
        ++g_fail;
        std::printf("  FAIL  %s\n", what);
    }
}

static void check_int(long got, long want, const char *what) {
    if (got == want) {
        ++g_pass;
        std::printf("  PASS  %s (=%ld)\n", what, got);
    } else {
        ++g_fail;
        std::printf("  FAIL  %s: got %ld, want %ld\n", what, got, want);
    }
}

// ── A. 版本标识 ────────────────────────────────────────────────────────────
static void group_version() {
    std::printf("[A] version identity\n");
    check_int(FL_MAJOR_VERSION, 1, "FL_MAJOR_VERSION");
    check_int(FL_MINOR_VERSION, 4, "FL_MINOR_VERSION");
    check_int(FL_PATCH_VERSION, 5, "FL_PATCH_VERSION");
    check_int(FL_API_VERSION, 10405, "FL_API_VERSION");
    // Fl::version()/api_version() 是运行期取值，能通过说明 libfltk.a 里的
    // 版本表与头文件一致（头库不同步时这里会不一致）
    check_int(Fl::api_version(), 10405, "Fl::api_version()");
    check(Fl::version() > 1.04 && Fl::version() < 1.05, "Fl::version() in (1.04, 1.05)");
}

// ── B. UTF-8 编解码 ────────────────────────────────────────────────────────
static void group_utf8() {
    std::printf("[B] UTF-8 encode/decode\n");

    // 非 BMP：U+1F600 U+1F600 四字节序列 F0 9F 98 80
    char buf[8];
    std::memset(buf, 0, sizeof(buf));
    int n = fl_utf8encode(0x1F600, buf);
    check_int(n, 4, "fl_utf8encode(U+1F600) length");
    check((unsigned char)buf[0] == 0xF0 && (unsigned char)buf[1] == 0x9F &&
          (unsigned char)buf[2] == 0x98 && (unsigned char)buf[3] == 0x80,
          "U+1F600 encodes to F0 9F 98 80");

    int consumed = 0;
    unsigned back = fl_utf8decode(buf, buf + 4, &consumed);
    check_int((long)back, 0x1F600L, "fl_utf8decode round-trip value");
    check_int(consumed, 4, "fl_utf8decode consumed bytes");

    // 3 字节：U+4E2D 中 = E4 B8 AD
    int n3 = fl_utf8encode(0x4E2D, buf);
    check_int(n3, 3, "fl_utf8encode(U+4E2D) length");
    check((unsigned char)buf[0] == 0xE4 && (unsigned char)buf[1] == 0xB8 &&
          (unsigned char)buf[2] == 0xAD, "U+4E2D encodes to E4 B8 AD");

    // ASCII
    check_int(fl_utf8encode('A', buf), 1, "fl_utf8encode('A') length");
    check_int(buf[0], 'A', "fl_utf8encode('A') byte");

    // 首字节长度判定：0xF0 → 4，续字节 0x80 → -1
    check_int(fl_utf8len((char)0xF0), 4, "fl_utf8len(0xF0)");
    check_int(fl_utf8len((char)0x80), -1, "fl_utf8len(0x80) is continuation");

    // UTF-8 字符计数（"héllo" = h + 2 字节 é + llo，共 6 字节 5 字符）
    const char *mixed = "h\xC3\xA9llo";
    check_int((long)std::strlen(mixed), 6, "strlen(\"he<2-byte>llo\")");
    check_int(fl_utf_nb_char((const unsigned char *)mixed, 6), 5,
              "fl_utf_nb_char counts 5 chars in 6 bytes");

    // 合法性判定：纯 ASCII → 1；含 2 字节序列 → 2；非法首字节 → 0
    check_int(fl_utf8test("A", 1), 1, "fl_utf8test(ASCII) == 1");
    check_int(fl_utf8test(mixed, 6), 2, "fl_utf8test(2-byte seq) == 2");
    check_int(fl_utf8test("\xFF", 1), 0, "fl_utf8test(len-6 lead byte) == 0");

    // 非法序列的回退语义（FLTK 1.4.5 实测，不是标准建议的 U+FFFD）：
    // fl_utf8.cxx 里 ERRORS_TO_CP1252 / ERRORS_TO_ISO8859_1 都默认开，
    // 于是 0x80 这类孤立续字节按 CP1252 表译成 U+20AC（欧元符），
    // 只前进 1 字节。上游文档明确指出想要 REPLACEMENT CHARACTER
    // 必须自己按 len<2 改写——下面同时钉住这两条。
    int bad_len = 0;
    unsigned bad = fl_utf8decode("\x80", NULL, &bad_len);
    check_int((long)bad, 0x20ACL, "fl_utf8decode(0x80) -> CP1252 U+20AC");
    check_int(bad_len, 1, "fl_utf8decode(0x80) consumes 1 byte");

    // 落入 FAIL 分支的首字节（0xC0 < 0xc2、0xFF 是非法首字节）走
    // ERRORS_TO_ISO8859_1，原样返回该字节且只前进 1 字节
    int c0_len = 0, ff_len = 0;
    check_int((long)fl_utf8decode("\xC0", NULL, &c0_len), 0xC0L,
              "fl_utf8decode(0xC0) -> ISO-8859-1 0xC0");
    check_int(c0_len, 1, "fl_utf8decode(0xC0) consumes 1 byte");
    check_int((long)fl_utf8decode("\xFF", NULL, &ff_len), 0xFFL,
              "fl_utf8decode(0xFF) -> ISO-8859-1 0xFF");
    check_int(ff_len, 1, "fl_utf8decode(0xFF) consumes 1 byte");

    // 上游文档推荐的替代写法：自行探测 len<2 再换成 U+FFFD
    unsigned repl = (bad_len < 2) ? 0xFFFDu : bad;
    check_int((long)repl, 0xFFFDL, "documented len<2 idiom yields U+FFFD");
}

// ── C. 文件名语义 ──────────────────────────────────────────────────────────
static void group_filename() {
    std::printf("[C] filename semantics (Unix)\n");

    check(std::strcmp(fl_filename_name("/usr/lib"), "lib") == 0,
          "fl_filename_name(\"/usr/lib\") == \"lib\"");
    // FLTK 的 Unix 实现是"取最后一个 '/' 之后的部分"，与 basename(3) 在
    // 尾随斜杠/根路径上的行为不同
    check(std::strcmp(fl_filename_name("/usr/"), "") == 0,
          "fl_filename_name(\"/usr/\") == \"\"");
    check(std::strcmp(fl_filename_name("/"), "") == 0,
          "fl_filename_name(\"/\") == \"\"");
    check(std::strcmp(fl_filename_name("/usr"), "usr") == 0,
          "fl_filename_name(\"/usr\") == \"usr\"");
    // 平台差异：Unix/OHOS 上只有 '/' 是分隔符，Windows 路径整体返回。
    // 依赖此行为在 Linux/Windows 间搬运路径会出错，故显式钉住。
    const char *win = "C:\\Users\\a\\b.txt";
    check(std::strcmp(fl_filename_name(win), win) == 0,
          "fl_filename_name of a backslash path returns it unchanged");

    const char *ext = fl_filename_ext("/a/b/c.txt");
    check(ext != NULL && std::strcmp(ext, ".txt") == 0,
          "fl_filename_ext(\"/a/b/c.txt\") == \".txt\"");
    // 无扩展名时上游文档写 NULL，但 Fl_System_Driver::filename_ext 实际
    // 返回指向结尾 '\\0' 的指针（即空串），这里按真实实现钉住
    ext = fl_filename_ext("/a/b/c");
    check(ext != NULL && std::strcmp(ext, "") == 0,
          "fl_filename_ext(\"/a/b/c\") == \"\"");

    check(fl_filename_match("a.txt", "*.txt") != 0,
          "fl_filename_match(\"a.txt\", \"*.txt\") matches");
    check(fl_filename_match("a.txt", "*.c") == 0,
          "fl_filename_match(\"a.txt\", \"*.c\") does not match");
}

// ── D. Fl_Text_Buffer ──────────────────────────────────────────────────────
static void group_text_buffer() {
    std::printf("[D] Fl_Text_Buffer\n");

    Fl_Text_Buffer buf;
    buf.text("alpha\nbeta\ngamma");
    check_int(buf.length(), 16, "length after text()");
    // count_lines 数的是区间内的 '\n' 个数
    check_int(buf.count_lines(0, 16), 2, "count_lines over whole buffer");

    int found = -1;
    check_int(buf.search_forward(0, "beta", &found, 1), 1,
              "search_forward finds \"beta\"");
    check_int(found, 6, "search_forward position of \"beta\"");

    check_int(buf.search_forward(0, "delta", &found, 1), 0,
              "search_forward miss returns 0");

    buf.remove(0, 6);
    check_int(buf.length(), 10, "length after remove(0, 6)");
    check(std::strcmp(buf.text(), "beta\ngamma") == 0,
          "buffer content after remove");

    // 多字节内容下的位置语义：位置是"字节偏移"而非"字符偏移"
    Fl_Text_Buffer mb;
    mb.text("h\xC3\xA9llo");          // 6 bytes, 5 chars
    check_int(mb.length(), 6, "multibyte buffer length is byte length");
    int mb_pos = -1;
    check_int(mb.search_forward(0, "llo", &mb_pos, 1), 1,
              "search_forward across multibyte content");
    check_int(mb_pos, 3, "position is a byte offset");

    // 另一个 buffer 上的操作不影响已断言过的 mb（缓冲相互独立）
    buf.insert(0, "#");
    check_int(buf.length(), 11, "length after insert");
    check(std::strcmp(buf.text(), "#beta\ngamma") == 0, "content after insert");
    check(std::strcmp(mb.text(), "h\xC3\xA9llo") == 0,
          "other buffer untouched by unrelated ops");
}

// ── E. 平台特有：fl_utf8locale() 是纯 getenv 启发式 ─────────────────────────
//
// 由 test_package/conanfile.py 以不同 LC_ALL 多次调用本程序来断言：
//   LC_ALL=C        → 0
//   LC_ALL=C.UTF-8  → 1
//   LC_ALL=en_US.UTF-8 → 1
// 单次进程内无法验证（utf8locale() 把结果缓存在 static 里），故拆成多次进程。
static int probe_utf8locale(const char *want) {
    int got = fl_utf8locale();
    int expect = std::atoi(want);
    std::printf("fl_utf8locale()=%d (expect %d)\n", got, expect);
    return got == expect ? 0 : 1;
}

int main(int argc, char **argv) {
    if (argc == 3 && std::strcmp(argv[1], "--expect-utf8locale") == 0) {
        return probe_utf8locale(argv[2]);
    }

    std::printf("fltk consumer behaviour test\n");
    std::printf("runtime fl_utf8locale()=%d\n", fl_utf8locale());
    group_version();
    group_utf8();
    group_filename();
    group_text_buffer();

    std::printf("\nRESULT: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
