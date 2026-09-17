#include <botan/cipher_mode.h>
#include <botan/hex.h>
#include <botan/secmem.h>
#include <botan/symkey.h>

#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

// NIST GCM spec (McGrew/Viega, Appendix B) Test Case 14:
// AES-256, all-zero key/IV/plaintext -> known ciphertext and tag.
static const char* kKeyHex = "0000000000000000000000000000000000000000000000000000000000000000";
static const char* kIvHex = "000000000000000000000000";
static const char* kPtHex = "00000000000000000000000000000000";
static const char* kCtTagHex = "cea7403d4d606b6e074ec5d3baf39d18d0d1c8a799996bf0265b98b5d48ab919";

int main()
{
    // OctetString (SymmetricKey) parses hex directly; the nonce is passed
    // as a vector like upstream's own AEAD tests do.
    const Botan::SymmetricKey key(kKeyHex);
    const std::vector<uint8_t> nonce = Botan::hex_decode(kIvHex);
    const Botan::secure_vector<uint8_t> plaintext = Botan::hex_decode_locked(kPtHex);
    const std::string expected_ct_tag = kCtTagHex;

    // Encrypt and assert the exact ciphertext||tag against the KAT vector.
    auto enc = Botan::Cipher_Mode::create("AES-256/GCM", Botan::Cipher_Dir::Encryption);
    if (!enc)
        return 1;
    enc->set_key(key);
    enc->start(nonce);
    Botan::secure_vector<uint8_t> buf(plaintext);
    enc->finish(buf);
    if (Botan::hex_encode(buf, false) != expected_ct_tag)
        return 2;

    // Decrypt the KAT ciphertext and assert the plaintext round-trip
    // (finish() also authenticates the GCM tag and throws on mismatch).
    auto dec = Botan::Cipher_Mode::create("AES-256/GCM", Botan::Cipher_Dir::Decryption);
    if (!dec)
        return 3;
    dec->set_key(key);
    dec->start(nonce);
    Botan::secure_vector<uint8_t> ct = Botan::hex_decode_locked(kCtTagHex);
    dec->finish(ct);
    if (Botan::hex_encode(ct, false) != kPtHex)
        return 4;

    // Tampered tag must be rejected (auth failure throws).
    Botan::secure_vector<uint8_t> bad = Botan::hex_decode_locked(kCtTagHex);
    bad.back() ^= 0x01;
    dec->start(nonce);
    bool threw = false;
    try
    {
        dec->finish(bad);
    }
    catch (const std::exception&)
    {
        threw = true;
    }
    if (!threw)
        return 5;

    return 0;
}
