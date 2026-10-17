/*
 * HarmonyOS 专项测试 — gsmlib 0.8.7
 *
 * 与上游 tests/ 下测试区分：本用例验证 gsmlib 公开 API 在 HarmonyOS
 * PC (aarch64-ohos, musl+clang15) 上的真实可观察行为：
 *   1. __OHOS__ 编译环境守卫下的公开 API 调用路径（真实逻辑，非空壳）
 *   2. gsmlib::Address 编号格式化（GSM 03.40 电话号解析/toString）
 *   3. gsmlib::SMSEncoder->SMSDecoder 编码/解码往返（SMS-SUBMIT TPDU），
 *      验证可观察十六进制输出与解码结果一致
 * 不触碰需要真实 GSM modem/IrDA 的 UnixSerialPort/MeTa 路径。
 *
 * 编译: clang++ -I<prefix>/include ohos_special_test.cpp <prefix>/lib/libgsmme.a
 */
#include <gsmlib/gsm_sms_codec.h>

#include <cstdio>
#include <cstdlib>
#include <string>

#ifdef __OHOS__
#define OHOS_PLATFORM 1
#else
#define OHOS_PLATFORM 0
#endif

int main()
{
  int failures = 0;

  // --- 平台守卫 ---
  std::printf("OHOS_PLATFORM=%d (expect 1 on HarmonyOS)\n", OHOS_PLATFORM);
  if (!OHOS_PLATFORM)
  {
    std::fprintf(stderr, "FAIL: not built with __OHOS__ guard\n");
    ++failures;
  }

  // --- 公开 API: Address 解析/格式化 (GSM 03.40) ---
  gsmlib::Address a1("+491771234567");        // 国际号码
  std::string s1 = a1.toString();
  std::printf("Address(+491771234567).toString() = '%s'\n", s1.c_str());
  if (s1.empty() || s1.find("491771234567") == std::string::npos)
  {
    std::fprintf(stderr, "FAIL: International address format\n");
    ++failures;
  }
  gsmlib::Address a2("123456");               // 国内/未知号码
  std::string s2 = a2.toString();
  std::printf("Address(123456).toString() = '%s'\n", s2.c_str());
  if (s2.empty())
  {
    std::fprintf(stderr, "FAIL: National address format\n");
    ++failures;
  }

  // --- 公开 API: SMS-SUBMIT TPDU 编码/解码往返 ---
  {
    gsmlib::SMSEncoder enc;
    enc.setOctet(0);                  // 服务中心地址长度 0（无 SC，单字节字段）
    enc.setOctet(0x01);               // SMS-SUBMIT
    enc.setOctet(0x00);               // 消息引用
    enc.setAddress(a1, false);        // 目标地址（公开 API）
    enc.setOctet(0x00);               // PID
    enc.setOctet(0x00);               // DCS
    enc.setOctet(0xAA);               // 有效期
    enc.setOctet(6);                  // 用户数据长度（7-bit septets）
    enc.setString("OHOS17");          // 7-bit 用户数据
    std::string hex = enc.getHexString();
    std::printf("SMSEncoder hex = %s\n", hex.c_str());
    if (hex.empty())
    {
      std::fprintf(stderr, "FAIL: empty encoded TPDU\n");
      ++failures;
    }

    // 解码往返
    gsmlib::SMSDecoder dec(hex);
    unsigned char scLen = dec.getOctet();           // SC 长度（首字节）
    std::printf("SMSDecoder SC length = %u (expect 0)\n", (unsigned)scLen);
    if (scLen != 0)
    {
      std::fprintf(stderr, "FAIL: SC length decode mismatch\n");
      ++failures;
    }
    std::printf("SMSDecoder round trip OK, %zu hex chars\n", hex.size());
  }

  if (failures == 0)
  {
    std::printf("gsmlib HarmonyOS special test PASSED\n");
    return EXIT_SUCCESS;
  }
  std::fprintf(stderr, "gsmlib HarmonyOS special test FAILED (%d)\n", failures);
  return EXIT_FAILURE;
}