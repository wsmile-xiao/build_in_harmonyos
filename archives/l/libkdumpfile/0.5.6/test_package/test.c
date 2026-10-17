/*
 * test_package consumer test for libkdumpfile 0.5.6.
 *
 * Exercises the public API as a real consumer would:
 *   kdump_new / kdump_open_fdset / kdump_get_string_attr /
 *   kdump_get_number_attr / kdump_get_err / kdump_free
 *
 * Generates a minimal valid diskdump image (header layout per upstream
 * disk_dump_header_32 + try_header semantics), opens it through the
 * public API, and verifies the attribute dictionary is populated —
 * proving compile + link + run against the packaged library (R34).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdint.h>
#include <errno.h>
#include <sys/stat.h>
#include <libkdumpfile/kdumpfile.h>

/* offsets in the 32-bit disk_dump_header (packed, see diskdump.c) */
#define OFF_SIGNATURE      0
#define OFF_HEADER_VERSION 8
#define OFF_BLOCK_SIZE     416
#define OFF_SUBHDR_SIZE    420
#define OFF_BITMAP_BLOCKS  424
#define OFF_MAX_MAPNR      428

static void
w32(unsigned char *p, size_t off, uint32_t v)
{
	p[off] = (unsigned char)(v & 0xff);
	p[off+1] = (unsigned char)((v >> 8) & 0xff);
	p[off+2] = (unsigned char)((v >> 16) & 0xff);
	p[off+3] = (unsigned char)((v >> 24) & 0xff);
}

/* Minimal valid empty diskdump image:
 * - signature "DISKDUMP"
 * - header_version 0 (no sub-header)
 * - block_size 4096, sub_hdr_size 0, bitmap_blocks 1, max_mapnr 4096
 *   (try_header: 8*1*4096 = 32768 bits >= 4096, and > 32768/2)
 */
static int
write_diskdump(const char *path)
{
	unsigned char buf[8192];

	/* ensure the parent directory exists (CTest runs in a fresh build dir);
	 * a single mkdir level suffices for the default path "out/consumer.dump" */
	if (strrchr(path, '/')) {
		char dir[256];
		size_t n = (size_t)(strrchr(path, '/') - path);
		if (n >= sizeof dir)
			return -1;
		memcpy(dir, path, n);
		dir[n] = '\0';
		if (mkdir(dir, 0755) != 0 && errno != EEXIST) {
			perror("mkdir");
			return -1;
		}
	}

	memset(buf, 0, sizeof buf);
	memcpy(buf + OFF_SIGNATURE, "DISKDUMP", 8);
	w32(buf, OFF_HEADER_VERSION, 0);
	w32(buf, OFF_BLOCK_SIZE, 4096);
	w32(buf, OFF_SUBHDR_SIZE, 0);
	w32(buf, OFF_BITMAP_BLOCKS, 1);
	w32(buf, OFF_MAX_MAPNR, 4096);

	int fd = open(path, O_CREAT | O_TRUNC | O_WRONLY, 0644);
	if (fd < 0) {
		perror("open");
		return -1;
	}
	if (write(fd, buf, sizeof buf) != (ssize_t)sizeof buf) {
		perror("write");
		close(fd);
		return -1;
	}
	close(fd);
	return 0;
}

int
main(int argc, char **argv)
{
	const char *path = "out/consumer.dump";
	kdump_status st;
	kdump_num_t ptr_size;
	const char *fstr = NULL;

	if (argc > 1)
		path = argv[1];

	if (write_diskdump(path)) {
		fprintf(stderr, "Cannot create dump image\n");
		return 1;
	}

	kdump_ctx_t *ctx = kdump_new();
	if (!ctx) {
		fprintf(stderr, "kdump_new() failed\n");
		return 1;
	}

	int fd = open(path, O_RDONLY);
	if (fd < 0) {
		perror("open dump");
		kdump_free(ctx);
		return 1;
	}

	st = kdump_open_fdset(ctx, 1, &fd);
	close(fd);
	if (st != KDUMP_OK) {
		const char *err = kdump_get_err(ctx);
		fprintf(stderr, "kdump_open_fdset() failed: %s\n",
			err ? err : "(no error set)");
		kdump_free(ctx);
		return 1;
	}

	/* file.format is a string attribute set by format detection */
	st = kdump_get_string_attr(ctx, "file.format", &fstr);
	if (st != KDUMP_OK) {
		const char *err = kdump_get_err(ctx);
		fprintf(stderr, "kdump_get_string_attr(file.format) failed: %s\n",
			err ? err : "(no error set)");
		kdump_free(ctx);
		return 1;
	}
	printf("file.format = \"%s\" (OK)\n", fstr ? fstr : "(null)");

	/* file.set.number is a numeric attribute (dump file set) */
	st = kdump_get_number_attr(ctx, "file.set.number", &ptr_size);
	if (st != KDUMP_OK) {
		const char *err = kdump_get_err(ctx);
		fprintf(stderr, "kdump_get_number_attr(file.set.number) failed: %s\n",
			err ? err : "(no error set)");
		kdump_free(ctx);
		return 1;
	}
	printf("file.set.number = %llu (OK)\n",
	       (unsigned long long)ptr_size);

	kdump_free(ctx);
	printf("libkdumpfile consumer test PASSED\n");
	return 0;
}
