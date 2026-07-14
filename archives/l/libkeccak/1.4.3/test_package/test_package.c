/*
 * test_package.c — libkeccak API test (R34: 实质调用被测包 API)
 *
 * 1. SHA3-256("")    与 NIST 标准向量比对
 * 2. SHA3-256("abc") 与 NIST 标准向量比对
 * 3. HMAC-SHA3-256 初始化 + 摘要，验证结果不同于裸 SHA3-256
 */
#include <libkeccak.h>

#include <stdio.h>
#include <string.h>

#define SHA3_256_EMPTY "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a"
#define SHA3_256_ABC   "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532"

static int
sha3_256(const char *msg, char *hex_out)
{
	struct libkeccak_spec spec;
	struct libkeccak_state state;
	char hashsum[32];

	libkeccak_spec_sha3(&spec, 256);
	if (libkeccak_spec_check(&spec))
		return -1;
	if (libkeccak_state_initialise(&state, &spec))
		return -1;
	if (libkeccak_update(&state, msg, strlen(msg))) {
		libkeccak_state_destroy(&state);
		return -1;
	}
	if (libkeccak_digest(&state, NULL, 0, 0, LIBKECCAK_SHA3_SUFFIX, hashsum)) {
		libkeccak_state_destroy(&state);
		return -1;
	}
	libkeccak_behex_lower(hex_out, hashsum, sizeof(hashsum));
	libkeccak_state_destroy(&state);
	return 0;
}

static int
hmac_sha3_256(const char *key, const char *msg, char *hex_out)
{
	struct libkeccak_spec spec;
	struct libkeccak_hmac_state state;
	char hashsum[32];

	/* libkeccak_hmac_set_key() reallocs state->key_opad — the state must be
	 * zeroed before initialisation, otherwise it reallocs a garbage pointer */
	memset(&state, 0, sizeof(state));

	libkeccak_spec_sha3(&spec, 256);
	if (libkeccak_hmac_initialise(&state, &spec, key, 8 * strlen(key)))
		return -1;
	if (libkeccak_hmac_digest(&state, msg, strlen(msg), 0,
	                          LIBKECCAK_SHA3_SUFFIX, hashsum)) {
		libkeccak_hmac_destroy(&state);
		return -1;
	}
	libkeccak_behex_lower(hex_out, hashsum, sizeof(hashsum));
	libkeccak_hmac_destroy(&state);
	return 0;
}

int
main(void)
{
	char hex_empty[65];
	char hex_abc[65];
	char hex_hmac[65];
	int failures = 0;

	if (sha3_256("", hex_empty)) {
		fprintf(stderr, "FAIL: SHA3-256(\"\") 计算失败\n");
		return 1;
	}
	if (strcmp(hex_empty, SHA3_256_EMPTY)) {
		fprintf(stderr, "FAIL: SHA3-256(\"\") = %s, expected %s\n",
		        hex_empty, SHA3_256_EMPTY);
		failures++;
	} else {
		printf("PASS: SHA3-256(\"\") = %s\n", hex_empty);
	}

	if (sha3_256("abc", hex_abc)) {
		fprintf(stderr, "FAIL: SHA3-256(\"abc\") 计算失败\n");
		return 1;
	}
	if (strcmp(hex_abc, SHA3_256_ABC)) {
		fprintf(stderr, "FAIL: SHA3-256(\"abc\") = %s, expected %s\n",
		        hex_abc, SHA3_256_ABC);
		failures++;
	} else {
		printf("PASS: SHA3-256(\"abc\") = %s\n", hex_abc);
	}

	if (hmac_sha3_256("key", "abc", hex_hmac)) {
		fprintf(stderr, "FAIL: HMAC-SHA3-256 计算失败\n");
		return 1;
	}
	if (!strcmp(hex_hmac, hex_abc)) {
		fprintf(stderr, "FAIL: HMAC-SHA3-256 与裸 SHA3-256 结果相同\n");
		failures++;
	} else {
		printf("PASS: HMAC-SHA3-256(key, \"abc\") = %s\n", hex_hmac);
	}

	if (failures) {
		fprintf(stderr, "\n%d test(s) FAILED\n", failures);
		return 1;
	}

	printf("\nAll libkeccak tests passed.\n");
	return 0;
}
