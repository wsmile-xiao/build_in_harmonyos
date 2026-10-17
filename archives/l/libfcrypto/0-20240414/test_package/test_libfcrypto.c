/* Consumer test for libfcrypto 0-20240414.
 *
 * Exercises the packaged library through its public API: version query,
 * RC4 context lifecycle, the published "Secret"/"Attack at dawn" test vector,
 * an encrypt/decrypt round trip on a second context and the error path of a
 * NULL context (the error object must be populated and freeable).
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include <libfcrypto.h>

static int failures = 0;
static int checks = 0;

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

int main(void)
{
	const uint8_t rc4_key[] = "Secret";
	const uint8_t rc4_plaintext[] = "Attack at dawn";
	const uint8_t rc4_expected[] = {
		0x45, 0xA0, 0x1F, 0x64, 0x5F, 0xC3, 0x5B, 0x38, 0x35,
		0x52, 0x54, 0x4B, 0x9B, 0xF5
	};
	uint8_t rc4_ciphertext[ 14 ];
	uint8_t rc4_recovered[ 14 ];

	libfcrypto_error_t *error = NULL;
	libfcrypto_rc4_context_t *encrypt_context = NULL;
	libfcrypto_rc4_context_t *decrypt_context = NULL;

	const char *version = libfcrypto_get_version();

	printf("libfcrypto consumer test (version: %s)\n",
	       version != NULL ? version : "(null)");

	CHECK("get_version returns a non-NULL string",
	      version != NULL);
	CHECK("version string is not empty",
	      version != NULL && version[ 0 ] != '\0');

	CHECK("rc4_context_initialize succeeds",
	      libfcrypto_rc4_context_initialize(
		      &encrypt_context, &error ) == 1);
	CHECK("rc4_context_set_key with the 48-bit key succeeds",
	      libfcrypto_rc4_context_set_key(
		      encrypt_context, rc4_key, 48, &error ) == 1);
	CHECK("rc4_crypt encrypts the plaintext buffer",
	      libfcrypto_rc4_crypt(
		      encrypt_context,
		      rc4_plaintext, 14,
		      rc4_ciphertext, 14,
		      &error ) == 1);
	CHECK("ciphertext matches the published RC4 test vector",
	      memcmp(rc4_ciphertext, rc4_expected, 14) == 0);

	CHECK("second rc4_context_initialize succeeds",
	      libfcrypto_rc4_context_initialize(
		      &decrypt_context, &error ) == 1);
	CHECK("second rc4_context_set_key succeeds",
	      libfcrypto_rc4_context_set_key(
		      decrypt_context, rc4_key, 48, &error ) == 1);
	CHECK("rc4_crypt decrypts the ciphertext buffer",
	      libfcrypto_rc4_crypt(
		      decrypt_context,
		      rc4_ciphertext, 14,
		      rc4_recovered, 14,
		      &error ) == 1);
	CHECK("decrypted buffer matches the original plaintext",
	      memcmp(rc4_recovered, rc4_plaintext, 14) == 0);

	CHECK("rc4_crypt with a NULL context fails",
	      libfcrypto_rc4_crypt(
		      NULL, rc4_plaintext, 14, rc4_ciphertext, 14, &error )
	      == -1);
	CHECK("the failed call populated the error object",
	      error != NULL);
	if (error != NULL) {
		char error_string[ 128 ];

		libfcrypto_error_sprint(error, error_string, 128);
		printf("     error: %s\n", error_string);
	}
	libfcrypto_error_free(&error);
	CHECK("error_free released the error object",
	      error == NULL);

	CHECK("rc4_context_free succeeds",
	      libfcrypto_rc4_context_free(&encrypt_context, &error) == 1);
	CHECK("second rc4_context_free succeeds",
	      libfcrypto_rc4_context_free(&decrypt_context, &error) == 1);

	printf("%d checks, %d failures\n", checks, failures);

	return failures == 0 ? 0 : 1;
}
