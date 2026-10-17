/* blake2b.h - minimal portable BLAKE2b (RFC 7693) vendored for libequihash.
 *
 * CC0 1.0 Universal (same license as libequihash itself).
 *
 * Only the one-shot API needed by equihash.cc is exposed. The implementation
 * in blake2b.c follows RFC 7693 section 3 (IV, sigma schedule, G, compress,
 * parameter block, buffering, padding, last-block flag) and matches the
 * official test vectors, e.g. blake2b-256("") =
 *   0e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a8
 */

#ifndef EQUIHASH_BLAKE2B_H
#define EQUIHASH_BLAKE2B_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* One-shot BLAKE2b: hash in[0..inlen) (plus optional key) into out[0..outlen).
 * outlen must be 1..64, keylen 0..64. Returns 0 on success, -1 on bad params.
 * With key == NULL and keylen == 0 this is exactly what libsodium's
 * crypto_generichash(out, outlen, in, inlen, NULL, 0) computes, which is the
 * only sodium call equihash.cc makes.
 */
int equihash_blake2b(unsigned char *out, size_t outlen,
                     const unsigned char *in, size_t inlen,
                     const unsigned char *key, size_t keylen);

#ifdef __cplusplus
}
#endif

#endif /* EQUIHASH_BLAKE2B_H */
