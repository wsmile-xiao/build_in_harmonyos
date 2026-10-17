/* Consumer checks for the *installed* package, exercised through the headers and the
 * archive exactly as a downstream project sees them:
 *   - every public header must be includable from C++ (upstream wraps the C prototypes
 *     in extern "C" and adds std::string overloads outside it), via CMake + CMakeDeps;
 *   - the generic dispatch headers must agree with the primitive headers;
 *   - the in-tree cpucycles/randombytes objects that package() folds into libnacl.a must
 *     resolve for a consumer that only links -lnacl.
 *
 * Argument shapes follow upstream's own tests/ programs. Public Domain.
 */
#include <iostream>
#include <string>
#include <string.h>

#include "crypto_hash.h"
#include "crypto_hash_sha256.h"
#include "crypto_hash_sha512.h"
#include "crypto_secretbox.h"
#include "crypto_sign.h"
#include "crypto_box.h"
#include "crypto_onetimeauth.h"
#include "crypto_stream.h"
#include "crypto_verify_16.h"
#include "randombytes.h"
#include "cpucycles.h"

static int checks;
static int failures;

#define CHECK(cond)                                                  \
  do {                                                               \
    ++checks;                                                        \
    if (!(cond)) {                                                   \
      ++failures;                                                    \
      std::cout << "FAIL " << __LINE__ << ": " << #cond << std::endl; \
    }                                                                \
  } while (0)

int main()
{
  const std::string msg = "testing\n";

  /* C++ std::string wrapper from the generated header vs. the C entry point */
  std::string wrapped = crypto_hash(msg);
  CHECK(wrapped.size() == crypto_hash_BYTES);
  unsigned char plain[crypto_hash_BYTES];
  crypto_hash_sha512(plain,
                     reinterpret_cast<const unsigned char *>(msg.data()), msg.size());
  CHECK(memcmp(wrapped.data(), plain, crypto_hash_BYTES) == 0);

  /* the generic name and the selected primitive must be the same function */
  unsigned char a[crypto_hash_BYTES], b[crypto_hash_BYTES];
  crypto_hash(a, reinterpret_cast<const unsigned char *>(msg.data()), msg.size());
  crypto_hash_sha512(b, reinterpret_cast<const unsigned char *>(msg.data()), msg.size());
  CHECK(memcmp(a, b, crypto_hash_BYTES) == 0);
  crypto_hash_sha256(a, reinterpret_cast<const unsigned char *>(msg.data()), msg.size());
  crypto_hash_sha512(b, reinterpret_cast<const unsigned char *>(msg.data()), msg.size());
  CHECK(memcmp(a, b, 32) != 0);

  /* secretbox / box / sign / onetimeauth / stream / verify constants */
  CHECK(crypto_secretbox_KEYBYTES == 32);
  CHECK(crypto_secretbox_NONCEBYTES == 24);
  CHECK(crypto_box_BEFORENMBYTES == 32);
  CHECK(crypto_sign_BYTES == 64);
  CHECK(crypto_onetimeauth_BYTES == 16);
  unsigned char zerokey[32], zerononce[24];
  memset(zerokey, 0, sizeof zerokey);
  memset(zerononce, 0, sizeof zerononce);
  CHECK(crypto_stream_xor(a, reinterpret_cast<const unsigned char *>(msg.data()),
                          msg.size(), zerononce, zerokey) == 0);
  CHECK(memcmp(a, msg.data(), msg.size()) != 0);
  crypto_stream_xor(a, a, msg.size(), zerononce, zerokey);
  CHECK(memcmp(a, msg.data(), msg.size()) == 0);
  CHECK(crypto_verify_16(b, b) == 0);

  /* C++ one-shot API. The std::string wrappers add and strip the ZEROBYTES/BOXZEROBYTES
     padding themselves, so the message going in and the plaintext coming out are raw. */
  unsigned char key[32], nonce[24];
  randombytes(key, sizeof key);
  randombytes(nonce, sizeof nonce);
  const std::string k(reinterpret_cast<const char *>(key), sizeof key);
  const std::string n(reinterpret_cast<const char *>(nonce), sizeof nonce);
  std::string box = crypto_secretbox(msg, n, k);
  CHECK(box.size() == msg.size() + crypto_secretbox_ZEROBYTES - crypto_secretbox_BOXZEROBYTES);
  CHECK(box != msg);
  CHECK(crypto_secretbox_open(box, n, k) == msg);
  std::string tampered = box;
  tampered[box.size() - 1] = tampered[box.size() - 1] ^ 1;
  bool threw = false;
  try {
    crypto_secretbox_open(tampered, n, k);
  } catch (const char *) {
    threw = true;
  }
  CHECK(threw);
  threw = false;
  try {
    crypto_secretbox(msg, std::string(), k);
  } catch (const char *) {
    threw = true;
  }
  CHECK(threw); /* the wrapper validates nonce length instead of reading out of bounds */

  CHECK(strlen(cpucycles_implementation) > 0);
  CHECK(cpucycles_persecond() > 0);

  std::cout << "nacl c++ consumer checks=" << checks << " failures=" << failures << std::endl;
  return failures ? 1 : 0;
}
