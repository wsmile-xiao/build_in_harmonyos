/* libewf 20260924 consumer test — OHOS specific (installed package only)
 *
 * HarmonyOS/OS-specific round trip:
 *  - must be compiled as an OHOS target (__OHOS__)
 *  - TMPDIR semantics: set, not the read-only /tmp, writable
 *  - synthesizes a compressed EWF image INSIDE TMPDIR through the write
 *    chain (open(WRITE) → set_media_size → set_compression_values(FAST,
 *    deflate) → write_buffer → close) and reads it back through the full
 *    read chain: signature → open(READ) → media size → full read + marker
 *    → cross-sector-boundary read → tail read → seek/offset → EOF
 *    → signal abort → close/free
 *  - error path: opening a non-existing image set inside TMPDIR returns -1
 *    and frees cleanly
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libewf.h>

#ifndef __OHOS__
#error "test_ohos.c must be compiled for the OHOS target"
#endif

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

int main(int argc, char *argv[])
{
	libewf_error_t *error = NULL;
	libewf_handle_t *handle = NULL;
	const char *tmpdir = NULL;
	const char *version = NULL;
	char base_path[512];
	char e01_path[512];
	unsigned char image[TEST_WRITE_SIZE];
	unsigned char buffer[TEST_WRITE_SIZE];
	unsigned char small_buffer[64];
	unsigned char tail_window[64];
	char *filenames[1];
	off64_t offset = 0;
	size64_t media_size = 0;
	ssize_t read_count = 0;
	ssize_t write_count = 0;
	int sector_iterator = 0;
	int result = 0;

	/* The test binary must be an OHOS target with a writable TMPDIR. */
	tmpdir = getenv("TMPDIR");
	CHECK(tmpdir != NULL, "TMPDIR is set");
	if (tmpdir == NULL)
	{
		printf("== libewf OHOS consumer test: %d/%d FAILED ==\\n",
		       failures,
		       assertions);
		return 1;
	}
	CHECK(strcmp(tmpdir, "/tmp") != 0, "TMPDIR is not the read-only /tmp");
	CHECK(access(tmpdir, W_OK) == 0, "TMPDIR is writable");

	version = libewf_get_version();
	CHECK(version != NULL && strcmp(version, LIBEWF_VERSION_STRING) == 0,
	      "OHOS target reports the adapted version " LIBEWF_VERSION_STRING);

	/* Build the in-memory image: 26 sectors of letters A..Z. */
	for (sector_iterator = 0; sector_iterator < 26; sector_iterator++)
	{
		memset(image + (sector_iterator * 512), 'A' + sector_iterator, 512);
	}

	(void)snprintf(base_path, sizeof(base_path),
	               "%s/libewf_ohos_test", tmpdir);
	(void)snprintf(e01_path, sizeof(e01_path),
	               "%s.E01", base_path);

	/* ── Write chain (deflate/fast compression exercises zlib) ── */
	result = libewf_handle_initialize(&handle, &error);
	CHECK(result == 1, "handle_initialize succeeds");

	filenames[0] = base_path;
	result = libewf_handle_open(handle,
	                            filenames,
	                            1,
	                            LIBEWF_OPEN_WRITE,
	                            &error);
	CHECK(result == 1, "handle_open(WRITE) succeeds in TMPDIR");

	result = libewf_handle_set_media_size(handle,
	                                      (size64_t)TEST_WRITE_SIZE,
	                                      &error);
	CHECK(result == 1, "set_media_size succeeds");

	result = libewf_handle_set_compression_values(
	    handle,
	    LIBEWF_COMPRESSION_LEVEL_FAST,
	    0,
	    &error);
	CHECK(result == 1, "set_compression_values(FAST) succeeds");

	write_count = libewf_handle_write_buffer(handle,
	                                         image,
	                                         TEST_WRITE_SIZE,
	                                         &error);
	CHECK(write_count == (ssize_t)TEST_WRITE_SIZE,
	      "write_buffer writes all bytes (deflate path, zlib)");

	result = libewf_handle_close(handle, &error);
	CHECK(result == 0, "handle_close(WRITE) returns 0");
	result = libewf_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free succeeds");

	/* The compressed image must carry the EWF signature. */
	result = libewf_check_file_signature(e01_path, &error);
	CHECK(result == 1, "compressed image carries EWF signature");

	/* ── Read chain ── */
	result = libewf_handle_initialize(&handle, &error);
	CHECK(result == 1, "handle_initialize (read) succeeds");

	filenames[0] = e01_path;
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
	      "full read returns all bytes (deflate inflate path)");
	CHECK(memcmp(buffer, image, TEST_WRITE_SIZE) == 0,
	      "read-back content matches written image");

	/* Cross-sector-boundary read. */
	offset = libewf_handle_seek_offset(handle, 500, SEEK_SET, &error);
	CHECK(offset == (off64_t)500, "seek_offset(500) == 500");
	memset(small_buffer, 0, sizeof(small_buffer));
	read_count = libewf_handle_read_buffer(handle,
	                                       small_buffer,
	                                       sizeof(small_buffer),
	                                       &error);
	CHECK(read_count == (ssize_t)sizeof(small_buffer) &&
	          memcmp(small_buffer, image + 500, sizeof(small_buffer)) == 0,
	      "boundary read (500..563) spans sectors A/B correctly");

	/* Tail read. */
	offset = libewf_handle_seek_offset(
	    handle, TEST_WRITE_SIZE - 64, SEEK_SET, &error);
	CHECK(offset == (off64_t)(TEST_WRITE_SIZE - 64),
	      "seek_offset(13248) == 13248");
	memset(tail_window, 0, sizeof(tail_window));
	read_count = libewf_handle_read_buffer(handle,
	                                       tail_window,
	                                       sizeof(tail_window),
	                                       &error);
	CHECK(read_count == (ssize_t)sizeof(tail_window) &&
	          memcmp(tail_window, image + TEST_WRITE_SIZE - 64,
	                 sizeof(tail_window)) == 0,
	      "tail read returns 64 bytes at 13248");

	/* EOF semantics. */
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

	/* Error path: open a non-existing image set inside TMPDIR. */
	{
		libewf_handle_t *bad = NULL;

		result = libewf_handle_initialize(&bad, &error);
		filenames[0] = (char *)"/no/such/ohos/image/set";
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

	(void)unlink(e01_path);

	if (failures == 0)
	{
		printf("== libewf OHOS consumer test: %d assertions,"
		       " all PASS ==\n",
		       assertions);
	}
	else
	{
		printf("== libewf OHOS consumer test: %d/%d FAILED ==\n",
		       failures,
		       assertions);
	}
	return failures == 0 ? 0 : 1;
}
