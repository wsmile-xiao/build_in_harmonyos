/* OHOS 专项测试：通过公开 API 验证 hash-library 在 HarmonyOS PC (armv8, OHOS clang)
 * 平台上的完整功能与可观察结果（与上游 tests/ 三个用例、test_package 消费者用例
 * 分别计数，不重复充数）。
 *
 * 验证点：
 *   1. 各算法已知向量（SHA256/MD5/SHA1/CRC32/SHA3-256/Keccak-256，与上游断言一致）
 *   2. HMAC RFC2202/4231 已知向量
 *   3. 流式 add()/getHash() 分块 API（模拟大文件分块哈希）
 *   4. 大块数据（1MB 'a' 流）SHA256 已知向量（NIST 标准向量）
 *   5. 重复 getHash() 幂等（issue#2 回归语义，平台独立验证）
 */
#include <crc32.h>
#include <md5.h>
#include <sha1.h>
#include <sha256.h>
#include <sha3.h>
#include <keccak.h>
#include <hmac.h>

#include <string>
#include <vector>
#include <iostream>
#include <cstdio>

static int g_failures = 0;

static void expect(const std::string& what, const std::string& got,
                   const std::string& want)
{
  if (got != want)
  {
    std::cerr << "FAIL: " << what << " got=" << got << " want=" << want << std::endl;
    g_failures++;
  }
  else
  {
    std::cout << "PASS: " << what << " -> " << got.substr(0, 16) << "..." << std::endl;
  }
}

int main()
{
  std::cout << "=== OHOS hash-library 专项测试 (armv8, clang 15) ===" << std::endl;

  // 1. NIST/known-answer vectors
  const std::string abc = "abc";
  const std::string empty;
  expect("SHA256(abc)", SHA256()(abc),
         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  expect("SHA256(empty)", SHA256()(empty),
         "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
  expect("MD5(abc)", MD5()(abc), "900150983cd24fb0d6963f7d28e17f72");
  expect("SHA1(abc)", SHA1()(abc), "a9993e364706816aba3e25717850c26c9cd0d89d");
  expect("CRC32(abc)", CRC32()(abc), "352441c2");
  expect("SHA3-256(abc)", SHA3()(abc),
         "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532");
  expect("Keccak-256(abc)", Keccak()(abc),
         "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45");
  expect("SHA3-512(empty)", SHA3(SHA3::Bits512)(empty),
         "a69f73cca23a9ac5c8b567dc185a756e97c982164fe25859e0d1dcc1475c80a6"
         "15b2123af1f5f94c11e3e9402c3ac558f500199d95b6d3e301758586281dcd26");

  // 2. HMAC vectors (RFC 2202 #1, RFC 4231 #2)
  expect("HMAC-MD5 RFC2202#1",
         hmac<MD5>("Hi There", 8,
                   "\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b", 16),
         "9294727a3638bb1c13f48ef8158bfc9d");
  expect("HMAC-SHA256 RFC4231#2",
         hmac<SHA256>("what do ya want for nothing?", 28, "Jefe", 4),
         "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843");

  // 3. streaming chunk-wise API (readme example)
  SHA256 stream;
  const char* url = "create.stephan-brumme.com"; // 25 bytes
  for (int i = 0; i < 25; i += 5)
    stream.add(url + i, 5);
  expect("SHA256(streaming-chunks)", stream.getHash(),
         "82aa771f1183c52f973c798c9243a1c73833ea40961c73e55e12430ec77b69f6");

  // 4. 1MB 'a' NIST vector
  std::string million(1000000, 'a');
  expect("SHA256(1Mx'a')", SHA256()(million),
         "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0");
  expect("SHA1(1Mx'a')", SHA1()(million),
         "34aa973cd4c4daa4f61eeb2bdbad27316534016f");

  // 5. repeated getHash() idempotence (issue#2 semantics)
  MD5 md5;
  md5.add(abc.c_str(), abc.size());
  std::string h1 = md5.getHash();
  std::string h2 = md5.getHash();
  std::string h3 = md5.getHash();
  expect("MD5 getHash idempotent", (h1 == h2 && h2 == h3) ? h1 : "DIFF", h1);

  std::cout << (g_failures == 0
                ? "OHOS test: all checks passed"
                : "OHOS test: FAILURES=" + std::to_string(g_failures))
            << std::endl;
  return g_failures;
}
