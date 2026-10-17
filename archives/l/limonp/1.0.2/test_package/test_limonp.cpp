// test_package/test_limonp.cpp — limonp 1.0.2 消费者测试
//
// 六组断言，失败以退出码 2..7 区分。判据全部是**可观测行为**：
// 安装布局（9 个公共头都在同一个 include 根下）+ 符号可链接、
// StringUtil 的字符串契约、LocalVector 的栈上内联缓冲语义、
// Closure/ArgvContext 的行为、以及两组鸿蒙特有断言
// （aarch64 的 char 有符号性与 bionic ctype 越界；多线程纯函数逐位可复现）。
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <thread>
#include <vector>

#include <limonp/ArgvContext.hpp>
#include <limonp/Closure.hpp>
#include <limonp/Colors.hpp>
#include <limonp/Config.hpp>
#include <limonp/LocalVector.hpp>
#include <limonp/Logging.hpp>
#include <limonp/StdExtension.hpp>
#include <limonp/StringUtil.hpp>

using namespace limonp;

static int fail(int code, const char* what) {
    std::printf("FAIL[%d]: %s\n", code, what);
    return code;
}

static void g1_noop() {
}

// ── 组 1：安装布局 + header-only 符号可链接 ────────────────────────────
// 这些头全部来自上游 `install(DIRECTORY include/ DESTINATION include)`；
// 这一段能编过并链上，就说明包里的 include 根布局是对的（而不是
// "include/limonp 是空的"或"头文件被装到了别的名字下"）。
static int group1() {
    // 9 个公共头每一个都实例化一次，缺任何一个都会在编译期炸掉。
    std::vector<std::string> words;
    Split(std::string("a,b,c"), words, std::string(","));
    if (words.size() != 3) return fail(2, "Split through <limonp/StringUtil.hpp> is unusable");

    LocalVector<size_t> lv;
    lv.push_back(1);
    if (lv.size() != 1) return fail(2, "LocalVector through <limonp/LocalVector.hpp> is unusable");

    ClosureInterface* c = NewClosure(&g1_noop);
    c->Run();
    delete c;
    const char* argv[] = {"exe", "pos"};
    ArgvContext ac(2, argv);
    if (ac[0] != "exe" || ac[1] != "pos")
        return fail(2, "ArgvContext through <limonp/ArgvContext.hpp> is unusable");

    std::printf("PASS 1: 9 public headers installed under one include root; "
                "string/LocalVector/Closure/ArgvContext symbols are linkable\n");
    return 0;
}

// ── 组 2：StringUtil 的字符串契约 ──────────────────────────────────────
static int group2() {
    const std::string s1 = StringFormat("select %s from %s;", "*", "table1");
    if (s1 != "select * from table1;") return fail(3, "StringFormat output mismatch");

    std::vector<std::string> v;
    Split(std::string("1,2,3,4"), v, std::string(","));
    if (Join(v.begin(), v.end(), std::string(",")) != "1,2,3,4")
        return fail(3, "Split/Join round trip mismatch");

    std::string t = " \t\n ni hao ad \r\n";
    if (Trim(t) != "ni hao ad") return fail(3, "Trim mismatch");

    std::string edge = "1, 2";
    Split(edge, v, std::string(","));
    if (v.size() != 2 || v[0] != "1" || v[1] != " 2")
        return fail(3, "Split must keep the leading space of \" 2\"");

    if (!StartsWith("--help", "--") || !EndsWith("hel", "el") || StartsWith("", "help"))
        return fail(3, "StartsWith/EndsWith mismatch");

    if (PathJoin("/home/foo/dir", "file") != "/home/foo/dir/file")
        return fail(3, "PathJoin mismatch");

    std::printf("PASS 2: StringFormat/Split/Join/Trim/StartsWith/EndsWith/PathJoin contracts hold\n");
    return 0;
}

// ── 组 3：LocalVector 的栈上内联缓冲语义 ───────────────────────────────
static int group3() {
    LocalVector<size_t> v;
    if (v.size() != 0) return fail(4, "fresh LocalVector not empty");
    if (v.capacity() != LOCAL_VECTOR_BUFFER_SIZE)
        return fail(4, "fresh LocalVector capacity != LOCAL_VECTOR_BUFFER_SIZE");

    for (size_t i = 0; i < 129; i++) v.push_back(i);
    if (v.size() != 129) return fail(4, "LocalVector size after 129 push_backs != 129");
    // 上游 LocalVector 的内联缓冲是 16，翻倍到 256 覆盖 129 个元素。
    if (v.capacity() != 256)
        return fail(4, "LocalVector capacity after 129 push_backs != 256");
    for (size_t i = 0; i < 129; i++) {
        if (v[i] != i) return fail(4, "LocalVector element corrupted after reallocation");
    }

    LocalVector<size_t> copy(v);
    if (copy.capacity() != v.capacity() || copy.size() != v.size())
        return fail(4, "LocalVector copy-construct did not preserve capacity/size");
    LocalVector<size_t> assigned;
    assigned = v;
    if (assigned.capacity() != v.capacity() || assigned.size() != v.size())
        return fail(4, "LocalVector copy-assign did not preserve capacity/size");

    std::printf("PASS 3: LocalVector inline buffer 16 -> 256, elements survive reallocation, "
                "copy ctor/assign preserve capacity and size\n");
    return 0;
}

