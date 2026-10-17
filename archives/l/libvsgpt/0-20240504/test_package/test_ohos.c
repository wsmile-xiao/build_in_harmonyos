/* libvsgpt 0-20240504 consumer test — HarmonyOS specific
 *
 * Builds a *fully valid* GPT disk image (protective MBR + primary GPT header +
 * 128 partition entries + backup entries + backup header, all CRC-32 fields
 * correct) inside $TMPDIR on the device and reads it back through the installed
 * libvsgpt public API.  This covers the platform semantics that only exist on
 * OHOS: the compile target itself, the TMPDIR contract (/tmp is read-only on
 * HarmonyOS) and a real on-disk round trip performed under that TMPDIR.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libvsgpt.h>

#if !defined(__OHOS__)
#error "test_ohos.c must be compiled for the OHOS target (__OHOS__)"
#endif

#define SECTOR_SIZE 512
#define TOTAL_SECTORS 4096 /* 2 MiB image */
#define ENTRY_COUNT 128
#define ENTRY_SIZE 128
#define ENTRY_SECTORS ((ENTRY_COUNT * ENTRY_SIZE) / SECTOR_SIZE) /* 32 */
#define PRIMARY_HEADER_LBA 1
#define PRIMARY_ENTRIES_LBA 2
#define FIRST_USABLE_LBA (PRIMARY_ENTRIES_LBA + ENTRY_SECTORS) /* 34 */
#define BACKUP_HEADER_LBA (TOTAL_SECTORS - 1)                  /* 4095 */
#define BACKUP_ENTRIES_LBA (BACKUP_HEADER_LBA - ENTRY_SECTORS) /* 4063 */
#define LAST_USABLE_LBA (BACKUP_ENTRIES_LBA - 1)               /* 4062 */
#define PARTITION_FIRST_LBA 2048
#define PARTITION_LAST_LBA 3071
#define PARTITION_SECTORS (PARTITION_LAST_LBA - PARTITION_FIRST_LBA + 1)
#define MARKER "VSGPT-PARTITION-DATA"

/* GPT on-disk GUID byte order: 0FC63DAF-8483-4772-8E79-3D69D8477DE4
 * (Linux filesystem data) with the first three fields little-endian. */
static const uint8_t linux_filesystem_guid[16] = {
    0xaf, 0x3d, 0xc6, 0x0f, 0x83, 0x84, 0x72, 0x47,
    0x8e, 0x79, 0x3d, 0x69, 0xd8, 0x47, 0x7d, 0xe4};

static const uint8_t expected_disk_guid[16] = {
    0x44, 0x49, 0x53, 0x4b, 0x47, 0x50, 0x54, 0x00,
    0x90, 0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66};

static const uint8_t expected_partition_guid[16] = {
    0x53, 0x47, 0x56, 0x50, 0x54, 0x01, 0x40, 0x00,
    0x80, 0x00, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff};

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

static uint32_t
crc32_ieee(const uint8_t *buffer, size_t size)
{
	uint32_t crc = 0xffffffffUL;
	size_t index = 0;
	int bit = 0;

	for (index = 0; index < size; index++) {
		crc ^= buffer[index];
		for (bit = 0; bit < 8; bit++) {
			if (crc & 1) {
				crc = 0xedb88320UL ^ (crc >> 1);
			} else {
				crc = crc >> 1;
			}
		}
	}
	return crc ^ 0xffffffffUL;
}

/* Builds one GPT header of 92 bytes at the start of header_sector. */
static void
build_gpt_header(uint8_t *header_sector, uint64_t current_lba,
                 uint64_t backup_lba, uint64_t entries_lba,
                 const uint8_t *disk_guid, uint32_t entries_crc)
{
	memset(header_sector, 0, SECTOR_SIZE);
	memcpy(header_sector, "EFI PART", 8);
	put_uint32_le(header_sector + 8, 0x00010000UL); /* revision 1.0 */
	put_uint32_le(header_sector + 12, 92);          /* header size */
	put_uint32_le(header_sector + 16, 0);           /* CRC-32: filled below */
	put_uint32_le(header_sector + 20, 0);           /* reserved */
	put_uint64_le(header_sector + 24, current_lba);
	put_uint64_le(header_sector + 32, backup_lba);
	put_uint64_le(header_sector + 40, FIRST_USABLE_LBA);
	put_uint64_le(header_sector + 48, LAST_USABLE_LBA);
	memcpy(header_sector + 56, disk_guid, 16);
	put_uint64_le(header_sector + 72, entries_lba);
	put_uint32_le(header_sector + 80, ENTRY_COUNT);
	put_uint32_le(header_sector + 84, ENTRY_SIZE);
	put_uint32_le(header_sector + 88, entries_crc);
	put_uint32_le(header_sector + 16, crc32_ieee(header_sector, 92));
}

