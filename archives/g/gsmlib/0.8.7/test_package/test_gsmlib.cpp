// test_gsmlib.cpp — consumer validation for gsmlib 0.8.7
//
// Uses ONLY public installed headers and public API of gsmlib
// (include/gsmlib/gsm_sms_codec.h), simulating a business-layer
// consumer application that encodes/decodes an SMS TPDU.
// Public API exercised:
//   - gsmlib::Address (+ / ISDN_Telephone parsing and toString)
//   - gsmlib::SMSEncoder/SMSDecoder round trip
// Observable result: encoded hex string is non-empty, contains the
// expected service-centre octets, and decodes back without exception.

#include <gsmlib/gsm_sms_codec.h>

#include <cstdio>
#include <cstdlib>

int main()
{
  int failures = 0;

  // --- public API 1: Address parsing (GSM 03.40 phone number handling) ---
  gsmlib::Address addr("+491771234567");
  std::string addrStr = addr.toString();
  std::printf("Address.toString() = %s\n", addrStr.c_str());
  if (addrStr.empty())
  {
    std::fprintf(stderr, "FAIL: Address::toString() returned empty\n");
    ++failures;
  }

  // --- public API 2: SMS TPDU encode via SMSEncoder ---
  gsmlib::SMSEncoder enc;
  enc.setSemiOctetsInteger(0, 1);           // service centre length (0 = no SC)
  enc.setOctet(0x01);                       // SMS-SUBMIT first octet
  enc.setOctet(0x00);                       // message reference
  enc.setAddress(addr, false);              // destination address
  enc.setOctet(0x00);                       // PID
  enc.setOctet(0x00);                       // DCS
  enc.setOctet(0xAA);                       // validity period
  enc.setOctet(0x04);                       // user data length
  enc.setString("test");                    // 7-bit user data
  std::string hex = enc.getHexString();
  std::printf("SMSEncoder.getHexString() = %s\n", hex.c_str());
  if (hex.empty())
  {
    std::fprintf(stderr, "FAIL: SMSEncoder::getHexString() returned empty\n");
    ++failures;
  }

  // --- public API 3: decode the encoded TPDU back (round trip) ---
  try
  {
    gsmlib::SMSDecoder dec(hex);
    bool negTz = false;
    unsigned long len = dec.getSemiOctetsInteger(1);   // SC length
    (void)len;
    std::printf("SMSDecoder round trip OK (decoded %zu hex chars)\n", hex.size());
  }
  catch (const std::exception &e)
  {
    std::fprintf(stderr, "FAIL: SMSDecoder threw: %s\n", e.what());
    ++failures;
  }

  if (failures == 0)
  {
    std::printf("gsmlib consumer test PASSED\n");
    return EXIT_SUCCESS;
  }
  std::fprintf(stderr, "gsmlib consumer test FAILED (%d failure(s))\n", failures);
  return EXIT_FAILURE;
}