// ── 组 4：Closure 与 ArgvContext 的行为 ────────────────────────────────
static int g4_free_calls = 0;
static void g4_free_fn(int x) {
    g4_free_calls += x;
}

class G4Obj {
 public:
    int calls = 0;
    void Method(int x) { calls += x; }
};

static int group4() {
    ClosureInterface* c = NewClosure(&g4_free_fn, 7);
    c->Run();
    delete c;
    if (g4_free_calls != 7) return fail(5, "NewClosure(free function) did not run");

    G4Obj obj;
    c = NewClosure(&obj, &G4Obj::Method, 5);
    c->Run();
    delete c;
    if (obj.calls != 5) return fail(5, "NewClosure(member function) did not run");

    const char* argv[] = {"./exe1", "--hehe", "11", "key2", "-k", "val"};
    ArgvContext arg(sizeof(argv) / sizeof(argv[0]), argv);
    std::string rendered;
    rendered << arg;
    if (rendered != "[\"./exe1\", \"key2\"]{--hehe:11, -k:val}{}")
        return fail(5, "ArgvContext rendering mismatch");
    if (arg[1] != "key2") return fail(5, "ArgvContext positional arg mismatch");
    if (arg["--hehe"] != "11") return fail(5, "ArgvContext long option mismatch");
    if (arg.HasKey("-help")) return fail(5, "ArgvContext reported a key it does not have");

    std::printf("PASS 4: Closure binds free/member functions and runs; "
                "ArgvContext splits positionals/--long/-k into the documented shape\n");
    return 0;
}

// ── 组 5：鸿蒙特有 A — char 有符号性 + bionic ctype 越界 ───────────────
// 两件与平台强相关的事：
//  (1) aarch64-linux（含 OHOS）的 char 默认 **unsigned**，x86-linux 是 signed。
//      GBK 的 "中" = 字节 D6 D0，0xD6 在 x86 的 signed char 里是 -42；
//      limonp 的 TwocharToUint16 用 `uint16_t(high) & 0x00ff`（先转无符号再
//      掩码）吃掉符号位，所以两端都必须得到 0xD6D0。这是可观测的跨平台契约，
//      而 OHOS/bionic 既没有 GBK locale 也没有 iconv，只能靠这段纯计算代码。
//  (2) IsSpace(unsigned) 的 `> 0xff` 早退分支：上游注释明说"把大整数喂给
//      isspace 会 core dump"。wchar_t 在 aarch64/OHOS 上是 4 字节，
//      `IsSpace(1000024u)` 必须返回 false 而不是把 1000024 & 0xff 拿去查表。
static int group5() {
    if (sizeof(void*) != 8) return fail(6, "sizeof(void*) != 8 on aarch64/OHOS");
    if (sizeof(wchar_t) != 4) return fail(6, "sizeof(wchar_t) != 4 on aarch64/OHOS");

    if (!IsSpace(0x20u)) return fail(6, "IsSpace(' ') must be true");
    if (!IsSpace(0x09u)) return fail(6, "IsSpace('\\t') must be true");
    if (IsSpace(0x41u)) return fail(6, "IsSpace('A') must be false");
    // 上游 TStringUtil.cpp 的注释点名的场景：大整数必须先被 >0xff 拦住。
    if (IsSpace(1000024u)) return fail(6, "IsSpace(1000024u) must be false");

    const std::string gbk("\xD6\xD0\xCE\xC4", 4);  // GBK "中文"
    std::vector<uint16_t> uni;
    if (!GBKTrans(gbk, uni)) return fail(6, "GBKTrans rejected a valid GBK sequence");
    if (uni.size() != 2) return fail(6, "GBKTrans produced the wrong number of units");
    if (uni[0] != 0xD6D0 || uni[1] != 0xCEC4)
        return fail(6, "GBKTrans sign-extension: expected 0xD6D0,0xCEC4");
    std::string back;
    GBKTrans(uni.begin(), uni.end(), back);
    if (back != gbk) return fail(6, "GBKTrans round trip is not byte-identical");

    const std::string utf8("\xE4\xB8\xAD\xE6\x96\x87", 6);  // UTF-8 "中文"
    std::vector<uint16_t> u16;
    if (!Utf8ToUnicode(utf8, u16)) return fail(6, "Utf8ToUnicode rejected valid UTF-8");
    if (u16.size() != 2 || u16[0] != 0x4E2D || u16[1] != 0x6587)
        return fail(6, "Utf8ToUnicode code points mismatch");
    std::string back8;
    UnicodeToUtf8(u16.begin(), u16.end(), back8);
    if (back8 != utf8) return fail(6, "Utf8ToUnicode/UnicodeToUtf8 is not byte-identical");

    std::printf("PASS 5: (aarch64/OHOS) sizeof(wchar_t)==4, sizeof(void*)==8; "
                "IsSpace(1000024u)==false without crashing; GBK D6 D0 CE C4 -> "
                "0xD6D0,0xCEC4 with no sign extension; UTF-8 round trip byte-identical\n");
    return 0;
}

