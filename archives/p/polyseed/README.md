# polyseed

Mnemonic seed library for Monero and other CryptoNote-based currencies
by tevador. https://github.com/tevador/polyseed

16-word mnemonic phrases (≈36% shorter than legacy 25-word seeds) with an
embedded wallet birthday, optional passphrase encryption, up to 3 custom
feature bits, and a Reed-Solomon single-word checksum over GF(2048).
Cryptographic primitives (randbytes, PBKDF2-HMAC-SHA256, memzero) and UTF-8
normalization are injected at runtime via `polyseed_inject()`, so the library
itself contains no cryptographic code and links no third-party dependencies.

Supported languages: English, Japanese, Korean, Spanish, French, Italian,
Czech, Portuguese, Chinese (Simplified), Chinese (Traditional).

License: LGPL-3.0-only.

## OpenHarmony adaptation notes

- Built as static (default) or shared library via Conan + CMake.
- Compiled with `-fsigned-char`: the upstream non-ASCII detection relies on
  signed `char`, which is inverted by the AArch64 ELF ABI default.
- Upstream suite `polyseed-tests` (51 cases) runs on every `conan create`.

See `1.0.0/notes.md` for details.
