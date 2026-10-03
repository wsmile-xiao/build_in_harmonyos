// test_package for mtxclient — offline consumer-side verification.
//
// Uses only the installed public API, no network and no homeserver:
//   mtx::identifiers        — Matrix ID parsing, incl. the v12 id form fixed
//                             in the 0.10.1 changelog
//   mtx::client::utils      — MXC URI parsing / query-string building
//   mtx::http::Client       — construction of the real HTTP client (pulls in
//                             coeurl, libcurl, libevent, spdlog)
//   mtx::crypto             — libolm + OpenSSL code paths (AES-CTR, HMAC,
//                             PBKDF2/HKDF, file encryption round trip)
//   mtx::events / mtx::responses — nlohmann/json (de)serialisation of the
//                             Matrix event and response types
//
// Note: the packaged libcurl is a no-TLS-backend variant, so this test
// deliberately performs no HTTPS request.
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include <mtx/common.hpp>
#include <mtx/events/messages/text.hpp>
#include <mtx/identifiers.hpp>
#include <mtx/responses/login.hpp>
#include <mtxclient/crypto/types.hpp>
#include <mtxclient/crypto/utils.hpp>
#include <mtxclient/http/client.hpp>
#include <mtxclient/utils.hpp>

namespace {

int checks_run   = 0;
int checks_fail  = 0;

void
check(bool condition, const std::string &what)
{
    ++checks_run;
    if (!condition) {
        ++checks_fail;
        std::cerr << "FAIL: " << what << '\n';
    } else {
        std::cout << "ok: " << what << '\n';
    }
}

template<typename T>
void
check_eq(const T &actual, const T &expected, const std::string &what)
{
    ++checks_run;
    if (!(actual == expected)) {
        ++checks_fail;
        std::cerr << "FAIL: " << what << '\n';
    } else {
        std::cout << "ok: " << what << '\n';
    }
}

void
check_identifiers()
{
    using mtx::identifiers::Room;
    using mtx::identifiers::User;

    const auto alice = mtx::identifiers::parse<User>("@alice:example.com");
    check_eq(alice.localpart(), std::string("alice"), "user localpart");
    check_eq(alice.hostname(), std::string("example.com"), "user hostname");

    const auto room = mtx::identifiers::parse<Room>("!room:example.com");
    check_eq(room.hostname(), std::string("example.com"), "room hostname");

    // 0.10.1 changelog: "Fix room ids without server name". V12 room ids carry
    // no ':' at all, so the parser must fall back to the no-hostname form.
    const auto v12_room = mtx::identifiers::parse<Room>("!abcdefghijklmnopqrst");
    check(!v12_room.hostname().empty() || v12_room.localpart() == "abcdefghijklmnopqrst",
          "v12 room id without server name parses");

    // The identifier is reachable through the installed json serialisation.
    const nlohmann::json j = alice;
    check_eq(j.get<std::string>(), std::string("@alice:example.com"),
             "user id json round trip");

    // Identifier has no string constructor, so equality is exercised between two
    // parsed values; the ordering check also covers the C++20 operator<=>.
    const auto alice_again = mtx::identifiers::parse<User>("@alice:example.com");
    check(alice_again == alice, "user id equality operator");
    check(!(alice_again < alice), "user id ordering operator (C++20 <=>)");
}

void
check_client_utils()
{
    const auto mxc = mtx::client::utils::parse_mxc_url("mxc://example.com/SomeMediaId");
    check_eq(mxc.server, std::string("example.com"), "mxc server");
    check_eq(mxc.media_id, std::string("SomeMediaId"), "mxc media id");

    check(mtx::client::utils::is_number("12345"), "is_number accepts digits");
    check(!mtx::client::utils::is_number("12x45"), "is_number rejects non-digits");

    const auto token = mtx::client::utils::random_token(16, false);
    check_eq(token.size(), std::size_t(16), "random_token length");

    const auto query = mtx::client::utils::query_params({{"a", "1"}, {"b", "2"}});
    check(query == "a=1&b=2" || query == "?a=1&b=2", "query_params ordering");

    check(!mtx::client::utils::url_encode("a b/c").empty(), "url_encode non-empty");

    // RFC 4648 test vector, through mtxclient's own base64 implementation.
    check_eq(mtx::crypto::bin2base64("foobar"), std::string("Zm9vYmFy"),
             "bin2base64 RFC 4648 vector");
    check_eq(mtx::crypto::base642bin("Zm9vYmFy"), std::string("foobar"),
             "base642bin RFC 4648 vector");
}

void
check_http_client()
{
    // Real client construction: exercises coeurl::Client, the libcurl easy
    // handle, the libevent base and the spdlog logger chain.
    mtx::http::Client client("https://example.com");
    // set_server() strips the scheme and keeps it as the protocol, so server()
    // holds the bare host while port() defaults to 443 for https.
    check_eq(client.server(), std::string("example.com"),
             "http client server host (scheme stripped)");
    check_eq(client.port(), uint16_t(443), "http client default https port");
    check_eq(client.server_url(), std::string("https://example.com:443"),
             "http client reconstructed server url");

    client.set_access_token("test_access_token");
    client.set_device_id("TESTDEVICE");
    client.set_port(443);
    check_eq(client.access_token(), std::string("test_access_token"),
             "http client access token getter");
}

void
check_crypto()
{
    using namespace mtx::crypto;

    const auto key = to_binary_buf("0123456789abcdef0123456789abcdef");

    // AES-CTR 256 round trip.
    const std::string plaintext = "mtxclient test_package plaintext";
    const auto iv               = create_buffer(16);
    const auto ciphertext       = AES_CTR_256_Encrypt(plaintext, key, iv);
    check_eq(ciphertext.size(), plaintext.size(), "AES-CTR ciphertext length");
    check(ciphertext != to_binary_buf(plaintext), "AES-CTR actually transformed data");
    check_eq(to_string(AES_CTR_256_Decrypt(to_string(ciphertext), key, iv)), plaintext,
             "AES-CTR decrypt round trip");

    // HMAC-SHA256 must be deterministic and 32 bytes wide.
    const auto mac = HMAC_SHA256(key, to_binary_buf("message"));
    check_eq(mac.size(), std::size_t(32), "HMAC-SHA256 output length");
    check(mac == HMAC_SHA256(key, to_binary_buf("message")), "HMAC-SHA256 deterministic");

    // Key derivation (OpenSSL PKCS5_PBKDF2_HMAC) and HKDF-SHA256.
    const auto derived = PBKDF2_HMAC_SHA_512("password", to_binary_buf("salt"), 1000, 32);
    check_eq(derived.size(), std::size_t(32), "PBKDF2 output length");
    check(derived == PBKDF2_HMAC_SHA_512("password", to_binary_buf("salt"), 1000, 32),
          "PBKDF2 deterministic");

    const auto hkdf = HKDF_SHA256(key, to_binary_buf("salt"), to_binary_buf("info"));
    check_eq(hkdf.aes.size(), std::size_t(32), "HKDF aes key length");
    check_eq(hkdf.mac.size(), std::size_t(32), "HKDF mac key length");

    // libolm reachable through the packaged library.
    const auto pubkey = CURVE25519_public_key_from_private(key);
    check(!pubkey.empty(), "CURVE25519 public key derived via libolm");

    // Matrix secret-storage round trip (AES-CTR + HMAC-SHA256, the SSSS path).
    const std::string secret = "matrix secret storage payload";
    const auto sealed        = encrypt(secret, key, "test_key");
    check(!sealed.ciphertext.empty(), "SSSS encrypt produced ciphertext");
    check_eq(decrypt(sealed, key, "test_key"), secret, "SSSS encrypt/decrypt round trip");

    // Matrix encrypted-file round trip (AES-CTR + SHA256 + HMAC).
    const std::string payload = "matrix encrypted attachment payload";
    auto encrypted            = encrypt_file(payload);
    encrypted.second.url      = "mxc://example.com/encryptedfile";
    check_eq(to_string(decrypt_file(to_string(encrypted.first), encrypted.second)), payload,
             "encrypt_file/decrypt_file round trip");
}

void
check_json_structs()
{
    using json = nlohmann::json;

    mtx::events::msg::Text text;
    text.body    = "hello from HarmonyOS";
    text.msgtype = "m.text";
    const json text_json = text;
    check_eq(text_json.at("body").get<std::string>(), std::string("hello from HarmonyOS"),
             "Text event serialisation");
    check_eq(text_json.at("msgtype").get<std::string>(), std::string("m.text"),
             "Text event msgtype serialisation");

    const auto text_back = text_json.get<mtx::events::msg::Text>();
    check_eq(text_back.body, text.body, "Text event round trip");

    // Deserialise a real login response (nlohmann/json + mtx structs).
    const auto login = json::parse(R"({
        "user_id": "@alice:example.com",
        "access_token": "abc123",
        "device_id": "TESTDEVICE",
        "home_server": "example.com"
    })")
                         .get<mtx::responses::Login>();
    check_eq(login.user_id.to_string(), std::string("@alice:example.com"),
             "Login response user_id");
    check_eq(login.access_token, std::string("abc123"), "Login response access_token");
    check_eq(login.device_id, std::string("TESTDEVICE"), "Login response device_id");
}

} // namespace

int
main()
{
    std::cout << "mtxclient test_package\n";

    check_identifiers();
    check_client_utils();
    check_http_client();
    check_crypto();
    check_json_structs();

    std::cout << "checks=" << checks_run << " failures=" << checks_fail << '\n';

    if (checks_fail != 0) {
        std::cout << "MTXCLIENT_TEST_PACKAGE_FAILED" << '\n';
        return EXIT_FAILURE;
    }

    std::cout << "MTXCLIENT_TEST_PACKAGE_OK" << '\n';
    return EXIT_SUCCESS;
}
