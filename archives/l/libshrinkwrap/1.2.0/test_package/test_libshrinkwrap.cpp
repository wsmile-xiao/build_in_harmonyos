// Consumer test for packaged libshrinkwrap 1.2.0 (R34: 真实 include + 真实调用).
//
// 覆盖 stdio / gz / xz / zstd / bgzf 五类 streambuf 与 generic istream
// 格式探测；seek 断言只做上游语义内确定性的部分：
//   - xz::ibuf 支持基于 lzma index 的任意 seekpos（上游 xz-seek 同语义）
//   - zstd::ibuf 的 seekpos 是压缩块边界语义且受解压缓冲影响，
//     只断言 seekg(0) 后全量重读一致
//   - bgzf::ibuf 的 tellg/seekg 虚拟偏移与缓冲无关，可做精确断言
// scratch 文件按 E002 家族教训经 $TMPDIR/$TMP/$TEMP/$HOME 解析，退回 cwd，
// 不写死 /var/tmp 或 /tmp。
#include "shrinkwrap/istream.hpp"

#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <vector>

namespace sw = shrinkwrap;

namespace {

int g_checks = 0;

void check(bool ok, const std::string& what)
{
  ++g_checks;
  if (!ok)
  {
    std::cerr << "[fail] (" << g_checks << ") " << what << std::endl;
    std::exit(1);
  }
}

// OHOS 的 / 与 /var/tmp 可能只读或不存在（E002 家族）：
// $TMPDIR -> $TMP -> $TEMP -> $HOME -> 当前目录。
const std::string& scratch_dir()
{
  static const std::string dir = []() -> std::string {
    const char* vars[] = {"TMPDIR", "TMP", "TEMP", "HOME"};
    for (const char* v : vars)
    {
      const char* p = std::getenv(v);
      if (p && p[0])
      {
        struct stat st;
        if (stat(p, &st) == 0 && S_ISDIR(st.st_mode))
          return p;
      }
    }
    return ".";
  }();
  return dir;
}

std::string scratch(const char* name)
{
  return scratch_dir() + "/" + name;
}

// 确定性载荷："000 001 ... 511 "，512 个 4 字节 token 共 2048 字节。
const std::string& payload()
{
  static const std::string data = []() -> std::string {
    std::ostringstream os;
    for (int i = 0; i < 512; ++i)
    {
      char buf[8];
      std::snprintf(buf, sizeof(buf), "%03d ", i);
      os << buf;
    }
    return os.str();
  }();
  return data;
}

// 写入（析构落盘）后用 istreambuf_iterator 全量读回比对。
template <typename OutT, typename InT>
bool roundtrip(const std::string& path)
{
  {
    OutT os(path);
    os << payload();
  }
  InT is(path);
  std::string out((std::istreambuf_iterator<char>(is.rdbuf())),
                  std::istreambuf_iterator<char>());
  return out == payload();
}

// 关闭后重新打开再读（落盘持久性 / HMDFS 写-关-重开语义）。
template <typename InT>
bool reopen_equals(const std::string& path)
{
  InT is(path);
  std::string out((std::istreambuf_iterator<char>(is.rdbuf())),
                  std::istreambuf_iterator<char>());
  return out == payload();
}

// 定位第 idx 个 token 的字节偏移。
std::streamoff token_offset(std::size_t idx)
{
  return static_cast<std::streamoff>(idx * 4);
}

} // namespace

