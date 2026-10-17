/* HarmonyOS-specific consumer test for libfcrypto 0-20240414.
 *
 * Compiled and run only on OHOS targets (see test_package/conanfile.py).
 * Checks the platform integration facts a generic consumer cannot see:
 *   1. the test binary really targets __OHOS__;
 *   2. the packaged shared library loads and computes on OHOS (RC4 vector);
 *   3. a writable temporary directory is available (TMPDIR, /tmp fallback);
 *      on a host with a read-only /tmp and no TMPDIR the fact is reported as
 *      SKIP and not counted as a pass (device /tmp is read-only, E002);
 *   4. the temp-file create/write/read-back/unlink lifecycle works.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libfcrypto.h>

static int failures = 0;
static int checks = 0;
static int skipped = 0;

#define CHECK(desc, condition) \
	do { \
		checks++; \
		if (condition) { \
			printf("PASS: %s\n", desc); \
		} else { \
			printf("FAIL: %s\n", desc); \
			failures++; \
		} \
	} while (0)

#define SKIP(desc) \
	do { \
		printf("SKIP: %s\n", desc); \
		skipped++; \
	} while (0)

int main(void)
{
	const uint8_t rc4_key[] = "Secret";
	const uint8_t rc4_plaintext[] = "Attack at dawn";
	const uint8_t rc4_expected[] = {
		0x45, 0xA0, 0x1F, 0x64, 0x5F, 0xC3, 0x5B, 0x38, 0x35,
		0x52, 0x54, 0x4B, 0x9B, 0xF5
	};
	uint8_t rc4_ciphertext[ 14 ];

	libfcrypto_error_t *error = NULL;
	libfcrypto_rc4_context_t *context = NULL;

#if defined( __OHOS__ )
	printf("target: OHOS\n");
	CHECK("binary compiled for __OHOS__", 1);
#else
	printf("target: non-OHOS\n");
	CHECK("binary compiled for __OHOS__", 0);
#endif

	CHECK("packaged libfcrypto computes on OHOS (RC4 test vector)",
	      libfcrypto_rc4_context_initialize(
		      &context, &error ) == 1
	      && libfcrypto_rc4_context_set_key(
		      context, rc4_key, 48, &error ) == 1
	      && libfcrypto_rc4_crypt(
		      context,
		      rc4_plaintext, 14,
		      rc4_ciphertext, 14,
		      &error ) == 1
	      && memcmp(rc4_ciphertext, rc4_expected, 14) == 0);

	if (context != NULL) {
		libfcrypto_rc4_context_free(&context, &error);
	}

	/* Temporary directory probe: TMPDIR wins, a writable /tmp is the
	 * fallback, anything else is a platform boundary and reported as SKIP.
	 */
	const char *tmp_env = getenv("TMPDIR");
	const char *base_dir = NULL;

	if (tmp_env != NULL && tmp_env[ 0 ] != '\0') {
		base_dir = tmp_env;
	} else if (access("/tmp", W_OK) == 0) {
		base_dir = "/tmp";
	}

	if (base_dir == NULL) {
		SKIP("no writable TMPDIR and read-only /tmp (platform boundary)");
	} else {
		char path[ 512 ];
		FILE *handle = NULL;
		const char *payload = "libfcrypto-ohos-probe";
		size_t length = strlen(payload);
		uint8_t buffer[ 32 ];

		printf("temporary directory: %s\n", base_dir);
		snprintf(path, sizeof(path), "%s/libfcrypto_ohos_probe_%d.tmp",
		         base_dir, (int)getpid());

		handle = fopen(path, "wb");
		CHECK("temp file can be created in the temporary directory",
		      handle != NULL);

		if (handle != NULL) {
			CHECK("temp file accepts a write",
			      fwrite(payload, 1, length, handle) == length);
			fclose(handle);

			memset(buffer, 0, sizeof(buffer));

			handle = fopen(path, "rb");
			CHECK("temp file can be reopened for reading",
			      handle != NULL);

			if (handle != NULL) {
				CHECK("temp file read-back matches the payload",
				      fread(buffer, 1, length, handle) == length
				      && memcmp(buffer, payload, length) == 0);
				fclose(handle);
			}

			CHECK("temp file can be removed (cleanup)",
		      unlink(path) == 0);
		}
	}

	printf("%d checks, %d failures, %d skipped\n", checks, failures, skipped);

	return failures == 0 ? 0 : 1;
}
