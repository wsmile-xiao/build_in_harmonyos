/* libvmdk 20240510 consumer test — generic (installed package only)
 *
 * Exercises the public API of the *installed* package (headers + shared
 * library): version string, access flags, codepage handling, VMDK signature
 * detection (positive/negative/error), and a full read round trip over a
 * self-synthesized "monolithicFlat" VMDK (descriptor + flat extent data
 * written by this test): open → open_extent_data_files → media size →
 * disk type → content identifiers → full/boundary reads → offset/seek →
 * EOF semantics → close/free plus the error paths of handle_open().
 *
 * Descriptor form note: libvmdk's descriptor parser matches the VMDK
 * specification's camelCase createType values ("monolithicFlat"); the
 * space-separated VMware spelling ("monolithic flat") parses as metadata
 * but leaves the disk type UNDEFINED and extent initialization rejects it
 * (device probe: "unsupported disk type").
 *
 * Assertions here are not platform specific; the OHOS specific round trip
 * (TMPDIR semantics) lives in test_ohos.c.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libvmdk.h>
#include <libvmdk/codepage.h>

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
#define MARKER "VMDK-CONSUMER-MARKER-0123456789"

static const char *descriptor_text =
    "# Disk DescriptorFile\n"
    "version=1\n"
    "CID=fffffffe\n"
    "parentCID=ffffffff\n"
    "createType=\"monolithicFlat\"\n"
    "\n"
    "# Extent description\n"
    "RW 16 FLAT \"vmdk_consumer_data.vmdk\" 0\n"
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
		buffer[index] = (uint8_t)(index * 7 + (index >> 5));
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
	uint8_t small_buffer[64];
	const char *version = NULL;
	char descriptor_path[] = "vmdk_consumer_desc.vmdk";
	char error_string[4096];  /* conan test cwd 路径长，双层 backtrace 超 512B 时 sprint 返 -1（round-2 实测） */
	size64_t media_size = 0;
	off64_t offset = -1;
	uint32_t content_identifier = 0;
	uint32_t parent_content_identifier = 0;
	int access_flags = -1;
	int codepage = -1;
	int disk_type = -1;
	int result = -1;
	ssize_t read_count = 0;

	printf("== libvmdk generic consumer test ==\n");

	/* Version string: upstream release version (not the Conan ref). */
	version = libvmdk_get_version();
	CHECK(version != NULL, "libvmdk_get_version() returns non-NULL");
	CHECK(version != NULL && strcmp(version, "20240510") == 0,
	      "version string is 20240510");

	/* Read access flags. */
	access_flags = libvmdk_get_access_flags_read();
	CHECK(access_flags == LIBVMDK_ACCESS_FLAG_READ,
	      "access_flags_read == LIBVMDK_ACCESS_FLAG_READ (0x01)");

	/* Codepage handling: ASCII is a valid value, read-back must match. */
	result = libvmdk_set_codepage(LIBVMDK_CODEPAGE_ASCII, &error);
	CHECK(result == 1, "libvmdk_set_codepage(ASCII) succeeds");
	result = libvmdk_get_codepage(&codepage, &error);
	CHECK(result == 1 && codepage == LIBVMDK_CODEPAGE_ASCII,
	      "get_codepage() reads back ASCII (20127)");
	result = libvmdk_set_codepage(-42, &error);
	CHECK(result == -1, "set_codepage(-42) fails");
	CHECK(error != NULL, "set_codepage(-42) sets error");
	if (error != NULL) {
		libvmdk_error_free(&error);
	}
	result = libvmdk_set_codepage(0, &error);
	codepage = -1;
	result = libvmdk_get_codepage(&codepage, &error);
	CHECK(result == 1 && codepage == 0,
	      "codepage 0 (UTF-8 mode) round trip");

	/* Synthesize a monolithicFlat VMDK pair (descriptor + flat extent). */
	fill_pattern(image, IMAGE_SIZE);
	CHECK(write_file(descriptor_path, descriptor_text,
	                 strlen(descriptor_text)) == 0,
	      "descriptor file written");
	CHECK(write_file("vmdk_consumer_data.vmdk", image, IMAGE_SIZE) == 0,
	      "flat extent data file (8 KiB) written");

	/* Signature detection: positive, negative and error paths. */
	result = libvmdk_check_file_signature(descriptor_path, &error);
	CHECK(result == 1, "check_file_signature(descriptor) == 1");
	result = libvmdk_check_file_signature("vmdk_consumer_data.vmdk",
	                                      &error);
	CHECK(result == 0, "check_file_signature(flat data file) == 0");
	result = libvmdk_check_file_signature("no-such-file.vmdk", &error);
	CHECK(result == -1, "check_file_signature(missing) == -1");
	CHECK(error != NULL, "check_file_signature(missing) sets error");
	if (error != NULL) {
		libvmdk_error_free(&error);
	}

	/* Error path: opening a non-existing file must fail and set error. */
	result = libvmdk_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize succeeds");
	result = libvmdk_handle_open(handle, "no-such-file.vmdk",
	                             LIBVMDK_ACCESS_FLAG_READ, &error);
	CHECK(result == -1, "handle_open(non-existing) returns -1");
	CHECK(error != NULL, "handle_open(non-existing) sets error");
	if (error != NULL) {
		result = libvmdk_error_backtrace_sprint(error, error_string,
		                                        sizeof(error_string));
		CHECK(result > 0, "error_backtrace_sprint() yields a message");
		libvmdk_error_free(&error);
	}
	result = libvmdk_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free after failed open");

	/* Happy path: open the synthesized VMDK and read it back. */
	result = libvmdk_handle_initialize(&handle, &error);
	CHECK(result == 1 && handle != NULL, "handle_initialize (2nd)");
	result = libvmdk_handle_open(handle, descriptor_path,
	                             LIBVMDK_ACCESS_FLAG_READ, &error);
	CHECK(result == 1, "handle_open(descriptor) succeeds");
	CHECK(error == NULL, "handle_open(descriptor) sets no error");
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
	result = libvmdk_handle_get_parent_content_identifier(
	    handle, &parent_content_identifier, &error);
	CHECK(result == 1 && parent_content_identifier == 0xffffffff,
	      "parent content identifier is 0xffffffff");

	/* Full image read-back. */
	memset(read_buffer, 0, IMAGE_SIZE);
	read_count = libvmdk_handle_read_buffer(handle, read_buffer,
	                                         IMAGE_SIZE, &error);
	CHECK(read_count == (ssize_t)IMAGE_SIZE, "full image read (8192)");
	CHECK(memcmp(read_buffer, image, IMAGE_SIZE) == 0,
	      "read-back pattern matches");
	CHECK(memcmp(read_buffer + 64, MARKER, sizeof(MARKER) - 1) == 0,
	      "marker present at offset 64");

	/* Random-access read at a sector boundary. */
	memset(small_buffer, 0, sizeof(small_buffer));
	read_count = libvmdk_handle_read_buffer_at_offset(
	    handle, small_buffer, sizeof(small_buffer), 512, &error);
	CHECK(read_count == (ssize_t)sizeof(small_buffer),
	      "read_buffer_at_offset(512, 64) returns 64");
	CHECK(memcmp(small_buffer, image + 512, sizeof(small_buffer)) == 0,
	      "read-at-offset bytes match image 512..575");

	/* Seek / offset accounting. */
	offset = libvmdk_handle_seek_offset(handle, 4096, SEEK_SET, &error);
	CHECK(offset == (off64_t)4096, "seek_offset(4096, SEEK_SET) == 4096");
	result = libvmdk_handle_get_offset(handle, &offset, &error);
	CHECK(result == 1 && offset == (off64_t)4096,
	      "get_offset() reads back 4096");
	memset(small_buffer, 0, sizeof(small_buffer));
	read_count = libvmdk_handle_read_buffer(handle, small_buffer,
	                                         sizeof(small_buffer), &error);
	CHECK(read_count == (ssize_t)sizeof(small_buffer) &&
	          memcmp(small_buffer, image + 4096,
	                 sizeof(small_buffer)) == 0,
	      "post-seek read matches image bytes 4096..4159");

	/* EOF semantics: seek to end, read must yield 0 bytes, no error. */
	offset = libvmdk_handle_seek_offset(handle, 0, SEEK_END, &error);
	CHECK(offset == (off64_t)IMAGE_SIZE, "seek_offset(0, SEEK_END) == 8192");
	memset(small_buffer, 0, sizeof(small_buffer));
	read_count = libvmdk_handle_read_buffer(handle, small_buffer,
	                                         sizeof(small_buffer), &error);
	CHECK(read_count == 0, "read at EOF returns 0 bytes");
	CHECK(error == NULL, "read at EOF sets no error");

	/* Signal abort + lifecycle. */
	result = libvmdk_handle_signal_abort(handle, &error);
	CHECK(result == 1, "handle_signal_abort succeeds");
	result = libvmdk_handle_close(handle, &error);
	CHECK(result == 0, "handle_close returns 0");
	result = libvmdk_handle_free(&handle, &error);
	CHECK(result == 1 && handle == NULL, "handle_free succeeds");

	(void)unlink(descriptor_path);
	(void)unlink("vmdk_consumer_data.vmdk");

	if (failures == 0) {
		printf("== libvmdk generic consumer test: %d assertions,"
		       " all PASS ==\n",
		       assertions);
	} else {
		printf("== libvmdk generic consumer test: %d/%d FAILED ==\n",
		       failures, assertions);
	}
	return failures == 0 ? 0 : 1;
}
