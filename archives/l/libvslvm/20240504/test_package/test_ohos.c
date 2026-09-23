/* libvslvm 20240504 consumer test — HarmonyOS specific
 *
 * Builds a *fully valid* LVM2 physical volume image (LABELONE label with
 * pv_header + data/metadata area descriptors + metadata area header with a raw
 * location descriptor + LVM2 metadata text with one volume group, one physical
 * volume and one linear logical volume; all weak CRC-32 checksums correct)
 * inside $TMPDIR on the device and reads it back through the installed libvslvm
 * public API.  This covers the platform semantics that only exist on OHOS: the
 * compile target itself, the TMPDIR contract (/tmp is read-only on HarmonyOS)
 * and a real on-disk round trip performed under that TMPDIR.
 *
 * The public API of libvslvm exposes the volume *metadata* chain
 * (signature → handle → volume group → physical/logical volumes → segments →
 * stripes); the logical volume data read path is internal to the library
 * (libvslvm_logical_volume_read_chunk_data takes libfdata vector internals),
 * so the deepest consumer-reachable assertions are the metadata chain below.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libvslvm.h>

#if !defined(__OHOS__)
#error "test_ohos.c must be compiled for the OHOS target (__OHOS__)"
#endif

#define SECTOR_SIZE 512
#define IMAGE_SIZE 16384          /* 32 sectors */
/* LVM2 pvcreate writes the label into one of the first 4 sectors and defaults
 * to labelsector=1.  libvslvm mirrors this: the handle open scans label
 * offsets 0/512/1024/1536, but check_volume_signature_file_io_handle probes
 * the fixed offset 512 only — so the synthesized label lives at 512.
 */
#define LABEL_OFFSET 512
#define METADATA_AREA_OFFSET 4096 /* 1 MiB is the LVM2 default, 4 KiB is valid */
#define METADATA_TEXT_OFFSET 4608 /* metadata area + 512-byte header */
#define DATA_AREA_OFFSET 8192
#define VG_EXTENT_SIZE 8192
#define WEAK_CRC32_INITIAL 0xf597a6cfUL
#define MARKER "LVM2-OHOS-TEST-DATA"

static const char volume_group_name[] = "vg0";
/* LVM2 UUIDs are 38 characters (6-4-4-4-4-4-6 with dashes); the parsers
 * of libvslvm require identifier_size == 39 including the terminator. */
static const char volume_group_id[] = "AbCdEf-GhIj-KlMn-OpQr-StUv-WxYz-012345";
static const char physical_volume_name[] = "pv0";
static const char physical_volume_id[] = "PqRsTu-VwXy-Z012-3456-AbCd-EfGh-IjKlMn";
static const char physical_volume_label_id[32] = "aBcDeFgHiJkLmNoPqRsTuVwXyZ012345";
static const char physical_volume_device[] = "/dev/ohos-lvm-test";
static const char logical_volume_name[] = "lv_data";
static const char logical_volume_id[] = "MnOpQr-StUv-WxYz-0123-4567-89Ab-CdEfGh";

static const char metadata_text[] =
	"vg0 {\n"
	"id = \"AbCdEf-GhIj-KlMn-OpQr-StUv-WxYz-012345\"\n"
	"seqno = 1\n"
	"status = [\"RESIZEABLE\", \"READ\", \"WRITE\"]\n"
	"flags = []\n"
	"extent_size = 8192\n"
	"max_lv = 255\n"
	"max_pv = 255\n"
	"metadata_copies = 0\n"
	"\n"
	"physical_volumes {\n"
	"\n"
	"pv0 {\n"
	"id = \"PqRsTu-VwXy-Z012-3456-AbCd-EfGh-IjKlMn\"\n"
	"device = \"/dev/ohos-lvm-test\"\n"
	"status = [\"ALLOCATABLE\"]\n"
	"flags = []\n"
	"dev_size = 32\n"
	"pe_start = 8192\n"
	"pe_count = 1\n"
	"}\n"
	"}\n"
	"\n"
	"logical_volumes {\n"
	"\n"
	"lv_data {\n"
	"id = \"MnOpQr-StUv-WxYz-0123-4567-89Ab-CdEfGh\"\n"
	"status = [\"READ\", \"WRITE\", \"VISIBLE\"]\n"
	"flags = []\n"
	"segment_count = 1\n"
	"\n"
	"segment1 {\n"
	"start_extent = 0\n"
	"extent_count = 1\n"
	"type = \"striped\"\n"
	"stripe_count = 1\n"
	"\n"
	"stripes = [\n"
	"\"pv0\", 0\n"
	"]\n"
	"}\n"
	"}\n"
	"}\n"
	"}\n";

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
put_uint32_le(uint8_t *buffer, uint32_t value)
{
	buffer[0] = (uint8_t)(value & 0xff);
	buffer[1] = (uint8_t)((value >> 8) & 0xff);
	buffer[2] = (uint8_t)((value >> 16) & 0xff);
	buffer[3] = (uint8_t)((value >> 24) & 0xff);
}

