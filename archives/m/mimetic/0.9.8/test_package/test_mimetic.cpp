// Consumer test for mimetic 0.9.8 on OpenHarmony PC (aarch64).
//
// Exercises the public API shipped by the Conan package: library version,
// base64/QP codecs (including the sign-sensitive decode table), programmatic
// MIME message construction, RFC822 serialization and re-parsing.
#include <mimetic/mimetic.h>

#include <cstdlib>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>

using namespace mimetic;

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const std::string& what)
{
    ++g_checks;
    if (ok)
    {
        std::cout << "ok: " << what << std::endl;
    }
    else
    {
        ++g_failures;
        std::cerr << "FAIL: " << what << std::endl;
    }
}

int main()
{
    // 1) library identity
    check(version == Version(0, 9, 8), "mimetic::version reports 0.9.8");

    // 2) base64 encode/decode round-trip (decode table is signed-char sensitive)
    const std::string plain("HarmonyOS PC aarch64 mimetic consumer");
    std::string encoded;
    {
        Base64::Encoder enc;
        encode(plain.begin(), plain.end(), enc, std::back_inserter(encoded));
    }
    check(encoded == "SGFybW9ueU9TIFBDIGFhcmNoNjQgbWltZXRpYyBjb25zdW1lcg==",
          "base64 encoding matches the known vector");
    std::string decoded;
    {
        Base64::Decoder dec;
        decode(encoded.begin(), encoded.end(), dec, std::back_inserter(decoded));
    }
    check(decoded == plain, "base64 decode returns the original payload");

    // 3) quoted-printable round-trip
    const std::string qp_src("line one\nline two = with equals\n");
    std::string qp_coded;
    {
        QP::Encoder qp;
        encode(qp_src.begin(), qp_src.end(), qp, std::back_inserter(qp_coded));
    }
    std::string qp_back;
    {
        QP::Decoder qp;
        decode(qp_coded.begin(), qp_coded.end(), qp, std::back_inserter(qp_back));
    }
    check(qp_back == qp_src, "quoted-printable round-trip returns the original payload");

    // 4) build a message, serialize it and parse it back
    MimeEntity built;
    built.header().from("dev@example.com");
    built.header().to("user@example.com");
    built.header().subject("mimetic on HarmonyOS");
    built.header().contentType(ContentType("text/plain"));
    built.body().assign("Hello from the mimetic test_package.\n");

    std::ostringstream out;
    out << built;
    const std::string serialized = out.str();
    check(serialized.find("Subject: mimetic on HarmonyOS") != std::string::npos,
          "serialized message carries the subject header");

    std::istringstream in(serialized);
    MimeEntity parsed(in);
    check(parsed.header().subject() == "mimetic on HarmonyOS",
          "re-parsed subject matches");
    check(parsed.header().from().str() == "dev@example.com", "re-parsed From matches");
    check(parsed.body().find("Hello from the mimetic test_package.") != std::string::npos,
          "re-parsed body matches");
    check(parsed.header().contentType().type() == "text",
          "re-parsed content type is textual");

    std::cout << "checks=" << g_checks << " failures=" << g_failures << std::endl;
    return g_failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