static int
write_gpt_image(const char *path)
{
	uint8_t sector[SECTOR_SIZE];
	uint8_t *entries = NULL;
	uint8_t *backup_entries = NULL;
	FILE *stream = NULL;
	uint32_t entries_crc = 0;
	size_t index = 0;
	int result = -1;

	entries = (uint8_t *)calloc(ENTRY_COUNT, ENTRY_SIZE);
	backup_entries = (uint8_t *)calloc(ENTRY_COUNT, ENTRY_SIZE);
	if (entries == NULL || backup_entries == NULL) {
		goto on_error;
	}
	/* entry 0: Linux filesystem data, LBA 2048..3071, name "VSGPTTEST" */
	memcpy(entries, linux_filesystem_guid, 16);
	memcpy(entries + 16, expected_partition_guid, 16);
	put_uint64_le(entries + 32, PARTITION_FIRST_LBA);
	put_uint64_le(entries + 40, PARTITION_LAST_LBA);
	put_uint64_le(entries + 48, 0); /* attributes */
	for (index = 0; index < 9; index++) {
		entries[56 + (index * 2)] = "VSGPTTEST"[index];
	}
	memcpy(backup_entries, entries, ENTRY_COUNT * ENTRY_SIZE);
	entries_crc = crc32_ieee(entries, ENTRY_COUNT * ENTRY_SIZE);

	stream = fopen(path, "wb");
	if (stream == NULL) {
		goto on_error;
	}
	/* LBA 0: protective MBR */
	memset(sector, 0, SECTOR_SIZE);
	sector[446 + 4] = 0xee; /* partition type: GPT protective */
	put_uint32_le(sector + 446 + 8, PRIMARY_HEADER_LBA);
	put_uint32_le(sector + 446 + 12, TOTAL_SECTORS - 1);
	sector[510] = 0x55;
	sector[511] = 0xaa;
	if (fwrite(sector, 1, SECTOR_SIZE, stream) != SECTOR_SIZE) {
		goto on_error;
	}
	/* LBA 1: primary GPT header */
	build_gpt_header(sector, PRIMARY_HEADER_LBA, BACKUP_HEADER_LBA,
	                 PRIMARY_ENTRIES_LBA, expected_disk_guid, entries_crc);
	if (fwrite(sector, 1, SECTOR_SIZE, stream) != SECTOR_SIZE) {
		goto on_error;
	}
	/* LBA 2..33: primary partition entry array */
	if (fwrite(entries, 1, ENTRY_COUNT * ENTRY_SIZE, stream) !=
	    (size_t)(ENTRY_COUNT * ENTRY_SIZE)) {
		goto on_error;
	}
	/* LBA 34..2047: unused, zero filled */
	memset(sector, 0, SECTOR_SIZE);
	for (index = FIRST_USABLE_LBA; index < PARTITION_FIRST_LBA; index++) {
		if (fwrite(sector, 1, SECTOR_SIZE, stream) != SECTOR_SIZE) {
			goto on_error;
		}
	}
	/* LBA 2048..3071: the partition payload with a recognisable marker */
	memset(sector, 0xab, SECTOR_SIZE);
	memcpy(sector, MARKER, sizeof(MARKER) - 1);
	for (index = 0; index < PARTITION_SECTORS; index++) {
		if (fwrite(sector, 1, SECTOR_SIZE, stream) != SECTOR_SIZE) {
			goto on_error;
		}
	}
	/* LBA 3072..4062: unused, zero filled */
	memset(sector, 0, SECTOR_SIZE);
	for (index = PARTITION_LAST_LBA + 1; index < BACKUP_ENTRIES_LBA;
	     index++) {
		if (fwrite(sector, 1, SECTOR_SIZE, stream) != SECTOR_SIZE) {
			goto on_error;
		}
	}
	/* LBA 4063..4094: backup partition entry array */
	if (fwrite(backup_entries, 1, ENTRY_COUNT * ENTRY_SIZE, stream) !=
	    (size_t)(ENTRY_COUNT * ENTRY_SIZE)) {
		goto on_error;
	}
	/* LBA 4095: backup GPT header */
	build_gpt_header(sector, BACKUP_HEADER_LBA, PRIMARY_HEADER_LBA,
	                 BACKUP_ENTRIES_LBA, expected_disk_guid, entries_crc);
	if (fwrite(sector, 1, SECTOR_SIZE, stream) != SECTOR_SIZE) {
		goto on_error;
	}
	if (fflush(stream) != 0) {
		goto on_error;
	}
	result = 0;

on_error:
	if (stream != NULL) {
		fclose(stream);
	}
	free(entries);
	free(backup_entries);
	return result;
}

