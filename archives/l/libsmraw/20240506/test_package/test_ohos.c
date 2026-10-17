/* libsmraw 20240506 consumer test — HarmonyOS specific
 *
 * Builds a synthetic Split RAW storage-media image (8 KiB split into two
 * 4 KiB segment files, 512-byte sectors, deterministic pattern + markers)
 * inside $TMPDIR on the device and reads it back through the installed
 * libsmraw public API via the multi-filename entry point.  This covers the
 * platform semantics that only exist on OHOS: the compile target itself, the
 * TMPDIR contract (/tmp is read-only on HarmonyOS), a real on-disk round
 * trip performed under that TMPDIR, and a read that crosses the segment
 * boundary at offset 4096.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libsmraw.h>

#if !defined(__OHOS__)
#error "test_ohos.c must be compiled for the OHOS target (__OHOS__)"
#endif

#define SECTOR_SIZE 512
#define SECTOR_COUNT 16
#define SEGMENT_SIZE (SECTOR_SIZE * 8) /* 4096 bytes per segment file */
#define IMAGE_SIZE (SECTOR_SIZE * SECTOR_COUNT)
#define BOUNDARY SEGMENT_SIZE /* segment boundary at offset 4096 */
#define MARKER "SMRAW-OHOS-ROUNDTRIP-MARKER-9876543210"

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

static void
fill_pattern(uint8_t *buffer, size_t size)
{
	size_t index = 0;

	for (index = 0; index < size; index++) {
		buffer[index] = (uint8_t)(index * 13 + 0x5a);
	}
	(void)memcpy(buffer + 128, MARKER, sizeof(MARKER) - 1);
	(void)memcpy(buffer + BOUNDARY - 8, MARKER, sizeof(MARKER) - 1);
	(void)memcpy(buffer + IMAGE_SIZE - 128, MARKER,
	             sizeof(MARKER) - 1);
}

static int
write_segment(const char *path, const uint8_t *buffer, size_t size)
{
	FILE *stream = fopen(path, "wb");

	if (stream == NULL) {
		return -1;
	}
	if (fwrite(buffer, 1, size, stream) != size || fclose(stream) != 0) {
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
	uint8_t cross[32];
	const char *tmpdir = getenv("TMPDIR");
	char path0[1024];
	char path1[1024];
	char *segments[2];
	size64_t media_size = 0;
	off64_t offset = -1;
	off64_t seek_result = -1;
	int result = -1;
	ssize_t read_count = 0;

	printf("== libsmraw OHOS specific consumer test ==\n");

	/* TMPDIR contract on HarmonyOS: /tmp is read-only, the environment
	 * must provide a writable TMPDIR and the library must work with
	 * segment files created under it. */
	CHECK(tmpdir != NULL && tmpdir[0] != '\0', "TMPDIR is set");
	CHECK(tmpdir != NULL && strcmp(tmpdir, "/tmp") != 0,
	      "TMPDIR is not the read-only /tmp");
	CHECK(tmpdir != NULL && access(tmpdir, W_OK) == 0,
	      "TMPDIR is writable");

	if (tmpdir == NULL ||
	    snprintf(path0, sizeof(path0), "%s/smraw_ohos_test.000", tmpdir) < 0 ||
	    snprintf(path1, sizeof(path1), "%s/smraw_ohos_test.001", tmpdir) < 0) {
		printf("  [FAIL] cannot build segment paths\n");
		return 1;
	}
	fill_pattern(image, IMAGE_SIZE);
	{
		FILE *stream = fopen(path0, "wb");

		CHECK(stream != NULL, "segment .000 created in TMPDIR");
		if (stream == NULL) {
			return 1;
		}
		fclose(stream);
	}
	CHECK(write_segment(path0, image, SEGMENT_SIZE) == 0 &&
	      write_segment(path1, image + SEGMENT_SIZE, SEGMENT_SIZE) == 0,
	      "both 4 KiB segments written");

	/* Error path first: non-existing segment inside TMPDIR. */
	result = libsmraw_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize succeeds");
	segments[0] = path0;
	segments[1] = "missing-segment.001";
	result = libsmraw_handle_open(handle, segments, 2,
	                              LIBSMRAW_OPEN_READ, &error);
	CHECK(result == -1, "handle_open(missing segment) returns -1");
	CHECK(error != NULL, "handle_open(missing segment) sets error");
	if (error != NULL) {
		libsmraw_error_free(&error);
	}
	result = libsmraw_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free after failed open");

	/* Round trip over two segments: open, size, full read, markers. */
	segments[0] = path0;
	segments[1] = path1;
	result = libsmraw_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize (2nd)");
	result = libsmraw_handle_open(handle, segments, 2,
	                              LIBSMRAW_OPEN_READ, &error);
	CHECK(result == 1, "handle_open(2 segments) succeeds");
	result = libsmraw_handle_get_media_size(handle, &media_size, &error);
	CHECK(result == 1 && media_size == (size64_t)IMAGE_SIZE,
	      "media size is 8192 bytes across 2 segments");
	memset(read_buffer, 0, IMAGE_SIZE);
	read_count = libsmraw_handle_read_buffer(handle, read_buffer,
	                                         IMAGE_SIZE, &error);
	CHECK(read_count == (ssize_t)IMAGE_SIZE, "full 8 KiB read");
	CHECK(memcmp(read_buffer, image, IMAGE_SIZE) == 0,
	      "full read-back pattern matches across segments");
	CHECK(memcmp(read_buffer + 128, MARKER, sizeof(MARKER) - 1) == 0,
	      "marker present at offset 128 (segment .000)");
	CHECK(memcmp(read_buffer + IMAGE_SIZE - 128, MARKER,
	             sizeof(MARKER) - 1) == 0,
	      "marker present at offset 8064 (segment .001)");

	/* Segment-boundary read: 32 bytes starting 8 bytes before the
	 * boundary must reproduce image bytes 4088..4119. */
	seek_result = libsmraw_handle_seek_offset(
	    handle, (off64_t)(BOUNDARY - 8), SEEK_SET, &error);
	CHECK(seek_result == (off64_t)(BOUNDARY - 8),
	      "seek_offset(4088) returns 4088");
	memset(cross, 0, sizeof(cross));
	read_count = libsmraw_handle_read_buffer(handle, cross, sizeof(cross),
	                                         &error);
	CHECK(read_count == (ssize_t)sizeof(cross),
	      "32-byte boundary-crossing read");
	CHECK(memcmp(cross, image + BOUNDARY - 8, sizeof(cross)) == 0,
	      "boundary-crossing bytes match");
	result = libsmraw_handle_get_offset(handle, &offset, &error);
	CHECK(result == 1 && offset == (off64_t)(BOUNDARY + 24),
	      "offset after boundary read is 4120");
	result = libsmraw_handle_signal_abort(handle, &error);
	CHECK(result == 1, "signal_abort accepted");
	result = libsmraw_handle_close(handle, &error);
	CHECK(result == 0, "handle_close succeeds");
	result = libsmraw_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free succeeds");

	(void)unlink(path0);
	(void)unlink(path1);

	if (failures == 0) {
		printf("== libsmraw OHOS consumer test: %d assertions,"
		       " all PASS ==\n",
		       assertions);
	} else {
		printf("== libsmraw OHOS consumer test: %d/%d FAILED ==\n",
		       failures, assertions);
	}
	return failures == 0 ? 0 : 1;
}
