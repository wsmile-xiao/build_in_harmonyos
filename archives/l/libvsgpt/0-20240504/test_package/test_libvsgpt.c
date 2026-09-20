/* libvsgpt 0-20240504 consumer test — generic (installed package only)
 *
 * Exercises the public API of the *installed* package (headers + shared library):
 * version, access flags, codepage handling, signature detection and the error
 * paths of check_volume_signature()/volume_open().  Assertions here are not
 * platform specific; the OHOS specific round trip lives in test_ohos.c.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libvsgpt.h>

static int assertions = 0;
static int failures = 0;

#define CHECK(condition, message)                                              \
	do {                                                                   \
		assertions++;                                                  \
		if (condition) {                                               \
			printf("  [PASS] %s\n", message);                      \
		} else {                                                       \
			printf("  [FAIL] %s\n", message);                      \
			failures++;                                            \
		}                                                              \
	} while (0)

static int
write_blank_file(const char *path, size_t size)
{
	FILE *stream = NULL;
	size_t index = 0;

	stream = fopen(path, "wb");
	if (stream == NULL) {
		return -1;
	}
	for (index = 0; index < size; index++) {
		if (fputc(0, stream) == EOF) {
			fclose(stream);
			return -1;
		}
	}
	fclose(stream);
	return 0;
}

int
main(void)
{
	libvsgpt_error_t *error = NULL;
	char error_string[256];
	const char *version = NULL;
	char blank_path[512];
	char *tmpdir = NULL;
	int codepage = -1;
	int result = 0;

	printf("== libvsgpt generic consumer test ==\n");

	/* 1. version identity: the library reports the upstream version, not the
	 * Conan package version (0-20240504). */
	version = libvsgpt_get_version();
	CHECK(version != NULL, "libvsgpt_get_version() returns a string");
	CHECK(version != NULL && strcmp(version, "20240504") == 0,
	      "libvsgpt_get_version() == \"20240504\" (upstream version)");

	/* 2. access flags */
	CHECK(libvsgpt_get_access_flags_read() == LIBVSGPT_ACCESS_FLAG_READ,
	      "libvsgpt_get_access_flags_read() == LIBVSGPT_ACCESS_FLAG_READ");
	CHECK(libvsgpt_get_access_flags_read_write() ==
	          (LIBVSGPT_ACCESS_FLAG_READ | LIBVSGPT_ACCESS_FLAG_WRITE),
	      "libvsgpt_get_access_flags_read_write() == READ|WRITE");

	/* 3. codepage handling: locale -> ASCII codepage set/get round trip */
	error = NULL;
	result = libvsgpt_get_codepage(&codepage, &error);
	CHECK(result == 1, "libvsgpt_get_codepage() succeeds");
	if (result != 1 && error != NULL) {
		libvsgpt_error_sprint(error, error_string, 256);
		printf("  (error: %s)\n", error_string);
	}
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}
	result = libvsgpt_set_codepage(1252, &error);
	CHECK(result == 1, "libvsgpt_set_codepage(1252) succeeds");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}
	codepage = -1;
	result = libvsgpt_get_codepage(&codepage, &error);
	CHECK(result == 1 && codepage == 1252,
	      "libvsgpt_get_codepage() returns the codepage set before (1252)");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}
	result = libvsgpt_set_codepage(0, &error);
	CHECK(result == 1, "libvsgpt_set_codepage(0) restores ASCII/ISO-8859-1");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}

	/* 4. signature detection error paths on a file without a GPT */
	tmpdir = getenv("TMPDIR");
	if (tmpdir == NULL || tmpdir[0] == '\0' || strcmp(tmpdir, "/tmp") == 0) {
		tmpdir = (char *) ".";
	}
	snprintf(blank_path, sizeof(blank_path), "%s/libvsgpt-blank-%ld.bin",
	         tmpdir, (long) getpid());
	CHECK(write_blank_file(blank_path, 8192) == 0,
	      "created a blank (non-GPT) 8192-byte file for the error paths");

	error = NULL;
	result = libvsgpt_check_volume_signature(blank_path, &error);
	CHECK(result == 0,
	      "check_volume_signature() returns 0 for data without a GPT signature");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}
	result = libvsgpt_check_volume_signature("/nonexistent/libvsgpt/no.img",
	                                         &error);
	CHECK(result == -1,
	      "check_volume_signature() returns -1 for a missing file");
	CHECK(error != NULL,
	      "check_volume_signature() sets an error for a missing file");
	if (error != NULL) {
		error_string[0] = 0;
		libvsgpt_error_sprint(error, error_string, 256);
		libvsgpt_error_free(&error);
		error = NULL;
	}

	/* 5. volume lifecycle on a non-GPT file must fail cleanly (no leak of the
	 * volume handle) and report an error. */
	{
		libvsgpt_volume_t *volume = NULL;

		error = NULL;
		result = libvsgpt_volume_initialize(&volume, &error);
		CHECK(result == 1 && volume != NULL,
		      "libvsgpt_volume_initialize() succeeds");
		if (error != NULL) {
			libvsgpt_error_free(&error);
			error = NULL;
		}
		result = libvsgpt_volume_open(volume, blank_path,
		                              LIBVSGPT_OPEN_READ, &error);
		CHECK(result == -1,
		      "volume_open() on a file without GPT fails (-1)");
		CHECK(error != NULL, "volume_open() failure sets an error object");
		if (error != NULL) {
			libvsgpt_error_free(&error);
			error = NULL;
		}
		result = libvsgpt_volume_free(&volume, &error);
		CHECK(result == 1 && volume == NULL,
		      "libvsgpt_volume_free() releases the volume handle");
		if (error != NULL) {
			libvsgpt_error_free(&error);
			error = NULL;
		}
	}

	unlink(blank_path);

	if (failures != 0) {
		printf("%d of %d assertions FAILED\n", failures, assertions);
		return EXIT_FAILURE;
	}
	printf("%d assertions passed\n", assertions);
	return EXIT_SUCCESS;
}
