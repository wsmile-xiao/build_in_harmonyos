/* libvmdk 20240510 consumer test — OHOS specific (installed package only)
 *
 * HarmonyOS/OS-specific round trip:
 *  - must be compiled as an OHOS target (__OHOS__)
 *  - TMPDIR semantics: set, not the read-only /tmp, writable
 *  - synthesizes a monolithicFlat VMDK (descriptor + 8 KiB flat extent)
 *    INSIDE TMPDIR and reads it back through the full API chain:
 *    open → open_extent_data_files → media size → disk type → content id
 *    → full read + marker → cross-sector-boundary read → tail read
 *    → seek/offset → open-handles limit → signal abort → close/free
 *  - error path: opening a non-existing VMDK inside TMPDIR sets a
 *    printable error backtrace
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libvmdk.h>

#ifndef __OHOS__
#error "test_ohos.c must be compiled for the OHOS target"
#endif

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
#define SECTOR_COUNT 16
#define IMAGE_SIZE (SECTOR_SIZE * SECTOR_COUNT)
#define MARKER "VMDK-OHOS-MARKER-0123456789abcdef"

static const char *descriptor_template =
    "# Disk DescriptorFile\n"
    "version=1\n"
    "CID=fffffffe\n"
    "parentCID=ffffffff\n"
    "createType=\"monolithicFlat\"\n"
    "\n"
    "# Extent description\n"
    "RW 16 FLAT \"ohos_vmdk_data.vmdk\" 0\n"
    "\n"
    "# The Disk Data Base\n"
    "ddb.adapterType = \"lsilogic\"\n"
    "ddb.geometry.cylinders = \"1\"\n"
    "ddb.geometry.heads = \"1\"\n"
    "ddb.geometry.sectors = \"16\"\n"
    "ddb.virtualHWVersion = \"4\"\n";

static void
fill_pattern(uint8_t *buffer, size_t size)
{
	size_t index;

	for (index = 0; index < size; index++) {
		buffer[index] = (uint8_t)((index * 13 + (index >> 3)) & 0xff);
	}
	(void)memcpy(buffer + 64, MARKER, sizeof(MARKER) - 1);
}

static int
write_file(const char *path, const void *data, size_t size)
{
	FILE *stream = fopen(path, "wb");

	if (stream == NULL) {
		return -1;
	}
	if (fwrite(data, 1, size, stream) != size) {
		fclose(stream);
		return -1;
	}
	return fclose(stream) == 0 ? 0 : -1;
}

int
main(void)
{
	libvmdk_error_t *error = NULL;
	libvmdk_handle_t *handle = NULL;
	uint8_t image[IMAGE_SIZE];
	uint8_t read_buffer[IMAGE_SIZE];
	uint8_t boundary[16];
	uint8_t tail_window[64];
	const char *tmpdir = NULL;
	char descriptor_path[1024];
	char data_path[1024];
	char missing_path[1024];
	char error_string[4096];  /* conan test cwd 路径长，双层 backtrace 超 512B 时 sprint 返 -1（round-2 实测） */
	size64_t media_size = 0;
	off64_t offset = -1;
	uint32_t content_identifier = 0;
	int disk_type = -1;
	int result = -1;
	ssize_t read_count = 0;

	printf("== libvmdk OHOS consumer test ==\n");

	/* Platform assertions. */
	CHECK(1, "__OHOS__ target compiled (compile-time gate)");
	tmpdir = getenv("TMPDIR");
	CHECK(tmpdir != NULL && tmpdir[0] != '\0', "TMPDIR is set and non-empty");
	CHECK(tmpdir != NULL && strcmp(tmpdir, "/tmp") != 0,
	      "TMPDIR is not the read-only /tmp");
	CHECK(tmpdir != NULL && access(tmpdir, W_OK) == 0,
	      "TMPDIR is writable");

	if (tmpdir == NULL || tmpdir[0] == '\0') {
		printf("== libvmdk OHOS consumer test: %d/%d FAILED (no"
		       " TMPDIR) ==\n",
		       failures, assertions);
		return 1;
	}

	(void)snprintf(descriptor_path, sizeof(descriptor_path),
	               "%s/ohos_vmdk_desc.vmdk", tmpdir);
	(void)snprintf(data_path, sizeof(data_path),
	               "%s/ohos_vmdk_data.vmdk", tmpdir);
	(void)snprintf(missing_path, sizeof(missing_path),
	               "%s/no-such-ohos.vmdk", tmpdir);

	/* Synthesize the VMDK pair inside TMPDIR. */
	fill_pattern(image, IMAGE_SIZE);
	CHECK(write_file(descriptor_path, descriptor_template,
	                 strlen(descriptor_template)) == 0,
	      "descriptor written into TMPDIR");
	CHECK(write_file(data_path, image, IMAGE_SIZE) == 0,
	      "flat extent data (8 KiB) written into TMPDIR");

	/* Error path inside TMPDIR. */
	result = libvmdk_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize succeeds");
	result = libvmdk_handle_open(handle, missing_path,
	                             LIBVMDK_ACCESS_FLAG_READ, &error);
	CHECK(result == -1, "handle_open(missing in TMPDIR) fails");
	CHECK(error != NULL, "error object set for missing file");
	if (error != NULL) {
		result = libvmdk_error_backtrace_sprint(error, error_string,
		                                        sizeof(error_string));
		CHECK(result > 0, "error backtrace is printable");
		libvmdk_error_free(&error);
	}
	result = libvmdk_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free after error");

	/* Happy path: open the TMPDIR image and read the full chain.
	 * The open-handles limit must be set BEFORE open(): upstream
	 * libvmdk_handle_set_maximum_number_of_open_handles() returns -1
	 * (and corrupts the extent pool's last-used list, which then also
	 * breaks handle_close) when the extent data file IO pool already
	 * exists — verified by device probe; with the pool not yet created
	 * it succeeds. See notes.md "known limitations". */
	result = libvmdk_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize (2nd)");
	result = libvmdk_handle_set_maximum_number_of_open_handles(handle, 4,
	                                                            &error);
	CHECK(result == 1 && error == NULL,
	      "set_maximum_number_of_open_handles(4) before open succeeds");
	result = libvmdk_handle_open(handle, descriptor_path,
	                             LIBVMDK_ACCESS_FLAG_READ, &error);
	CHECK(result == 1, "handle_open(TMPDIR descriptor) succeeds");
	result = libvmdk_handle_open_extent_data_files(handle, &error);
	CHECK(result == 1, "handle_open_extent_data_files succeeds");

	result = libvmdk_handle_get_media_size(handle, &media_size, &error);
	CHECK(result == 1 && media_size == (size64_t)IMAGE_SIZE,
	      "media size is 8192 bytes");
	result = libvmdk_handle_get_disk_type(handle, &disk_type, &error);
	CHECK(result == 1 && disk_type == LIBVMDK_DISK_TYPE_MONOLITHIC_FLAT,
	      "disk type is MONOLITHIC_FLAT");
	result = libvmdk_handle_get_content_identifier(handle,
	                                               &content_identifier,
	                                               &error);
	CHECK(result == 1 && content_identifier == 0xfffffffe,
	      "content identifier is 0xfffffffe");

	/* Full read-back + marker. */
	memset(read_buffer, 0, IMAGE_SIZE);
	read_count = libvmdk_handle_read_buffer(handle, read_buffer,
	                                         IMAGE_SIZE, &error);
	CHECK(read_count == (ssize_t)IMAGE_SIZE, "full image read (8192)");
	CHECK(memcmp(read_buffer, image, IMAGE_SIZE) == 0,
	      "read-back pattern matches");
	CHECK(memcmp(read_buffer + 64, MARKER, sizeof(MARKER) - 1) == 0,
	      "OHOS marker present at offset 64");

	/* Cross-sector-boundary read (bytes 504..519 spans offset 512). */
	memset(boundary, 0, sizeof(boundary));
	read_count = libvmdk_handle_read_buffer_at_offset(handle, boundary,
	                                                   sizeof(boundary),
	                                                   504, &error);
	CHECK(read_count == (ssize_t)sizeof(boundary),
	      "cross-sector-boundary read returns 16 bytes at 504");
	CHECK(memcmp(boundary, image + 504, sizeof(boundary)) == 0,
	      "cross-sector bytes match image 504..519");

	/* Tail read: last 64 bytes of the media. */
	memset(tail_window, 0, sizeof(tail_window));
	read_count = libvmdk_handle_read_buffer_at_offset(
	    handle, tail_window, sizeof(tail_window), IMAGE_SIZE - 64, &error);
	CHECK(read_count == (ssize_t)sizeof(tail_window),
	      "tail read returns 64 bytes at 8128");
	CHECK(memcmp(tail_window, image + IMAGE_SIZE - 64,
	             sizeof(tail_window)) == 0,
	      "tail bytes match image 8128..8191");

	/* Seek / offset advance. */
	offset = libvmdk_handle_seek_offset(handle, 4096, SEEK_SET, &error);
	CHECK(offset == (off64_t)4096, "seek_offset(4096) == 4096");
	result = libvmdk_handle_get_offset(handle, &offset, &error);
	CHECK(result == 1 && offset == (off64_t)4096, "get_offset() == 4096");
	memset(boundary, 0, sizeof(boundary));
	read_count = libvmdk_handle_read_buffer(handle, boundary,
	                                         sizeof(boundary), &error);
	CHECK(read_count == (ssize_t)sizeof(boundary) &&
	          memcmp(boundary, image + 4096, sizeof(boundary)) == 0,
	      "post-seek read matches image bytes 4096..4111");

	/* Signal abort + lifecycle. */
	result = libvmdk_handle_signal_abort(handle, &error);
	CHECK(result == 1, "handle_signal_abort succeeds");
	result = libvmdk_handle_close(handle, &error);
	CHECK(result == 0, "handle_close returns 0");
	result = libvmdk_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free succeeds");

	(void)unlink(descriptor_path);
	(void)unlink(data_path);

	if (failures == 0) {
		printf("== libvmdk OHOS consumer test: %d assertions,"
		       " all PASS ==\n",
		       assertions);
	} else {
		printf("== libvmdk OHOS consumer test: %d/%d FAILED ==\n",
		       failures, assertions);
	}
	return failures == 0 ? 0 : 1;
}