int main()
{
  const std::string& data = payload();
  check(data.size() == 2048, "payload is 2048 bytes");

  // ---- stdio（无压缩基线）----
  const std::string p_stdio = scratch("sw_test_stdio.txt");
  check((roundtrip<sw::stdio::ostream, sw::stdio::istream>(p_stdio)), "stdio roundtrip");
  {
    sw::stdio::istream is(p_stdio);
    int v = -1;
    is >> v;
    check(v == 0, "stdio token 0");
    is.clear();
    is.seekg(token_offset(2), std::ios::beg);
    is >> v;
    check(v == 2, "stdio seekg(8) token 2");
  }
  check(reopen_equals<sw::stdio::istream>(p_stdio), "stdio reopen");

  // ---- gzip（上游无 gz-seek 用例，不做 seek 断言）----
  const std::string p_gz = scratch("sw_test.gz");
  check((roundtrip<sw::gz::ostream, sw::gz::istream>(p_gz)), "gz roundtrip");
  check(reopen_equals<sw::gz::istream>(p_gz), "gz reopen");

  // ---- xz（lzma index 支持任意 seekpos）----
  const std::string p_xz = scratch("sw_test.xz");
  check((roundtrip<sw::xz::ostream, sw::xz::istream>(p_xz)), "xz roundtrip");
  check(reopen_equals<sw::xz::istream>(p_xz), "xz reopen");
  {
    sw::xz::istream is(p_xz);
    int v = -1;
    is.seekg(token_offset(2), std::ios::beg);
    is >> v;
    check(v == 2, "xz seekg(8) token 2");
    is.clear();
    is.seekg(-4, std::ios::end);
    is >> v;
    check(v == 511, "xz seekg(-4, end) token 511");
  }

  // ---- zstd（seekpos 为压缩块边界语义：只做 seekg(0) 全量重读）----
  const std::string p_zstd = scratch("sw_test.zst");
  check((roundtrip<sw::zstd::ostream, sw::zstd::istream>(p_zstd)), "zstd roundtrip");
  check(reopen_equals<sw::zstd::istream>(p_zstd), "zstd reopen");
  {
    sw::zstd::istream is(p_zstd);
    std::string first64(64, '\0');
    is.read(&first64[0], 64);
    check(is.gcount() == 64 && first64 == data.substr(0, 64), "zstd first 64 bytes");
    is.clear();
    // zstd::ibuf 的 seekoff 只支持 (0, cur)（tellg）；绝对定位必须走
    // seekg(pos) → seekpos（压缩块边界语义，上游 block_seek 同款用法）。
    is.seekg(0);
    std::string out((std::istreambuf_iterator<char>(is.rdbuf())),
                    std::istreambuf_iterator<char>());
    check(out == data, "zstd seekg(0) full re-read");
  }

  // ---- BGZF：多块（每 100 个 token flush 一次）+ 虚拟偏移 ----
  const std::string p_bgzf = scratch("sw_test.bgzf");
  {
    sw::bgzf::ostream os(p_bgzf);
    for (int i = 0; i < 512; ++i)
    {
      char buf[8];
      std::snprintf(buf, sizeof(buf), "%03d ", i);
      os << buf;
      if ((i % 100) == 99)
        os.flush(); // flush() 产生 BGZF 块边界
    }
  }
  check(reopen_equals<sw::bgzf::istream>(p_bgzf), "bgzf roundtrip");
  {
    sw::bgzf::istream is(p_bgzf);
    char tok[5] = {0};
    unsigned long long vo250 = 0;
    for (int i = 0; i < 512; ++i)
    {
      if (i == 250)
        vo250 = static_cast<unsigned long long>(is.tellg());
      is.read(tok, 4);
      if (is.gcount() != 4)
        break;
    }
    check(is.gcount() == 4, "bgzf full token walk");
    check((vo250 >> 16) != 0, "bgzf virtual offset has nonzero compressed part");
    is.clear();
    is.seekg(static_cast<std::streamoff>(vo250));
    is.read(tok, 4);
    tok[4] = '\0';
    check(std::string(tok) == "250 ", "bgzf seekg(virtual offset) token 250");
  }

  // ---- generic istream：魔数自动探测 ----
  check((reopen_equals<sw::istream>(p_gz)), "generic istream detects gz");
  check((reopen_equals<sw::istream>(p_xz)), "generic istream detects xz");
  check((reopen_equals<sw::istream>(p_zstd)), "generic istream detects zstd");
  check((reopen_equals<sw::istream>(p_bgzf)), "generic istream detects bgzf");

  // ---- 清理 scratch ----
  std::remove(p_stdio.c_str());
  std::remove(p_gz.c_str());
  std::remove(p_xz.c_str());
  std::remove(p_zstd.c_str());
  std::remove(p_bgzf.c_str());

  std::cout << "libshrinkwrap consumer test: " << g_checks << "/" << g_checks
            << " checks passed" << std::endl;
  return 0;
}
