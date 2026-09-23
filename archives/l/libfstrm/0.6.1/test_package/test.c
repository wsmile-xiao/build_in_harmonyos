/*
 * test_libfstrm — real round-trip test against the installed libfstrm API.
 *
 * Writes two data frames to a Frame Streams file via fstrm_file_writer /
 * fstrm_writer_write, then reads them back with fstrm_file_reader /
 * fstrm_reader_read and verifies payload equality (R34: test must exercise
 * the tested package's API, not just print a string).
 *
 * File I/O transport is used instead of AF_UNIX because OHOS SELinux policy
 * restricts Unix domain socket bind() (knowledge E024; TCP equivalent PASSes).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <fstrm.h>
#include <fstrm/file.h>
#include <fstrm/reader.h>
#include <fstrm/writer.h>

static int
write_frames(const char *path)
{
	struct fstrm_file_options *fopt;
	struct fstrm_writer *writer;
	fstrm_res res;
	const char *f1 = "frame-one";
	const char *f2 = "frame-two";

	fopt = fstrm_file_options_init();
	if (fopt == NULL)
		return -1;
	fstrm_file_options_set_file_path(fopt, path);

	writer = fstrm_file_writer_init(fopt, NULL);
	fstrm_file_options_destroy(&fopt);
	if (writer == NULL) {
		fprintf(stderr, "fstrm_file_writer_init() failed\n");
		return -1;
	}

	res = fstrm_writer_write(writer, f1, strlen(f1) + 1);
	if (res != fstrm_res_success) {
		fprintf(stderr, "fstrm_writer_write(1) failed\n");
		fstrm_writer_destroy(&writer);
		return -1;
	}
	res = fstrm_writer_write(writer, f2, strlen(f2) + 1);
	if (res != fstrm_res_success) {
		fprintf(stderr, "fstrm_writer_write(2) failed\n");
		fstrm_writer_destroy(&writer);
		return -1;
	}

	res = fstrm_writer_destroy(&writer);
	if (res != fstrm_res_success) {
		fprintf(stderr, "fstrm_writer_destroy() failed\n");
		return -1;
	}
	return 0;
}

static int
read_frames(const char *path)
{
	struct fstrm_file_options *fopt;
	struct fstrm_reader *reader;
	fstrm_res res;
	const uint8_t *data;
	size_t len;
	const char *f1 = "frame-one";
	const char *f2 = "frame-two";
	int n = 0;

	fopt = fstrm_file_options_init();
	if (fopt == NULL)
		return -1;
	fstrm_file_options_set_file_path(fopt, path);

	reader = fstrm_file_reader_init(fopt, NULL);
	fstrm_file_options_destroy(&fopt);
	if (reader == NULL) {
		fprintf(stderr, "fstrm_file_reader_init() failed\n");
		return -1;
	}

	for (;;) {
		res = fstrm_reader_read(reader, &data, &len);
		if (res == fstrm_res_stop)
			break;
		if (res != fstrm_res_success) {
			fprintf(stderr, "fstrm_reader_read() failed\n");
			fstrm_reader_destroy(&reader);
			return -1;
		}
		if (n == 0) {
			if (len != strlen(f1) + 1 || memcmp(data, f1, len) != 0) {
				fprintf(stderr, "frame 1 mismatch\n");
				fstrm_reader_destroy(&reader);
				return -1;
			}
		} else if (n == 1) {
			if (len != strlen(f2) + 1 || memcmp(data, f2, len) != 0) {
				fprintf(stderr, "frame 2 mismatch\n");
				fstrm_reader_destroy(&reader);
				return -1;
			}
		}
		n++;
	}

	res = fstrm_reader_destroy(&reader);
	if (res != fstrm_res_success) {
		fprintf(stderr, "fstrm_reader_destroy() failed\n");
		return -1;
	}
	if (n != 2) {
		fprintf(stderr, "expected 2 frames, got %d\n", n);
		return -1;
	}
	return 0;
}

int
main(int argc, char **argv)
{
	const char *path;

	if (argc > 1)
		path = argv[1];
	else
		path = "test-libfstrm.fs";

	if (write_frames(path) != 0)
		return EXIT_FAILURE;
	if (read_frames(path) != 0)
		return EXIT_FAILURE;

	printf("test libfstrm 0.6.1: OK (2 frames round-trip via fstrm_file)\n");
	return EXIT_SUCCESS;
}
