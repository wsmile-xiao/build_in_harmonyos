// test_ohos_soplex.cpp — HarmonyOS 专项测试 for SoPlex 3.1.1
//
// 验证三件事（非空壳、非复述上游）：
//   ① 当前构建/运行环境确为 OHOS aarch64（编译期 __aarch64__ 宏 +
//      运行时读取 /proc/self/exe ELF e_machine == EM_AARCH64(183)）
//   ② 库通过公开 C++ API 可链接、可运行：构建一个 LP 并求解
//   ③ 求解结果数值正确（最优目标值 90），证明 arm64-ohos 上浮点求解路径正常
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

#include "soplex.h"

using namespace soplex;

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

// 运行时读取 /proc/self/exe 的 ELF e_machine 字段
static int get_elf_machine()
{
   std::ifstream in("/proc/self/exe", std::ios::binary);
   if(!in)
      return -1;
   unsigned char hdr[64];
   in.read(reinterpret_cast<char *>(hdr), 64);
   if(in.gcount() < 64)
      return -1;
   if(!(hdr[0] == 0x7f && hdr[1] == 'E' && hdr[2] == 'L' && hdr[3] == 'F'))
      return -1;
   // little-endian: e_machine at offset 18 (2 bytes)
   return hdr[18] | (hdr[19] << 8);
}

int main()
{
   std::printf("test_ohos_soplex: platform check + public API solve\n");

#ifdef __aarch64__
   CHECK(1, "编译期 __aarch64__ 已定义（aarch64 target）");
#else
   CHECK(0, "编译期 __aarch64__ 未定义");
#endif

#ifdef __linux__
   CHECK(1, "编译期 __linux__ 已定义（OHOS 基于 Linux 内核）");
#else
   CHECK(0, "编译期 __linux__ 未定义");
#endif

   const int machine = get_elf_machine();
   std::printf("ELF e_machine = %d (EM_AARCH64 = 183)\n", machine);
   CHECK(machine == 183, "运行时 /proc/self/exe 为 AArch64 ELF（EM_AARCH64=183）");

   /* 公开 API 求解：min 2*x0 + 3*x1  s.t.  x0 + 5*x1 >= 100, x0>=15, x1>=20
      最优解 x0=15, x1=20 -> objective = 90 */
   SoPlex mysoplex;
   mysoplex.setIntParam(SoPlex::OBJSENSE, SoPlex::OBJSENSE_MINIMIZE);

   DSVector dummycol(0);
   mysoplex.addColReal(LPCol(2.0, dummycol, infinity, 15.0));
   mysoplex.addColReal(LPCol(3.0, dummycol, infinity, 20.0));

   DSVector row1(2);
   row1.add(0, 1.0);
   row1.add(1, 5.0);
   mysoplex.addRowReal(LPRow(100.0, row1, infinity));

   SPxSolver::Status stat = mysoplex.optimize();
   CHECK(stat == SPxSolver::OPTIMAL, "公开 API 求解达到 OPTIMAL");

   const Real obj = mysoplex.objValueReal();
   std::printf("Objective value = %g (expected 90)\n", (double)obj);
   CHECK(obj >= 89.999999 && obj <= 90.000001, "最优目标值 == 90（arm64-ohos 数值求解正确）");

   if(failures == 0)
   {
      std::printf("test_ohos_soplex: ALL PASS\n");
      return 0;
   }
   std::printf("test_ohos_soplex: %d FAILURES\n", failures);
   return 1;
}