static void
put_uint64_le(uint8_t *buffer, uint64_t value)
{
	put_uint32_le(buffer, (uint32_t)(value & 0xffffffffULL));
	put_uint32_le(buffer + 4, (uint32_t)(value >> 32));
}

/* The LVM2 "weak" CRC-32: reflected CRC-32 (polynomial 0xedb88320) with a
 * non-standard initial value and no final XOR (see the bundled
 * libvslvm_checksum.c: libvslvm_checksum_calculate_weak_crc32). */
static uint32_t
weak_crc32(const uint8_t *buffer, size_t size)
{
	static uint32_t table[256];
	static int table_computed = 0;
	uint32_t checksum = WEAK_CRC32_INITIAL;
	size_t index = 0;

	if (table_computed == 0) {
		uint32_t value = 0;
		int bit = 0;

		for (value = 0; value < 256; value++) {
			uint32_t entry = value;

			for (bit = 0; bit < 8; bit++) {
				if (entry & 1UL) {
					entry = 0xedb88320UL ^ (entry >> 1);
				} else {
					entry >>= 1;
				}
			}
			table[value] = entry;
		}
		table_computed = 1;
	}
	for (index = 0; index < size; index++) {
		checksum = table[(checksum ^ buffer[index]) & 0xffUL] ^
		           (checksum >> 8);
	}
	return checksum;
}

static int
build_lvm2_image(const char *path)
{
	uint8_t image[IMAGE_SIZE];
	size_t text_size = sizeof(metadata_text) - 1;

	memset(image, 0, sizeof(image));

	/* ── sector 1 (LVM2 default labelsector): physical volume label ──
	 * The handle open scans label offsets 0/512/1024/1536, but
	 * check_volume_signature_file_io_handle probes the fixed offset 512
	 * only, so the label goes here to satisfy both paths. */
	memcpy(image + LABEL_OFFSET + 0, "LABELONE", 8);
	put_uint64_le(image + LABEL_OFFSET + 8, 1); /* label sector number */
	put_uint32_le(image + LABEL_OFFSET + 20, 32);
	memcpy(image + LABEL_OFFSET + 24, "LVM2 001", 8);

	/* pv_header: 32-byte identifier + volume size in sectors */
	memcpy(image + LABEL_OFFSET + 32, physical_volume_label_id, 32);
	put_uint64_le(image + LABEL_OFFSET + 64, IMAGE_SIZE / SECTOR_SIZE);

	/* data area descriptor list: one entry + zero terminator */
	put_uint64_le(image + LABEL_OFFSET + 72, DATA_AREA_OFFSET);
	put_uint64_le(image + LABEL_OFFSET + 80,
	              IMAGE_SIZE - DATA_AREA_OFFSET);
	/* bytes LABEL_OFFSET+88..103 stay zero (terminator) */

	/* metadata area descriptor list: one entry + zero terminator */
	put_uint64_le(image + LABEL_OFFSET + 104, METADATA_AREA_OFFSET);
	put_uint64_le(image + LABEL_OFFSET + 112,
	              METADATA_TEXT_OFFSET - METADATA_AREA_OFFSET);

	/* label checksum covers bytes LABEL_OFFSET+20 .. +512 and must be
	 * computed after every other label field is in place */
	put_uint32_le(image + LABEL_OFFSET + 16,
	              weak_crc32(image + LABEL_OFFSET + 20,
	                         SECTOR_SIZE - 20));

	/* ── metadata area header (512 bytes) ── */
	memcpy(image + METADATA_AREA_OFFSET + 4,
	       " LVM2 x[5A%r0N*>", 16);
	put_uint32_le(image + METADATA_AREA_OFFSET + 20, 1); /* version */
	put_uint64_le(image + METADATA_AREA_OFFSET + 24, 512);
	put_uint64_le(image + METADATA_AREA_OFFSET + 32,
	              METADATA_TEXT_OFFSET - METADATA_AREA_OFFSET - 512);
	/* raw location descriptor: offset is RELATIVE to the metadata area
	 * start (the library stores file_offset + offset when parsing), then
	 * size, text checksum, flags=0 */
	put_uint64_le(image + METADATA_AREA_OFFSET + 40,
	              (uint64_t) (METADATA_TEXT_OFFSET - METADATA_AREA_OFFSET));
	put_uint64_le(image + METADATA_AREA_OFFSET + 48, text_size);
	put_uint32_le(image + METADATA_AREA_OFFSET + 56,
	              weak_crc32((const uint8_t *) metadata_text, text_size));
	put_uint32_le(image + METADATA_AREA_OFFSET + 60, 0);
	/* header checksum lives at +0 and covers bytes +4..+512 */
	put_uint32_le(image + METADATA_AREA_OFFSET + 0,
	              weak_crc32(image + METADATA_AREA_OFFSET + 4,
	                         SECTOR_SIZE - 4));

	/* ── metadata text ── */
	memcpy(image + METADATA_TEXT_OFFSET, metadata_text, text_size);

	/* ── data area (public API is metadata-only; marker for hexdump) ── */
	memcpy(image + DATA_AREA_OFFSET, MARKER, sizeof(MARKER) - 1);

	{
		FILE *stream = fopen(path, "wb");
		size_t written = 0;

		if (stream == NULL) {
			return -1;
		}
		written = fwrite(image, 1, sizeof(image), stream);
		fclose(stream);
		return written == sizeof(image) ? 0 : -1;
	}
}

