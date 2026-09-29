/*
 * 鸿蒙专项测试：digestpp_ohos_test
 *
 * 目的：在 OHOS aarch64 工具链（clang 15 + libc++，os=OHOS profile）构建并运行的
 * HarmonyOS 专项用例，验证 digestpp 在 OHOS 平台真实可用：
 *   1. 仅通过已安装公共头文件 <digestpp/digestpp.hpp> 与公开 API
 *      （sha256 / sha3 / blake2b / shake256 / skein512）使用本库。
 *   2. 覆盖本适配修复的 LSH 算法（rotate_left 零旋转 UB 补丁）在 OHOS
 *      优化构建下的正确性（LSH256/LSH512 官方测试向量）。
 *   3. 该用例与 test_package 消费者测试互补：本用例聚焦哈希库在 OHOS
 *      工具链下的真实摘要正确性与 XOF 流式吸收/挤出行为。
 */
#include <digestpp/digestpp.hpp>
#include <cstdio>
#include <string>

namespace
{
   int failures = 0;

   void check(const char* name, const std::string& actual, const std::string& expected)
   {
      if (actual != expected)
      {
         std::printf("OHOS test FAIL: %s expected %s, actual %s\n", name,
                     expected.c_str(), actual.c_str());
         failures++;
      }
#if OHOS_TEST_VERBOSE
      else
      {
         std::printf("OHOS test OK: %s (%s)\n", name, actual.c_str());
      }
#endif
   }
}  // namespace

int main()
{
   // FIPS 180-2 SHA-256("abc")
   check("sha256(abc)",
         digestpp::sha256().absorb("abc").hexdigest(),
         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");

   // NIST SHA3-512("")
   check("sha3_512(empty)",
         digestpp::sha3(512).hexdigest(),
         "a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a6"
         "15b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26");

   // BLAKE2b-512("")
   check("blake2b512(empty)",
         digestpp::blake2b().hexdigest(),
         "786a02f742015903c6c6fd852552d272912f4740e15847618a86e217f71f5419"
         "d25e1031afee585313896444934eb04b903a685b1448b755d56f701afe9be2ce");

   // SHAKE256 XOF: batch squeeze == per-byte squeeze（流式行为）
   digestpp::shake256 x1, x2;
   const std::string ts = "The quick brown fox jumps over the lazy dog";
   x1.absorb(ts);
   x2.absorb(ts);
   std::string s1 = x1.hexsqueeze(64);
   std::string s2;
   for (int i = 0; i != 64; ++i)
      s2 += x2.hexsqueeze(1);
   check("shake256 batch==per-byte", s1, s2);

   // LSH256/256 官方测试向量（本适配补丁修复项，-O2 下必须正确）
   check("lsh256_256(quickfox)",
         digestpp::lsh256(256).absorb(ts).hexdigest(),
         "f8025b61eb10d80a7f03ccfb906222a0645bb175fdeee9595f223936edbf7070");

   // LSH512/256 官方测试向量（同补丁修复项）
   check("lsh512_256(quickfox)",
         digestpp::lsh512(256).absorb(ts).hexdigest(),
         "5e4ebe2017e84f35420bda7486ebbd791e0ece579cc18e49341b9a526466e633");

   // Skein512/512 官方测试向量（testvectors/skein512_512.txt：Msg= 空消息）
   check("skein512(empty)",
         digestpp::skein512(512).hexdigest(),
         "bc5b4c50925519c290cc634277ae3d6257212395cba733bbad37a4af0fa06af4"
         "1fca7903d06564fea7a2d3730dbdb80c1f85562dfcc070334ea4d1d9e72cba7a");

   if (failures == 0)
   {
      std::printf("OHOS test PASS: digestpp 7 checks (sha256/sha3/blake2b/shake256/lsh256/"
                  "lsh512/skein512) on OHOS aarch64\n");
      return 0;
   }
   std::printf("OHOS test FAILED with %d errors\n", failures);
   return 1;
}