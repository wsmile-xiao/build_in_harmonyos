// test_libpar2.cpp — libpar2 0.4 消费者闭环测试
//
// 上游无测试套件，本文件是唯一验证手段，真实调用 libpar2 公开 API 完成
// PAR2 全流程闭环：
//   1. 生成数据文件 → Par2Creator 创建 PAR2 恢复集（eSuccess）
//   2. LibPar2 校验完好文件（eSuccess）
//   3. 损坏数据文件 → LibPar2 校验（eRepairPossible）
//   4. LibPar2 修复 → 文件恢复且内容与原始一致（eSuccess）
//
// 任一步失败返回非 0 退出码。
#include "libpar2.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace {

// 构造并解析命令行，返回解析结果
bool ParseCommandLine(CommandLine& cl, const std::vector<std::string>& args)
{
  std::vector<char*> argv;
  for (size_t i = 0; i < args.size(); ++i)
    argv.push_back(const_cast<char*>(args[i].c_str()));
  return cl.Parse(static_cast<int>(argv.size()), argv.data());
}

// 用 Par2Creator 创建恢复集
Result RunCreate(const std::vector<std::string>& args)
{
  CommandLine cl;
  if (!ParseCommandLine(cl, args))
    return eInvalidCommandLineArguments;
  Par2Creator* creator = new Par2Creator;
  Result result = creator->Process(cl);
  delete creator;
  return result;
}

// 用 LibPar2 校验（dorepair=false）或修复（dorepair=true）
Result RunLibPar2(const std::vector<std::string>& args, bool dorepair)
{
  CommandLine cl;
  if (!ParseCommandLine(cl, args))
    return eInvalidCommandLineArguments;
  LibPar2* libpar2 = new LibPar2(&cl);
  Result result = libpar2->PreProcess();
  if (result == eSuccess)
    result = libpar2->Process(dorepair);
  delete libpar2;
  return result;
}

bool WriteFile(const std::string& name, const std::vector<unsigned char>& data)
{
  std::ofstream out(name.c_str(), std::ios::binary | std::ios::trunc);
  if (!out)
    return false;
  out.write(reinterpret_cast<const char*>(data.data()), data.size());
  return out.good();
}

bool ReadFile(const std::string& name, std::vector<unsigned char>& data)
{
  std::ifstream in(name.c_str(), std::ios::binary);
  if (!in)
    return false;
  data.assign(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
  return in.good() || in.eof();
}

int g_failures = 0;

void Check(bool condition, const char* what)
{
  if (!condition)
  {
    std::fprintf(stderr, "FAIL: %s\n", what);
    ++g_failures;
  }
  else
  {
    std::printf("PASS: %s\n", what);
  }
}

} // namespace

int main()
{
  // 1. 生成 1 MiB 确定性伪随机数据文件
  const size_t kSize = 1 << 20;
  std::vector<unsigned char> original(kSize);
  unsigned seed = 0x12345678u;
  for (size_t i = 0; i < kSize; ++i)
  {
    seed = seed * 1103515245u + 12345u;
    original[i] = static_cast<unsigned char>((seed >> 16) & 0xff);
  }
  Check(WriteFile("testdata.bin", original), "write testdata.bin (1 MiB)");

  // 2. 创建 PAR2 恢复集：块 1 KiB、冗余 10%
  Result r = RunCreate({"par2", "c", "-q", "-s1024", "-r10", "testdata.bin"});
  Check(r == eSuccess, "Par2Creator create recovery set");

  // 3. 校验完好文件
  r = RunLibPar2({"par2", "v", "-q", "testdata.bin.par2"}, false);
  Check(r == eSuccess, "LibPar2 verify intact file");

  // 4. 损坏数据文件中部 512 字节
  std::vector<unsigned char> damaged = original;
  const size_t mid = kSize / 2;
  for (size_t i = 0; i < 512; ++i)
    damaged[mid + i] ^= 0x5a;
  Check(WriteFile("testdata.bin", damaged), "corrupt testdata.bin middle");

  // 5. 校验损坏文件：应报告可修复
  r = RunLibPar2({"par2", "v", "-q", "testdata.bin.par2"}, false);
  Check(r == eRepairPossible, "LibPar2 verify detects damage (eRepairPossible)");

  // 6. 修复文件
  r = RunLibPar2({"par2", "r", "-q", "testdata.bin.par2"}, true);
  Check(r == eSuccess, "LibPar2 repair file");

  // 7. 修复后内容与原始一致
  std::vector<unsigned char> repaired;
  Check(ReadFile("testdata.bin", repaired), "read repaired testdata.bin");
  Check(repaired.size() == original.size(), "repaired size matches");
  Check(repaired == original, "repaired content matches original");

  if (g_failures != 0)
  {
    std::fprintf(stderr, "libpar2 0.4: %d check(s) FAILED\n", g_failures);
    return 1;
  }

  std::printf("libpar2 0.4: all checks passed (create/verify/repair round-trip)\n");
  return 0;
}