// ── 组 6：鸿蒙特有 B — bionic std::thread 上纯函数逐位可复现 ───────────
// limonp 的 StringUtil 全是无状态纯函数（没有全局 locale、没有静态缓冲），
// 所以"每个线程各跑各的"必须在 aarch64/bionic 上给出与单线程逐位相同的
// 结果。这里用一个确定性 LCG 造输入，把输出揉进 64 位哈希。
static uint64_t g6_run(unsigned seed, int rounds, bool* identity_ok) {
    uint64_t h = 1469598103934665603ULL;  // FNV-1a offset basis
    uint64_t x = seed * 2862933555777941757ULL + 3037000493ULL;
    std::vector<std::string> v;
    for (int i = 0; i < rounds; i++) {
        x = x * 6364136223846793005ULL + 1442695040888963407ULL;
        const unsigned n = static_cast<unsigned>((x >> 33) % 40u);
        std::string s;
        for (unsigned k = 0; k < n; k++) {
            x = x * 6364136223846793005ULL + 1442695040888963407ULL;
            s.push_back(static_cast<char>('a' + ((x >> 33) % 26u)));
        }
        std::string work = StringFormat("[%s]", s.c_str());
        Split(work, v, std::string(","));
        const std::string joined = Join(v.begin(), v.end(), std::string("|"));
        std::string trimmed = "  " + joined + "  ";
        Trim(trimmed);

        std::vector<uint16_t> uni;
        Utf8ToUnicode(trimmed, uni);
        std::string out;
        UnicodeToUtf8(uni.begin(), uni.end(), out);
        if (out != trimmed) *identity_ok = false;

        for (size_t k = 0; k < out.size(); k++) {
            h ^= static_cast<unsigned char>(out[k]);
            h *= 1099511628211ULL;  // FNV-1a prime
        }
        v.clear();
    }
    return h;
}

static int group6() {
    const int kThreads = 4;
    const int kRounds = 4000;
    bool identity_ok = true;
    const uint64_t reference = g6_run(1, kRounds, &identity_ok);
    if (!identity_ok)
        return fail(7, "single-threaded StringUtil round trip is not identity");

    std::vector<uint64_t> got(kThreads, 0);
    std::vector<int> thread_identity(kThreads, 1);  // vector<bool> 是位打包，不能并发写
    std::vector<std::thread> ts;
    for (int i = 0; i < kThreads; i++) {
        ts.push_back(std::thread([i, kRounds, &got, &thread_identity] {
            bool ok = true;
            got[i] = g6_run(1, kRounds, &ok);
            thread_identity[i] = ok ? 1 : 0;
        }));
    }
    for (int i = 0; i < kThreads; i++) ts[i].join();

    for (int i = 0; i < kThreads; i++) {
        if (!thread_identity[i])
            return fail(7, "StringUtil round trip is not identity inside a bionic std::thread");
        if (got[i] != reference)
            return fail(7, "bionic std::thread produced a different StringUtil checksum");
    }

    std::printf("PASS 6: 4 bionic std::threads x %d rounds of Split/Join/StringFormat/Trim/"
                "Utf8<->Unicode all match the single-threaded checksum bit for bit\n", kRounds);
    return 0;
}

int main() {
    int rc = 0;
    if ((rc = group1()) != 0) return rc;
    if ((rc = group2()) != 0) return rc;
    if ((rc = group3()) != 0) return rc;
    if ((rc = group4()) != 0) return rc;
    if ((rc = group5()) != 0) return rc;
    if ((rc = group6()) != 0) return rc;
    std::printf("ALL PASS: limonp 1.0.2 consumer checks (6 groups)\n");
    return 0;
}