int
main(void)
{
	libvslvm_error_t *error = NULL;
	libvslvm_handle_t *handle = NULL;
	libvslvm_volume_group_t *volume_group = NULL;
	libvslvm_physical_volume_t *physical_volume = NULL;
	libvslvm_logical_volume_t *logical_volume = NULL;
	libvslvm_segment_t *segment = NULL;
	libvslvm_stripe_t *stripe = NULL;
	char image_path[512];
	char name_buffer[128];
	char *tmpdir = NULL;
	uint32_t sequence_number = 0;
	size64_t extent_size = 0;
	size64_t segment_size = 0;
	off64_t segment_offset = 0;
	int number_of_physical_volumes = 0;
	int number_of_logical_volumes = 0;
	int number_of_segments = 0;
	int number_of_stripes = 0;
	int result = 0;

	printf("== libvslvm HarmonyOS specific consumer test ==\n");

	/* ── TMPDIR contract: /tmp is read-only on HarmonyOS ── */
	tmpdir = getenv("TMPDIR");
	CHECK(tmpdir != NULL, "TMPDIR is set");
	CHECK(tmpdir != NULL && strcmp(tmpdir, "/tmp") != 0,
	      "TMPDIR is not the read-only /tmp");
	CHECK(tmpdir != NULL && access(tmpdir, W_OK) == 0,
	      "TMPDIR is writable");
	snprintf(image_path, sizeof(image_path), "%s/libvslvm_test.img",
	         tmpdir != NULL ? tmpdir : ".");

	/* ── build the LVM2 image ── */
	(void) unlink(image_path);
	result = build_lvm2_image(image_path);
	CHECK(result == 0, "LVM2 image written under TMPDIR");
	CHECK(access(image_path, R_OK) == 0, "LVM2 image is readable");

	/* ── signature detection ── */
	error = NULL;
	result = libvslvm_check_volume_signature(image_path, &error);
	CHECK(result == 1, "check_volume_signature(image) returns 1 (found)");
	if (error != NULL) {
		libvslvm_error_free(&error);
	}

	/* ── open the volume ── */
	CHECK(libvslvm_handle_initialize(&handle, NULL) == 1 && handle != NULL,
	      "handle_initialize() succeeds");
	error = NULL;
	result = libvslvm_handle_open(handle, image_path, LIBVSLVM_OPEN_READ,
	                              &error);
	if (result != 1 && error != NULL) {
		char open_error[512];

		if (libvslvm_error_sprint(error, open_error,
		                          sizeof(open_error)) > 0) {
			printf("  [INFO] handle_open error: %s\n", open_error);
		}
		libvslvm_error_backtrace_fprint(error, stdout);
	}
	CHECK(result == 1, "handle_open(image) succeeds");
	if (error != NULL) {
		libvslvm_error_free(&error);
	}

	/* ── volume group ── */
	CHECK(libvslvm_handle_get_volume_group(handle, &volume_group,
	                                       NULL) == 1,
	      "handle_get_volume_group() succeeds");
	result = libvslvm_volume_group_get_name(volume_group, name_buffer,
	                                        sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, volume_group_name) == 0,
	      "volume group name is the synthesized one");
	result = libvslvm_volume_group_get_identifier(
		volume_group, name_buffer, sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, volume_group_id) == 0,
	      "volume group identifier matches the metadata text");
	CHECK(libvslvm_volume_group_get_sequence_number(volume_group,
	                                                &sequence_number,
	                                                NULL) == 1 &&
	      sequence_number == 1,
	      "volume group sequence number is 1");
	result = libvslvm_volume_group_get_extent_size(volume_group, &extent_size,
	                                             NULL);
	printf("  [INFO] extent_size rc=%d value=%llu\n", result,
	       (unsigned long long) extent_size);
	/* the volume group parser stores the metadata "extent_size" value
	 * multiplied by 512 (8192 -> 4194304) */
	CHECK(result == 1 &&
	      extent_size == (size64_t) VG_EXTENT_SIZE * 512,
	      "volume group extent size is 8192 sectors (4194304 bytes)");

	/* ── physical volume ── */
	CHECK(libvslvm_volume_group_get_number_of_physical_volumes(
		      volume_group, &number_of_physical_volumes,
		      NULL) == 1 &&
	      number_of_physical_volumes == 1,
	      "volume group has exactly 1 physical volume");
	CHECK(libvslvm_volume_group_get_physical_volume(
		      volume_group, 0, &physical_volume, NULL) == 1,
	      "get_physical_volume(0) succeeds");
	result = libvslvm_physical_volume_get_name(
		physical_volume, name_buffer, sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, physical_volume_name) == 0,
	      "physical volume name is pv0");
	result = libvslvm_physical_volume_get_identifier(
		physical_volume, name_buffer, sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, physical_volume_id) == 0,
	      "physical volume identifier matches the metadata text");
	result = libvslvm_physical_volume_get_device_path(
		physical_volume, name_buffer, sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, physical_volume_device) == 0,
	      "physical volume device path matches the metadata text");
	/* ── logical volume → segment → stripe ── */
	CHECK(libvslvm_volume_group_get_number_of_logical_volumes(
		      volume_group, &number_of_logical_volumes, NULL) == 1 &&
	      number_of_logical_volumes == 1,
	      "volume group has exactly 1 logical volume");
	CHECK(libvslvm_volume_group_get_logical_volume(
		      volume_group, 0, &logical_volume, NULL) == 1,
	      "get_logical_volume(0) succeeds");
	result = libvslvm_logical_volume_get_name(
		logical_volume, name_buffer, sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, logical_volume_name) == 0,
	      "logical volume name is lv_data");
	result = libvslvm_logical_volume_get_identifier(
		logical_volume, name_buffer, sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, logical_volume_id) == 0,
	      "logical volume identifier matches the metadata text");
	CHECK(libvslvm_logical_volume_get_number_of_segments(
		      logical_volume, &number_of_segments, NULL) == 1 &&
	      number_of_segments == 1,
	      "logical volume has exactly 1 segment");
	CHECK(libvslvm_logical_volume_get_segment(
		      logical_volume, 0, &segment, NULL) == 1,
	      "get_segment(0) succeeds");
	CHECK(libvslvm_segment_get_offset(segment, &segment_offset, NULL) == 1 &&
	      segment_offset == 0,
	      "segment offset is start_extent * extent_size = 0");
	result = libvslvm_segment_get_size(segment, &segment_size, NULL);
	printf("  [INFO] segment_size rc=%d value=%llu\n", result,
	       (unsigned long long) segment_size);
	CHECK(result == 1 &&
	      segment_size == (size64_t) VG_EXTENT_SIZE * 512,
	      "segment size is extent_count * extent_size = 4194304");
	CHECK(libvslvm_segment_get_number_of_stripes(
		      segment, &number_of_stripes, NULL) == 1 &&
	      number_of_stripes == 1,
	      "segment has exactly 1 stripe");
	CHECK(libvslvm_segment_get_stripe(segment, 0, &stripe, NULL) == 1,
	      "get_stripe(0) succeeds");
	result = libvslvm_stripe_get_physical_volume_name(
		stripe, name_buffer, sizeof(name_buffer), NULL);
	name_buffer[sizeof(name_buffer) - 1] = '\0';
	CHECK(result == 1 &&
	      strcmp(name_buffer, physical_volume_name) == 0,
	      "stripe points at physical volume pv0");

	/* ── close and clean up ── */
	CHECK(libvslvm_handle_close(handle, NULL) == 0, "handle_close() succeeds");
	CHECK(libvslvm_handle_free(&handle, NULL) == 1 && handle == NULL,
	      "handle_free() succeeds");
	(void) unlink(image_path);

	printf("== %d assertions, %d failures (LVM2 image round trip under "
	       "TMPDIR) ==\n",
	       assertions, failures);

	if (failures > 0) {
		return 1;
	}
	return 0;
}
