/*
 * Consumer smoke test for ell 0.71 (Conan L1 test_package).
 *
 * It really calls into libell instead of only printing a string:
 *   - l_base64_encode() : encode a known vector and compare byte for byte
 *   - l_base64_decode() : decode it back and compare the round trip
 *   - l_strdup_printf() : ell-owned formatted string allocation
 *   - l_free()          : release every ell-owned allocation
 *
 * These are pure computation helpers chosen deliberately: they depend on
 * neither epoll, netlink, DBus nor AF_ALG, so the consumer test stays
 * runnable in the restricted sandbox this package is built in.
 */
#include <stdio.h>
#include <string.h>

#include <ell/ell.h>

static const char input[] = "ell-0.71";

/* base64("ell-0.71"), no line wrapping */
static const char *expected_b64 = "ZWxsLTAuNzE=";

int main(void)
{
	char *encoded;
	char *formatted;
	uint8_t *decoded;
	size_t decoded_len = 0;

	/* ---- base64 encode against a known vector ---- */
	encoded = l_base64_encode((const uint8_t *) input, strlen(input), 0);
	if (!encoded) {
		fprintf(stderr, "FAIL: l_base64_encode returned NULL\n");
		return 1;
	}
	if (strcmp(encoded, expected_b64) != 0) {
		fprintf(stderr, "FAIL: base64 mismatch\n  got: %s\n  exp: %s\n",
			encoded, expected_b64);
		l_free(encoded);
		return 1;
	}

	/* ---- base64 decode round trip ---- */
	decoded = l_base64_decode(encoded, strlen(encoded), &decoded_len);
	l_free(encoded);
	if (!decoded) {
		fprintf(stderr, "FAIL: l_base64_decode returned NULL\n");
		return 1;
	}
	if (decoded_len != strlen(input) ||
			memcmp(decoded, input, decoded_len) != 0) {
		fprintf(stderr, "FAIL: base64 round-trip mismatch (len=%zu)\n",
			decoded_len);
		l_free(decoded);
		return 1;
	}
	l_free(decoded);

	/* ---- ell-owned formatted string ---- */
	formatted = l_strdup_printf("%s-%d", "ell", 71);
	if (!formatted) {
		fprintf(stderr, "FAIL: l_strdup_printf returned NULL\n");
		return 1;
	}
	if (strcmp(formatted, "ell-71") != 0) {
		fprintf(stderr, "FAIL: l_strdup_printf got '%s'\n", formatted);
		l_free(formatted);
		return 1;
	}
	l_free(formatted);

	printf("ell 0.71 consumer smoke: base64 encode/decode + string OK\n");
	return 0;
}
