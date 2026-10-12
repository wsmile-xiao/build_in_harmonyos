/* libewf 20260924 consumer test — generic (installed package only)
 *
 * Exercises the public API of the *installed* package (headers + shared
 * library): version string, access flags, codepage handling, EWF signature
 * detection (positive/negative), and a full write/read round trip over a
 * self-synthesized EWF image (26 sectors x 512 bytes, no compression):
 * open(WRITE) → set_media_size → set_compression_values → write_buffer
 * → close → signature → open(READ) → media size → full read-back
 * → boundary/offset reads → seek → EOF semantics → error paths
 * → close/free.
 *
 * Assertions here are not platform specific; the OHOS specific round trip
 * lives in test_ohos.c (compiled and run only for settings.os=OHOS).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libewf.h>

#ifndef LIBEWF_VERSION_STRING
#define LIBEWF_VERSION_STRING "20260924"
#endif

static int assertions = 0;
static int failures = 0;

#define CHECK(condition, message)                                              \
	do                                                                     \
	{                                                                      \
		assertions++;                                                  \
		if (!(condition))                                              \
		{                                                              \
			failures++;                                            \
			printf("FAIL: %s\n", message);                         \
		}                                                              \
	} while (0)

#define TEST_WRITE_SIZE (512 * 26)
#define TEST_FILENAME_BASE "libewf_consumer_test"

int main(void)
{
	libewf_error_t *error = NULL;
	libewf_handle_t *handle = NULL;
	const char *version = NULL;
	unsigned char image[TEST_WRITE_SIZE];
	unsigned char buffer[TEST_WRITE_SIZE];
	unsigned char small_buffer[64];
	char *filenames[1];
	off64_t offset = 0;
	size64_t media_size = 0;
	ssize_t read_count = 0;
	ssize_t write_count = 0;
	int codepage = 0;
	int sector_iterator = 0;
	int result = 0;

	/* Version string and access flag ABI. */
	version = libewf_get_version();
	CHECK(version != NULL, "libewf_get_version() != NULL");
	if (version == NULL)
	{
		printf("== libewf generic consumer test: %d/%d FAILED ==\n",
		       failures,
		       assertions);
		return 1;
	}
	CHECK(strcmp(version, LIBEWF_VERSION_STRING) == 0,
	      "libewf_get_version() == \"" LIBEWF_VERSION_STRING "\"");
	CHECK(libewf_get_access_flags_read() == LIBEWF_ACCESS_FLAG_READ,
	      "get_access_flags_read() == LIBEWF_ACCESS_FLAG_READ");
	CHECK(libewf_get_access_flags_write() == LIBEWF_ACCESS_FLAG_WRITE,
	      "get_access_flags_write() == LIBEWF_ACCESS_FLAG_WRITE");
	CHECK((libewf_get_access_flags_read_write() &
	       (LIBEWF_ACCESS_FLAG_READ | LIBEWF_ACCESS_FLAG_WRITE)) ==
	              (LIBEWF_ACCESS_FLAG_READ | LIBEWF_ACCESS_FLAG_WRITE),
	      "get_access_flags_read_write() covers READ|WRITE");

	/* Codepage handling (UTF-8 default path). */
	result = libewf_set_codepage(0, &error);
	CHECK(result == 1, "libewf_set_codepage(0) returns 1");
	result = libewf_get_codepage(&codepage, &error);
	CHECK(result == 1 && codepage == 0, "get_codepage() returns 1 and 0");

	/* Negative signature check: plain text file is not an EWF image. */
	{
		FILE *plain = fopen("not_ewf.txt", "w");

		if (plain != NULL)
		{
			fprintf(plain, "plain text, not an EWF image\n");
			fclose(plain);
			result = libewf_check_file_signature("not_ewf.txt", &error);
			CHECK(result == 0, "check_file_signature(plain text) == 0");
			(void)unlink("not_ewf.txt");
		}
	}

	/* Error path: signature of a non-existing file. */
	result = libewf_check_file_signature("no_such_file_xyz.e01", &error);
	CHECK(result == -1, "check_file_signature(missing) == -1");
	if (error != NULL)
	{
		libewf_error_free(&error);
	}
	CHECK(error == NULL, "error freed and NULLed");

	/* Build the in-memory image: 26 sectors of letters A..Z. */
	for (sector_iterator = 0; sector_iterator < 26; sector_iterator++)
	{
		memset(image + (sector_iterator * 512), 'A' + sector_iterator, 512);
	}

	/* ── Write round trip ── */
	result = libewf_handle_initialize(&handle, &error);
	CHECK(result == 1, "handle_initialize succeeds");

	filenames[0] = (char *)TEST_FILENAME_BASE;
	result = libewf_handle_open(handle,
	                            filenames,
	                            1,
	                            LIBEWF_OPEN_WRITE,
	                            &error);
	CHECK(result == 1, "handle_open(WRITE) succeeds");

	result = libewf_handle_set_media_size(handle,
	                                      (size64_t)TEST_WRITE_SIZE,
	                                      &error);
	CHECK(result == 1, "set_media_size succeeds");

	result = libewf_handle_set_compression_values(
	    handle,
	    LIBEWF_COMPRESSION_LEVEL_NONE,
	    0,
	    &error);
	CHECK(result == 1, "set_compression_values(NONE) succeeds");

	write_count = libewf_handle_write_buffer(handle,
	                                         image,
	                                         TEST_WRITE_SIZE,
	                                         &error);
	CHECK(write_count == (ssize_t)TEST_WRITE_SIZE,
	      "write_buffer writes all " "13312" " bytes");

	result = libewf_handle_close(handle, &error);
	CHECK(result == 0, "handle_close(WRITE) returns 0");
	result = libewf_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free succeeds");

	/* The written image must carry the EWF signature. */
	result = libewf_check_file_signature(TEST_FILENAME_BASE ".E01", &error);
	CHECK(result == 1,
	      "check_file_signature(<base>.E01) == 1 after write");

	/* ── Read round trip ── */
	result = libewf_handle_initialize(&handle, &error);
	CHECK(result == 1, "handle_initialize (read) succeeds");

	filenames[0] = (char *)TEST_FILENAME_BASE ".E01";
	result = libewf_handle_open(handle,
	                            filenames,
	                            1,
	                            LIBEWF_OPEN_READ,
	                            &error);
	CHECK(result == 1, "handle_open(READ) succeeds");

	result = libewf_handle_get_media_size(handle, &media_size, &error);
	CHECK(result == 1 && media_size == (size64_t)TEST_WRITE_SIZE,
	      "get_media_size == 13312");

	memset(buffer, 0, sizeof(buffer));
	read_count = libewf_handle_read_buffer(handle,
	                                       buffer,
	                                       sizeof(buffer),
	                                       &error);
	CHECK(read_count == (ssize_t)sizeof(buffer),
	      "read_buffer returns full size");
	CHECK(memcmp(buffer, image, TEST_WRITE_SIZE) == 0,
	      "read-back content matches written image");

	/* Offset / seek semantics. */
	result = libewf_handle_get_offset(handle, &offset, &error);
	CHECK(result == 1 && offset == (off64_t)TEST_WRITE_SIZE,
	      "get_offset() == 13312 after full read");

	offset = libewf_handle_seek_offset(handle, 4096, SEEK_SET, &error);
	CHECK(offset == (off64_t)4096, "seek_offset(4096) == 4096");
	memset(small_buffer, 0, sizeof(small_buffer));
	read_count = libewf_handle_read_buffer(handle,
	                                       small_buffer,
	                                       sizeof(small_buffer),
	                                       &error);
	CHECK(read_count == (ssize_t)sizeof(small_buffer) &&
	          memcmp(small_buffer, image + 4096, sizeof(small_buffer)) == 0,
	      "post-seek read matches image bytes 4096..4159");

	/* EOF semantics: seek to end, read must yield 0 bytes, no error. */
	offset = libewf_handle_seek_offset(handle, 0, SEEK_END, &error);
	CHECK(offset == (off64_t)TEST_WRITE_SIZE,
	      "seek_offset(0, SEEK_END) == 13312");
	memset(small_buffer, 0, sizeof(small_buffer));
	read_count = libewf_handle_read_buffer(handle,
	                                       small_buffer,
	                                       sizeof(small_buffer),
	                                       &error);
	CHECK(read_count == 0, "read at EOF returns 0 bytes");
	CHECK(error == NULL, "read at EOF sets no error");

	/* Error path: open a non-existing image set. */
	{
		libewf_handle_t *bad = NULL;

		result = libewf_handle_initialize(&bad, &error);
		filenames[0] = (char *)"missing_image_set";
		result = libewf_handle_open(bad,
		                            filenames,
		                            1,
		                            LIBEWF_OPEN_READ,
		                            &error);
		CHECK(result == -1, "open(missing image set) == -1");
		if (error != NULL)
		{
			libewf_error_free(&error);
		}
		result = libewf_handle_free(&bad, &error);
		CHECK(result == 1 && bad == NULL, "bad handle freed");
		if (error != NULL)
		{
			libewf_error_free(&error);
		}
	}

	/* Signal abort + lifecycle. */
	result = libewf_handle_signal_abort(handle, &error);
	CHECK(result == 1, "handle_signal_abort succeeds");
	result = libewf_handle_close(handle, &error);
	CHECK(result == 0, "handle_close returns 0");
	result = libewf_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free succeeds");

	(void)unlink(TEST_FILENAME_BASE ".E01");

	if (failures == 0)
	{
		printf("== libewf generic consumer test: %d assertions,"
		       " all PASS ==\n",
		       assertions);
	}
	else
	{
		printf("== libewf generic consumer test: %d/%d FAILED ==\n",
		       failures,
		       assertions);
	}
	return failures == 0 ? 0 : 1;
}