int
main(void)
{
	libvsgpt_error_t *error = NULL;
	libvsgpt_volume_t *volume = NULL;
	libvsgpt_partition_t *partition = NULL;
	uint8_t guid_data[16];
	uint8_t buffer[SECTOR_SIZE];
	char image_path[512];
	char *tmpdir = NULL;
	uint32_t bytes_per_sector = 0;
	uint32_t entry_index = 0;
	int number_of_partitions = 0;
	off64_t volume_offset = -1;
	off64_t current_offset = -1;
	size64_t size = 0;
	ssize_t read_count = 0;
	FILE *stream = NULL;
	int result = 0;

	printf("== libvsgpt HarmonyOS consumer test ==\n");

	/* 1. compile target */
	CHECK(1, "compiled with __OHOS__ defined (OHOS target)");

	/* 2. TMPDIR contract: must be set, must not be the read-only /tmp and
	 * must be writable. */
	tmpdir = getenv("TMPDIR");
	CHECK(tmpdir != NULL && tmpdir[0] != '\0', "TMPDIR is set");
	CHECK(tmpdir != NULL && strcmp(tmpdir, "/tmp") != 0,
	      "TMPDIR is not the read-only /tmp");
	snprintf(image_path, sizeof(image_path), "%s/libvsgpt-ohos-%ld.img",
	         (tmpdir != NULL && tmpdir[0] != '\0') ? tmpdir : ".", (long)getpid());
	stream = fopen(image_path, "wb");
	CHECK(stream != NULL, "TMPDIR is writable (probe file created)");
	if (stream != NULL) {
		fclose(stream);
		unlink(image_path);
	} else {
		/* fall back to the build folder so the round trip can still run */
		snprintf(image_path, sizeof(image_path),
		         "libvsgpt-ohos-%ld.img", (long)getpid());
	}

	/* 3. synthesise a valid GPT image inside TMPDIR */
	CHECK(write_gpt_image(image_path) == 0,
	      "created a valid GPT image (2 MiB: MBR + primary GPT + entries + "
	      "backup entries + backup header) under TMPDIR");

	/* 4. signature detection on the installed library */
	error = NULL;
	result = libvsgpt_check_volume_signature(image_path, &error);
	CHECK(result == 1, "check_volume_signature() == 1 for the GPT image");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}

	/* 5. open the volume */
	error = NULL;
	result = libvsgpt_volume_initialize(&volume, &error);
	CHECK(result == 1 && volume != NULL, "libvsgpt_volume_initialize()");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}
	result = libvsgpt_volume_open(volume, image_path, LIBVSGPT_OPEN_READ,
	                              &error);
	CHECK(result == 1, "libvsgpt_volume_open() on the GPT image");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}

	/* 6. volume metadata */
	result = libvsgpt_volume_get_bytes_per_sector(volume, &bytes_per_sector,
	                                              &error);
	CHECK(result == 1 && bytes_per_sector == SECTOR_SIZE,
	      "libvsgpt_volume_get_bytes_per_sector() == 512");
	result = libvsgpt_volume_get_number_of_partitions(
	    volume, &number_of_partitions, &error);
	CHECK(result == 1 && number_of_partitions == 1,
	      "libvsgpt_volume_get_number_of_partitions() == 1 "
	      "(empty GPT entries are ignored)");
	memset(guid_data, 0, 16);
	result = libvsgpt_volume_get_disk_identifier(volume, guid_data, 16,
	                                             &error);
	CHECK(result == 1 && memcmp(guid_data, expected_disk_guid, 16) == 0,
	      "libvsgpt_volume_get_disk_identifier() returns the GPT disk GUID");

	/* 7. partition lookup: *_by_identifier / *_with_identifier take an
	 * *entry index* (uint32_t), not a GUID, despite the function names. */
	result = libvsgpt_volume_has_partition_with_identifier(volume, 0, &error);
	CHECK(result == 1,
	      "libvsgpt_volume_has_partition_with_identifier(volume, 0) == 1 "
	      "(argument is the entry index)");
	CHECK(libvsgpt_volume_has_partition_with_identifier(volume, 1, &error) ==
	          0,
	      "libvsgpt_volume_has_partition_with_identifier(volume, 1) == 0 "
	      "(empty entry is not a partition)");
	result = libvsgpt_volume_get_partition_by_identifier(volume, 0,
	                                                     &partition, &error);
	CHECK(result == 1 && partition != NULL,
	      "libvsgpt_volume_get_partition_by_identifier(volume, 0)");
	result = libvsgpt_partition_get_entry_index(partition, &entry_index,
	                                            &error);
	CHECK(result == 1 && entry_index == 0,
	      "libvsgpt_partition_get_entry_index() == 0");
	/* get_volume_offset() is the byte offset in the volume;
	 * get_offset() is the *current* read offset inside the partition. */
	result = libvsgpt_partition_get_volume_offset(partition, &volume_offset,
	                                              &error);
	CHECK(result == 1 &&
	          volume_offset == (off64_t)PARTITION_FIRST_LBA * SECTOR_SIZE,
	      "libvsgpt_partition_get_volume_offset() == 2048 * 512");
	result = libvsgpt_partition_get_offset(partition, &current_offset, &error);
	CHECK(result == 1 && current_offset == 0,
	      "libvsgpt_partition_get_offset() == 0 before reading "
	      "(current offset, not the volume offset)");
	result = libvsgpt_partition_get_size(partition, &size, &error);
	CHECK(result == 1 && size == (size64_t)PARTITION_SECTORS * SECTOR_SIZE,
	      "libvsgpt_partition_get_size() == 1024 * 512");
	memset(guid_data, 0, 16);
	result = libvsgpt_partition_get_identifier(partition, guid_data, 16,
	                                           &error);
	CHECK(result == 1 &&
	          memcmp(guid_data, expected_partition_guid, 16) == 0,
	      "libvsgpt_partition_get_identifier() returns the partition GUID");
	memset(guid_data, 0, 16);
	result = libvsgpt_partition_get_type_identifier(partition, guid_data, 16,
	                                                &error);
	CHECK(result == 1 &&
	          memcmp(guid_data, linux_filesystem_guid, 16) == 0,
	      "libvsgpt_partition_get_type_identifier() returns the GPT type GUID "
	      "(Linux filesystem data)");

	/* 8. read the payload back through the partition handle */
	memset(buffer, 0, SECTOR_SIZE);
	read_count = libvsgpt_partition_read_buffer(partition, buffer,
	                                            SECTOR_SIZE, &error);
	CHECK(read_count == SECTOR_SIZE,
	      "libvsgpt_partition_read_buffer() reads one sector");
	CHECK(memcmp(buffer, MARKER, sizeof(MARKER) - 1) == 0,
	      "partition payload marker read back from the image");
	CHECK(buffer[SECTOR_SIZE - 1] == 0xab,
	      "partition payload fill pattern read back from the image");
	result = libvsgpt_partition_get_offset(partition, &current_offset, &error);
	CHECK(result == 1 && current_offset == SECTOR_SIZE,
	      "libvsgpt_partition_get_offset() == 512 after reading one sector");

	/* 9. release */
	result = libvsgpt_partition_free(&partition, &error);
	CHECK(result == 1 && partition == NULL,
	      "libvsgpt_partition_free() releases the partition handle");
	result = libvsgpt_volume_close(volume, &error);
	CHECK(result == 0, "libvsgpt_volume_close() returns 0 on success");
	result = libvsgpt_volume_free(&volume, &error);
	CHECK(result == 1 && volume == NULL,
	      "libvsgpt_volume_free() releases the volume handle");
	if (error != NULL) {
		libvsgpt_error_free(&error);
		error = NULL;
	}

	/* 10. clean up the temp image */
	CHECK(unlink(image_path) == 0, "temporary GPT image removed from TMPDIR");

	if (failures != 0) {
		printf("%d of %d assertions FAILED\n", failures, assertions);
		return EXIT_FAILURE;
	}
	printf("%d assertions passed (GPT image round trip under TMPDIR)\n",
	       assertions);
	return EXIT_SUCCESS;
}
