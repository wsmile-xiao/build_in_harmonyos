//
// test_lazperf.cpp — 消费者视角验证 lazperf 3.4.0（OpenHarmony / HarmonyOS PC aarch64）
//
// 只使用上游 install() 安装的公开头文件（lazperf/{lazperf,header,readers,writers,vlr,filestream}.hpp
// 以及被 RENAME 安装的 lazperf/lazperf_base.hpp），即真实使用者的编译面。
//
// 场景一（鸿蒙特有）：只读根文件系统 / 无 /var/tmp 下的临时路径解析
//     上游 cpp/test/io_tests.cpp 的 makeTempFileName() 把临时文件写死成
//     "/var/tmp/fnXXXXXX"。OHOS 上 / 与 /var/tmp 可能根本不存在或只读，mkstemp()
//     失败后被忽略，后续 ofstream 静默产出空文件——7 个用例因此失败
//     （E002 家族：鸿蒙 /tmp 只读，通用方案是把 TMPDIR 指向可写目录）。
//     库本身对临时路径零假设，本场景证明：只要调用方给出一个可写目录
//     （$TMPDIR，退回 $HOME，最后 .），整条 LAZ 写-读链路就能工作，
//     且该目录不是 /tmp 也不是 /var/tmp。
// 场景二：LAZ 写-读往返 + LAZ VLR 元数据（消费者契约）
// 场景三：aarch64/LP64 与非对齐点记录访问（严格对齐架构）
// 场景四：多线程压缩确定性（上游测试完全无线程覆盖）
// 场景五：HMDFS 目录语义：写盘-关闭-立即重开字节一致
//
#include <lazperf/filestream.hpp>
#include <lazperf/header.hpp>
#include <lazperf/lazperf.hpp>
#include <lazperf/readers.hpp>
#include <lazperf/vlr.hpp>
#include <lazperf/writers.hpp>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include <sys/stat.h>
#ifdef _WIN32
#include <direct.h>
#include <io.h>
#define LAZPERF_TEST_ACCESS _access
#define LAZPERF_TEST_MKDIR(p) _mkdir(p)
#else
#include <unistd.h>
#define LAZPERF_TEST_ACCESS access
#define LAZPERF_TEST_MKDIR(p) ::mkdir((p), 0755)
#endif

namespace
{

unsigned gChecks = 0;
unsigned gFailures = 0;

void check(bool ok, const std::string& what)
{
    ++gChecks;
    if (!ok)
    {
        ++gFailures;
        std::cout << "[ FAIL ] " << what << std::endl;
    }
    else
        std::cout << "[  ok  ] " << what << std::endl;
}

template <typename A, typename B>
void checkEq(const A& a, const B& b, const std::string& what)
{
    ++gChecks;
    if (!(a == b))
    {
        ++gFailures;
        std::cout << "[ FAIL ] " << what << "  (got " << a << ", want " << b << ")"
                  << std::endl;
    }
    else
        std::cout << "[  ok  ] " << what << std::endl;
}

bool pathExists(const std::string& p)
{
    std::ifstream f(p, std::ios::binary);
    return f.good();
}

bool dirWritable(const std::string& p)
{
#ifdef _WIN32
    return LAZPERF_TEST_ACCESS(p.c_str(), 2) == 0;
#else
    return LAZPERF_TEST_ACCESS(p.c_str(), W_OK) == 0;
#endif
}

std::string envOr(const char* name, const std::string& fallback)
{
    const char* v = std::getenv(name);
    return (v && *v) ? std::string(v) : fallback;
}

bool pathExistsIsDir(const std::string& p)
{
#ifdef _WIN32
    struct _stat st;
    if (::_stat(p.c_str(), &st) != 0)
        return false;
    return (st.st_mode & _S_IFDIR) != 0;
#else
    struct stat st;
    if (::stat(p.c_str(), &st) != 0)
        return false;
    return (st.st_mode & S_IFMT) == S_IFDIR;
#endif
}

void mkdirP(const std::string& p)
{
    if (p.empty() || p == "/" || pathExistsIsDir(p))
        return;
    const size_t slash = p.find_last_of("/\\");
    if (slash != std::string::npos && slash > 0)
        mkdirP(p.substr(0, slash));
    LAZPERF_TEST_MKDIR(p.c_str());
}

// mkdir -p，返回是否最终可写
bool ensureDir(const std::string& p)
{
    if (p.empty())
        return false;
    if (!pathExistsIsDir(p))
        mkdirP(p);
    return dirWritable(p);
}

// 场景一的解析顺序：$TMPDIR → $HOME/.lazperf-test-scratch → 当前目录。
// 刻意与上游写死的 "/var/tmp/fnXXXXXX" 无关：OHOS 上 /var/tmp 可能不存在或只读。
std::string scratchRoot()
{
    std::string t = envOr("TMPDIR", "");
    if (!t.empty() && ensureDir(t))
        return t;

    std::string home = envOr("HOME", "");
    if (!home.empty())
    {
        std::string h = home + "/.lazperf-test-scratch";
        if (ensureDir(h))
            return h;
    }
    return ".";
}

uint64_t fileSize(const std::string& p)
{
    std::ifstream f(p, std::ios::binary | std::ios::ate);
    if (!f.good())
        return 0;
    return static_cast<uint64_t>(f.tellg());
}

std::string readAll(const std::string& p)
{
    std::ifstream f(p, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(f)),
                       std::istreambuf_iterator<char>());
}

