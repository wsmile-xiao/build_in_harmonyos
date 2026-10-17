/* libsmraw 20240506 consumer test — generic (installed package only)
 *
 * Exercises the public API of the *installed* package (headers + shared
 * library): version string, codepage handling, single-segment RAW open/read
 * round trip via the filenames[] entry point, offset accounting and the
 * error paths of handle_open().  Assertions here are not platform specific;
 * the OHOS specific multi-segment round trip lives in test_ohos.c.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libsmraw.h>

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

#define SECTOR_SIZE 512
#define SECTOR_COUNT 8
#define IMAGE_SIZE (SECTOR_SIZE * SECTOR_COUNT)
#define MARKER "SMRAW-CONSUMER-MARKER-0123456789"

static void
fill_pattern(uint8_t *buffer, size_t size)
{
	size_t index = 0;

	for (index = 0; index < size; index++) {
		buffer[index] = (uint8_t)(index * 7 + (index >> 5));
	}
	(void)memcpy(buffer + 64, MARKER, sizeof(MARKER) - 1);
}

static int
write_pattern_file(const char *path, const uint8_t *buffer, size_t size)
{
	FILE *stream = fopen(path, "wb");

	if (stream == NULL) {
		return -1;
	}
	if (fwrite(buffer, 1, size, stream) != size) {
		fclose(stream);
		return -1;
	}
	if (fclose(stream) != 0) {
		return -1;
	}
	return 0;
}

int
main(void)
{
	libsmraw_error_t *error = NULL;
	libsmraw_handle_t *handle = NULL;
	uint8_t image[IMAGE_SIZE];
	uint8_t read_buffer[IMAGE_SIZE];
	uint8_t small_buffer[64];
	const char *version = NULL;
	char filename[] = "smraw_consumer_test.raw";
	char *missing[1] = { "no-such-file.raw" };
	char *segments[1];
	size64_t media_size = 0;
	off64_t offset = -1;
	off64_t seek_result = -1;
	int codepage = -1;
	int result = -1;
	ssize_t read_count = 0;

	printf("== libsmraw generic consumer test ==\n");

	/* Version string: upstream release version (not the Conan ref). */
	version = libsmraw_get_version();
	CHECK(version != NULL, "libsmraw_get_version() returns non-NULL");
	CHECK(version != NULL && strcmp(version, "20240506") == 0,
	      "version string is 20240506");

	/* Codepage handling: ASCII is a valid value, read-back must match. */
	result = libsmraw_set_codepage(LIBSMRAW_CODEPAGE_ASCII, &error);
	CHECK(result == 1, "libsmraw_set_codepage(ASCII) succeeds");
	result = libsmraw_get_codepage(&codepage, &error);
	CHECK(result == 1 && codepage == LIBSMRAW_CODEPAGE_ASCII,
	      "libsmraw_get_codepage() reads back ASCII");
	result = libsmraw_set_codepage(-42, &error);
	CHECK(result == -1, "libsmraw_set_codepage(-42) fails");
	if (error != NULL) {
		libsmraw_error_free(&error);
	}

	fill_pattern(image, IMAGE_SIZE);
	CHECK(write_pattern_file(filename, image, IMAGE_SIZE) == 0,
	      "synthetic 4 KiB RAW image written");

	/* Error path: opening a non-existing file must fail and set error. */
	result = libsmraw_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize succeeds");
	result = libsmraw_handle_open(handle, missing, 1,
	                              LIBSMRAW_OPEN_READ, &error);
	CHECK(result == -1, "handle_open(non-existing) returns -1");
	CHECK(error != NULL, "handle_open(non-existing) sets error");
	if (error != NULL) {
		libsmraw_error_free(&error);
	}
	result = libsmraw_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free after failed open");

	/* Happy path: open the synthetic image and read it back. */
	segments[0] = filename;
	result = libsmraw_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize (2nd)");
	result = libsmraw_handle_open(handle, segments, 1,
	                              LIBSMRAW_OPEN_READ, &error);
	CHECK(result == 1, "handle_open(RAW image) succeeds");
	result = libsmraw_handle_get_media_size(handle, &media_size, &error);
	CHECK(result == 1 && media_size == (size64_t)IMAGE_SIZE,
	      "media size is 4096 bytes");
	memset(read_buffer, 0, IMAGE_SIZE);
	read_count = libsmraw_handle_read_buffer(handle, read_buffer,
	                                         IMAGE_SIZE, &error);
	CHECK(read_count == (ssize_t)IMAGE_SIZE, "full image read");
	CHECK(memcmp(read_buffer, image, IMAGE_SIZE) == 0,
	      "read-back pattern matches");
	CHECK(memcmp(read_buffer + 64, MARKER, sizeof(MARKER) - 1) == 0,
	      "marker present at offset 64");
	result = libsmraw_handle_get_offset(handle, &offset, &error);
	CHECK(result == 1 && offset == (off64_t)IMAGE_SIZE,
	      "offset advanced to end of image");
	seek_result = libsmraw_handle_seek_offset(handle, 512, SEEK_SET,
	                                          &error);
	CHECK(seek_result == (off64_t)512, "seek_offset(512) returns 512");
	memset(small_buffer, 0, sizeof(small_buffer));
	read_count = libsmraw_handle_read_buffer(handle, small_buffer,
	                                         sizeof(small_buffer), &error);
	CHECK(read_count == (ssize_t)sizeof(small_buffer),
	      "64 bytes read after seek");
	CHECK(memcmp(small_buffer, image + 512, sizeof(small_buffer)) == 0,
	      "post-seek read matches image bytes 512..575");
	result = libsmraw_handle_close(handle, &error);
	CHECK(result == 0, "handle_close succeeds");
	result = libsmraw_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free succeeds");

	(void)unlink(filename);

	if (failures == 0) {
		printf("== libsmraw generic consumer test: %d assertions,"
		       " all PASS ==\n",
		       assertions);
	} else {
		printf("== libsmraw generic consumer test: %d/%d FAILED ==\n",
		       failures, assertions);
	}
	return failures == 0 ? 0 : 1;
}
