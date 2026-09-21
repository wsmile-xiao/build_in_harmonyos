/* libvslvm 20240504 consumer test — generic (installed package only)
 *
 * Exercises the public API of the *installed* package (headers + shared library):
 * version string, access flags, codepage handling and the error/not-found paths
 * of check_volume_signature() plus the handle lifecycle.  Assertions here are
 * not platform specific; the OHOS specific LVM2 image round trip lives in
 * test_ohos.c.
 *
 * Return-value conventions verified against libvslvm_support.c / handle.c:
 * initialize/getters/set_codepage return 1 on success, close/free return 0,
 * error paths return -1.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libvslvm.h>

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
	libvslvm_error_t *error = NULL;
	char error_string[256];
	const char *version = NULL;
	char blank_path[512];
	char *tmpdir = NULL;
	libvslvm_handle_t *handle = NULL;
	int codepage = -1;
	int access_flags_read_write = 0;
	int access_flags_write = 0;
	int result = 0;

	printf("== libvslvm generic consumer test ==\n");

	tmpdir = getenv("TMPDIR");
	if (tmpdir == NULL || tmpdir[0] == '\0' || strcmp(tmpdir, "/tmp") == 0) {
		tmpdir = ".";
	}
	snprintf(blank_path, sizeof(blank_path), "%s/libvslvm_blank.img", tmpdir);

	/* Version string: the upstream release version, not the Conan ref */
	version = libvslvm_get_version();
	CHECK(version != NULL, "libvslvm_get_version() returns a string");
	CHECK(version != NULL && strstr(version, "20240504") != NULL,
	      "version string contains upstream release 20240504");

	/* Access flags: the public API declares read and write bits */
	access_flags_read_write = libvslvm_get_access_flags_read_write();
	CHECK(access_flags_read_write ==
	      (LIBVSLVM_ACCESS_FLAG_READ | LIBVSLVM_ACCESS_FLAG_WRITE),
	      "get_access_flags_read_write() returns READ|WRITE");
	access_flags_write = libvslvm_get_access_flags_write();
	CHECK(access_flags_write == (int) LIBVSLVM_ACCESS_FLAG_WRITE,
	      "get_access_flags_write() returns WRITE");

	/* Codepage round trip and the invalid value error path (set/get
	 * return 1 on success) */
	CHECK(libvslvm_set_codepage(LIBVSLVM_CODEPAGE_ASCII, NULL) == 1,
	      "set_codepage(ASCII) succeeds");
	CHECK(libvslvm_get_codepage(&codepage, NULL) == 1 &&
	      codepage == (int) LIBVSLVM_CODEPAGE_ASCII,
	      "get_codepage() reads back the value set");
	CHECK(libvslvm_set_codepage(0xdead, NULL) == -1,
	      "set_codepage(invalid) returns -1");

	/* Error object smoke test on the rejected codepage path */
	error = NULL;
	(void) libvslvm_set_codepage(0xdead, &error);
	if (error != NULL) {
		result = libvslvm_error_sprint(error, error_string,
		                               sizeof(error_string));
		CHECK(result > 0 && strstr(error_string, "codepage") != NULL,
		      "error_sprint() reports the codepage error");
		libvslvm_error_free(&error);
	} else {
		CHECK(0, "error_sprint() reports the codepage error");
	}

	/* check_volume_signature(): a blank file has no LVM2 label */
	(void) unlink(blank_path);
	CHECK(write_blank_file(blank_path, 16384) == 0,
	      "blank fixture file written");
	error = NULL;
	result = libvslvm_check_volume_signature(blank_path, &error);
	CHECK(result == 0, "check_volume_signature(blank) returns 0 (not found)");
	if (error != NULL) {
		libvslvm_error_free(&error);
	}

	/* handle lifecycle (initialize returns 1, close/free return 0) */
	handle = NULL;
	CHECK(libvslvm_handle_initialize(&handle, NULL) == 1 && handle != NULL,
	      "handle_initialize() succeeds");
	/* closing a handle that was never opened fails by design */
	CHECK(libvslvm_handle_close(handle, NULL) == -1,
	      "handle_close(unopened) returns -1");
	CHECK(libvslvm_handle_free(&handle, NULL) == 1 && handle == NULL,
	      "handle_free() succeeds");

	/* Opening a volume without an LVM2 label must fail with an error */
	handle = NULL;
	CHECK(libvslvm_handle_initialize(&handle, NULL) == 1,
	      "handle_initialize() for open-failure path");
	error = NULL;
	result = libvslvm_handle_open(handle, blank_path,
	                              LIBVSLVM_OPEN_READ, &error);
	CHECK(result == -1, "handle_open(blank) returns -1");
	CHECK(error != NULL, "handle_open(blank) sets an error object");
	if (error != NULL) {
		result = libvslvm_error_sprint(error, error_string,
		                               sizeof(error_string));
		/* error_sprint reports the outermost frame only */
		CHECK(result > 0 &&
		      strstr(error_string, "unable to open handle") != NULL,
		      "error reports the failed volume open");
		libvslvm_error_free(&error);
	} else {
		CHECK(0, "error reports the missing metadata area descriptor");
	}
	CHECK(libvslvm_handle_free(&handle, NULL) == 1,
	      "handle_free() after open-failure path");

	/* Opening a file that does not exist must fail with an error */
	handle = NULL;
	CHECK(libvslvm_handle_initialize(&handle, NULL) == 1,
	      "handle_initialize() for missing-file path");
	error = NULL;
	result = libvslvm_handle_open(handle, "no-such-volume.img",
	                              LIBVSLVM_OPEN_READ, &error);
	CHECK(result == -1, "handle_open(missing) returns -1");
	if (error != NULL) {
		libvslvm_error_free(&error);
	}
	CHECK(libvslvm_handle_free(&handle, NULL) == 1,
	      "handle_free() after missing-file path");

	(void) unlink(blank_path);

	printf("== %d assertions, %d failures ==\n", assertions, failures);

	if (failures > 0) {
		return 1;
	}
	return 0;
}
