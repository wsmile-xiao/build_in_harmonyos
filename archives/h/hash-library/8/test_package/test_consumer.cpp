// test_package consumer — validates hash-library's public C++ API works
// from an external consumer's perspective (installed headers + static lib).
// Real assertions: known-answer vectors for SHA256, MD5, SHA1, CRC32, SHA3,
// Keccak and HMAC (RFC 2202/4231) — not a print-only stub (R34).
#include <crc32.h>
#include <md5.h>
#include <sha1.h>
#include <sha256.h>
#include <sha3.h>
#include <keccak.h>
#include <hmac.h>

#include <string>
#include <iostream>

static int failures = 0;

static void expect_eq(const std::string& what,
                      const std::string& got, const std::string& want)
{
  if (got != want)
  {
    std::cerr << "FAIL " << what << ": got=" << got << " want=" << want << std::endl;
    failures++;
  }
}

int main()
{
  const std::string abc = "abc";

  expect_eq("SHA256(abc)", SHA256()(abc),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  expect_eq("MD5(abc)", MD5()(abc),
            "900150983cd24fb0d6963f7d28e17f72");
  expect_eq("SHA1(abc)", SHA1()(abc),
            "a9993e364706816aba3e25717850c26c9cd0d89d");
  expect_eq("CRC32(abc)", CRC32()(abc),
            "352441c2");
  expect_eq("SHA3-256(abc)", SHA3()(abc),
            "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532");
  expect_eq("Keccak-256(abc)", Keccak()(abc),
            "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45");
  expect_eq("HMAC-MD5(RFC2202#1)", hmac<MD5>("Hi There", 8, "\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b", 16),
            "9294727a3638bb1c13f48ef8158bfc9d");
  expect_eq("HMAC-SHA256(RFC4231#2)", hmac<SHA256>("what do ya want for nothing?", 28, "Jefe", 4),
            "5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843");

  // streaming API
  SHA256 stream;
  const char* url = "create.stephan-brumme.com"; // 25 bytes
  for (int i = 0; i < 25; i += 5)
    stream.add(url + i, 5);
  expect_eq("SHA256(streaming)", stream.getHash(),
            "82aa771f1183c52f973c798c9243a1c73833ea40961c73e55e12430ec77b69f6");

  if (failures == 0)
    std::cout << "test_hash-library: all consumers assertions passed" << std::endl;
  else
    std::cout << "test_hash-library: " << failures << " failures" << std::endl;
  return failures;
}