// 20 字节的 LAS point format 0 记录：x/y/z/as_intensity/bitfields/classification/...
// 逐字节自造，避免依赖未安装的 lazperf/las.hpp。
const int kPointSize = 20;
const int kPointCount = 1000;

std::vector<char> makePoints(int count)
{
    std::vector<char> buf(static_cast<size_t>(count) * kPointSize, 0);
    for (int i = 0; i < count; ++i)
    {
        char* p = buf.data() + static_cast<size_t>(i) * kPointSize;
        int32_t x = 100000 + i * 37;
        int32_t y = -200000 + i * 11;
        int32_t z = 30000 + (i % 97);
        std::memcpy(p + 0, &x, 4);
        std::memcpy(p + 4, &y, 4);
        std::memcpy(p + 8, &z, 4);
        uint16_t intensity = static_cast<uint16_t>(i % 65535);
        std::memcpy(p + 12, &intensity, 2);
        p[14] = 0x09;   // return number / number of returns
        p[15] = 0x05;   // classification
        p[16] = 0x07;   // scan angle rank
    }
    return buf;
}

} // namespace

int main()
{
    std::cout << "===== lazperf 3.4.0 test_package (OHOS aarch64) =====" << std::endl;
    std::cout << "LAZPERF_VERSION = " << LAZPERF_MAJOR_VERSION << "."
              << LAZPERF_MINOR_VERSION << "." << LAZPERF_REVISION << std::endl;

    // ─────────────────────────────────────────────────────────────────────
    // 场景一：只读根文件系统 / 无 /var/tmp 下的临时路径解析（鸿蒙特有）
    // ─────────────────────────────────────────────────────────────────────
    const std::string tmpdirRaw = envOr("TMPDIR", "(unset)");
    const std::string homeRaw = envOr("HOME", "(unset)");
    const bool varTmpExists = pathExistsIsDir("/var/tmp");
    const bool varTmpWritable = varTmpExists && dirWritable("/var/tmp");
    const bool slashTmpWritable = pathExistsIsDir("/tmp") && dirWritable("/tmp");

    std::cout << "[probe] TMPDIR=" << tmpdirRaw << " HOME=" << homeRaw
              << " /var/tmp exists=" << varTmpExists
              << " writable=" << varTmpWritable
              << " /tmp writable=" << slashTmpWritable << std::endl;

    const std::string scratch = scratchRoot();
    check(!scratch.empty(), "场景一：解析出可写临时目录（$TMPDIR → $HOME → .）");
    check(dirWritable(scratch), "场景一：解析出的临时目录可写: " + scratch);
    // 该目录必须不是写死的 /var/tmp —— OHOS 上它常常不存在或只读。
    check(scratch != "/var/tmp" && scratch != "/var/tmp/",
          "场景一：临时目录并非写死的 /var/tmp");
    // 无论 /var/tmp 是否可用，写-读链路都必须成功（上游 io_tests 的 7 个用例在
    // /var/tmp 不可写时必然失败，这里证明库代码本身对此零假设）。
    std::cout << "[probe] 上游 io_tests 的 /var/tmp 假设在本环境下 "
              << (varTmpWritable ? "恰好成立" : "会失败（这正是本适配修复的缺陷）")
              << std::endl;

    const std::string scratchLaz = scratch + "/lazperf-scratch-roundtrip.laz";
    {
        lazperf::writer::named_file::config c({0.01, 0.01, 0.01}, {0.0, 0.0, 0.0});
        c.pdrf = 0;
        lazperf::writer::named_file out(scratchLaz, c);
        const std::vector<char> pts = makePoints(kPointCount);
        for (int i = 0; i < kPointCount; ++i)
            out.writePoint(pts.data() + static_cast<size_t>(i) * kPointSize);
        out.close();
    }
    check(pathExists(scratchLaz),
          "场景一：LAZ 文件在临时目录中真实落盘: " + scratchLaz);

    {
        lazperf::reader::named_file in(scratchLaz);
        checkEq(static_cast<uint64_t>(in.pointCount()),
                static_cast<uint64_t>(kPointCount),
                "场景一：临时目录中的 LAZ 可被重新打开且点数一致");
    }

    // ─────────────────────────────────────────────────────────────────────
    // 场景二：LAZ 写-读往返 + LAZ VLR 元数据
    // ─────────────────────────────────────────────────────────────────────
    const std::vector<char> points = makePoints(kPointCount);
    const std::string roundtrip = scratch + "/lazperf-roundtrip.laz";
    {
        lazperf::writer::named_file::config c({0.01, 0.01, 0.01}, {0.0, 0.0, 0.0});
        c.pdrf = 0;
        c.chunk_size = 500;
        lazperf::writer::named_file out(roundtrip, c);
        for (int i = 0; i < kPointCount; ++i)
            out.writePoint(points.data() + static_cast<size_t>(i) * kPointSize);
        out.close();
    }

    checkEq(fileSize(roundtrip) > 0, true, "场景二：写出的 LAZ 文件非空");
    checkEq(readAll(roundtrip).compare(0, 4, "LASF"), 0,
            "场景二：文件魔数为 LASF");

    {
        lazperf::reader::named_file in(roundtrip);
        checkEq(static_cast<uint64_t>(in.pointCount()),
                static_cast<uint64_t>(kPointCount), "场景二：reader 报告点数一致");

        const lazperf::header14& h = in.header();
        checkEq(static_cast<int>(h.point_format_id), 0, "场景二：point_format_id == 0");
        checkEq(static_cast<int>(h.point_record_length), kPointSize,
                "场景二：point_record_length == 20");
        checkEq(static_cast<int>(h.version.minor), 3, "场景二：按默认写出 LAS 1.3");
        checkEq(h.scale.x, 0.01, "场景二：scale.x 往返");
        checkEq(h.offset.y, 0.0, "场景二：offset.y 往返");

        const lazperf::laz_vlr lazv = in.lazVlr();
        checkEq(static_cast<int>(lazv.compressor), 2,
                "场景二：LAZ VLR compressor == 2 (chunked, point format ≤ 5)");
        checkEq(static_cast<int>(lazv.chunk_size), 500, "场景二：chunk_size 往返");
        checkEq(static_cast<int>(lazv.ver_major), 3, "场景二：LASzip ver_major == 3");
        checkEq(static_cast<int>(lazv.ver_minor), 4, "场景二：LASzip ver_minor == 4");
        checkEq(static_cast<int>(lazv.revision), 3, "场景二：LASzip revision == 3");
        // lazperf 的 item type 常量（POINT10 = 6）定义在 vlr.cpp 的匿名枚举里，
        // 未随头文件导出，故此处写字面量 6 并在此说明其来源。
        checkEq(static_cast<int>(lazv.items.size()), 1,
                "场景二：point format 0 的 LAZ VLR 恰有 1 个 item");
        checkEq(static_cast<int>(lazv.items[0].type), 6,
                "场景二：items[0].type == POINT10 (6)");
        checkEq(static_cast<int>(lazv.items[0].size), 20,
                "场景二：items[0].size == 20");

        // 逐点读回并与写入的原始记录逐字节比对
        std::vector<char> back(static_cast<size_t>(kPointCount) * kPointSize, 0);
        for (int i = 0; i < kPointCount; ++i)
            in.readPoint(back.data() + static_cast<size_t>(i) * kPointSize);
        checkEq(std::memcmp(back.data(), points.data(),
                            static_cast<size_t>(kPointCount) * kPointSize), 0,
                "场景二：1000 个点记录逐字节往返一致");
    }

    // header 尺寸契约（消费者按 sizeof 分配缓冲区，位宽错误即在 aarch64 上越界）
    checkEq(lazperf::header12::Size, static_cast<size_t>(227), "场景二：header12::Size == 227");
    checkEq(lazperf::header13::Size, static_cast<size_t>(235), "场景二：header13::Size == 235");
    checkEq(lazperf::header14::Size, static_cast<size_t>(375), "场景二：header14::Size == 375");
    checkEq(lazperf::baseCount(0), 20, "场景二：point format 0 baseCount == 20");
    checkEq(lazperf::baseCount(3), 34, "场景二：point format 3 baseCount == 34");
    checkEq(lazperf::baseCount(6), 30, "场景二：point format 6 baseCount == 30");

    // ─────────────────────────────────────────────────────────────────────
    // 场景三：aarch64 / LP64 与非对齐点记录访问
    // ─────────────────────────────────────────────────────────────────────
    checkEq(static_cast<int>(sizeof(void*)), 8, "场景三：LP64（指针 8 字节）");
    checkEq(static_cast<int>(sizeof(long)), 8, "场景三：LP64（long 8 字节）");

    {
        // 非对齐输入：把点记录放在缓冲区 +3 处。aarch64 的严格对齐下，
        // 编解码器若做了对齐假设就会 SIGBUS/结果错乱。
        const std::vector<char> pts = makePoints(16);
        std::vector<char> inBuf(16 * kPointSize + 8, 0);
        char* misaligned = inBuf.data() + 3;
        std::memcpy(misaligned, pts.data(), 16 * kPointSize);

        lazperf::writer::chunk_compressor comp(0, 0);
        for (int i = 0; i < 16; ++i)
            comp.compress(misaligned + static_cast<size_t>(i) * kPointSize);
        std::vector<unsigned char> chunk = comp.done();
        check(!chunk.empty(), "场景三：非对齐输入可压缩出非空 chunk");

        std::vector<char> outBuf(16 * kPointSize + 8, 0);
        char* misalignedOut = outBuf.data() + 5;
        lazperf::reader::chunk_decompressor dec(
            0, 0, reinterpret_cast<const char*>(chunk.data()));
        for (int i = 0; i < 16; ++i)
            dec.decompress(misalignedOut + static_cast<size_t>(i) * kPointSize);
        checkEq(std::memcmp(misalignedOut, pts.data(), 16 * kPointSize), 0,
                "场景三：非对齐 chunk 压缩/解压往返逐字节一致");
    }

    // ─────────────────────────────────────────────────────────────────────
    // 场景四：多线程压缩确定性（上游无线程测试）
    // ─────────────────────────────────────────────────────────────────────
    {
        const std::vector<char> pts = makePoints(200);
        auto compressOnce = [&pts]() {
            lazperf::writer::chunk_compressor comp(0, 0);
            for (int i = 0; i < 200; ++i)
                comp.compress(pts.data() + static_cast<size_t>(i) * kPointSize);
            return comp.done();
        };

        const std::vector<unsigned char> baseline = compressOnce();
        check(!baseline.empty(), "场景四：单线程基线 chunk 非空");

        std::vector<std::vector<unsigned char>> results(4);
        std::atomic<int> mismatches{0};
        std::vector<std::thread> threads;
        for (int t = 0; t < 4; ++t)
        {
            threads.emplace_back([&, t]() {
                std::vector<unsigned char> r = compressOnce();
                if (r != baseline)
                    ++mismatches;
                results[t] = std::move(r);
            });
        }
        for (std::thread& th : threads)
            th.join();

        checkEq(mismatches.load(), 0,
                "场景四：4 线程并发压缩结果与单线程基线逐字节一致");
        checkEq(static_cast<int>(std::thread::hardware_concurrency() >= 1), 1,
                "场景四：hardware_concurrency() 可用");
    }

    // ─────────────────────────────────────────────────────────────────────
    // 场景五：HMDFS 目录语义 —— 写盘-关闭-立即重开字节一致
    // ─────────────────────────────────────────────────────────────────────
    {
        const std::string p = scratch + "/lazperf-hmdfs-latch.laz";
        {
            lazperf::writer::named_file::config c({0.01, 0.01, 0.01}, {0.0, 0.0, 0.0});
            c.pdrf = 0;
            lazperf::writer::named_file out(p, c);
            out.writePoint(points.data());
            out.writePoint(points.data() + kPointSize);
            out.close();
        }
        const std::string first = readAll(p);
        const std::string second = readAll(p);
        checkEq(first.size() == second.size(), true,
                "场景五：关闭后连续两次读取长度稳定（无延迟可见性）");
        checkEq(std::memcmp(first.data(), second.data(), first.size()), 0,
                "场景五：关闭后连续两次读取字节一致");
        checkEq(fileSize(p), static_cast<uint64_t>(first.size()),
                "场景五：stat 大小与读取长度一致");

        lazperf::reader::named_file in(p);
        char rec[kPointSize];
        in.readPoint(rec);
        checkEq(std::memcmp(rec, points.data(), kPointSize), 0,
                "场景五：重开后第一个点记录一致");
        in.readPoint(rec);
        checkEq(std::memcmp(rec, points.data() + kPointSize, kPointSize), 0,
                "场景五：重开后第二个点记录一致");
    }

    std::cout << "===== " << (gChecks - gFailures) << "/" << gChecks
              << " assertions passed =====" << std::endl;
    return gFailures == 0 ? 0 : 1;
}
