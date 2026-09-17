/* test-custom-write-cjson.c — cJSON port of upstream test6/test-custom-write.c.
 *
 * Upstream test6 drives the custom-write path (mustach_*_write with a
 * Upper/Lower/Passthrough writer) via test-custom-write.c linked against
 * json-c (-ljson-c). json-c is not published in the registry (R36), so this
 * port exercises the IDENTICAL upstream fixtures (test6/json, test6/must,
 * test6/resu.ref) and the IDENTICAL dotest.sh assertion
 * (mustach=./test-custom-write-cjson ../dotest.sh json -U must -l must -x must)
 * through the vendored cJSON backend (mustach_cJSON_write). Same templates,
 * same expected bytes, same diff-based harness — only the JSON parser
 * differs (cJSON vs json-c, both parse the same fixture JSON).
 *
 * Vendored cJSON 1.7.19 (MIT, Dave Gamble): vendor_cjson/cJSON.c + cJSON.h.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>

#include "cJSON.h"
#include "mustach.h"
#include "mustach-wrap.h"
#include "mustach-cjson.h"

static const size_t BLOCKSIZE = 8192;

static char *readfile(const char *filename, size_t *out_len)
{
	int f;
	struct stat s;
	char *result, *ptr;
	size_t size, pos;
	ssize_t rc;

	result = NULL;
	if (filename[0] == '-' && filename[1] == 0)
		f = dup(0);
	else
		f = open(filename, O_RDONLY);
	if (f < 0) {
		fprintf(stderr, "Can't open file: %s\n", filename);
		exit(1);
	}

	fstat(f, &s);
	switch (s.st_mode & S_IFMT) {
	case S_IFREG:
		size = (size_t)s.st_size;
		break;
	case S_IFSOCK:
	case S_IFIFO:
		size = BLOCKSIZE;
		break;
	default:
		fprintf(stderr, "Bad file: %s\n", filename);
		exit(1);
	}

	pos = 0;
	result = (char *)malloc(size + 1);
	do {
		if (result == NULL) {
			fprintf(stderr, "Out of memory\n");
			exit(1);
		}
		rc = read(f, &result[pos], (size - pos) + 1);
		if (rc < 0) {
			fprintf(stderr, "Error while reading %s\n", filename);
			exit(1);
		}
		if (rc > 0) {
			pos += (size_t)rc;
			if (pos > size) {
				size = pos + BLOCKSIZE;
				ptr = (char *)realloc(result, size + 1);
				if (!ptr)
					free(result);
				result = ptr;
			}
		}
	} while (rc > 0);

	close(f);
	result[pos] = 0;
	if (out_len)
		*out_len = pos;
	return result;
}

enum { None, Upper, Lower } mode = None;

static int uwrite(void *closure, const char *buffer, size_t size)
{
	(void)closure;
	switch (mode) {
	case None:
		fwrite(buffer, size, 1, stdout);
		break;
	case Upper:
		while (size--)
			fputc(toupper((unsigned char)*buffer++), stdout);
		break;
	case Lower:
		while (size--)
			fputc(tolower((unsigned char)*buffer++), stdout);
		break;
	}
	return 0;
}

int main(int ac, char **av)
{
	cJSON *o;
	char *t;
	char *jbuf;
	size_t jlen = 0;
	int s;

	(void)ac;
	if (*++av) {
		jbuf = readfile(av[0], &jlen);
		if (jbuf == NULL) {
			fprintf(stderr, "Aborted: null json (file %s)\n", av[0]);
			exit(1);
		}
		o = cJSON_ParseWithLength(jbuf, jlen);
		free(jbuf);
		if (o == NULL) {
			fprintf(stderr, "Aborted: null json (file %s)\n", av[0]);
			exit(1);
		}
		while (*++av) {
			if (!strcmp(*av, "-U"))
				mode = Upper;
			else if (!strcmp(*av, "-l"))
				mode = Lower;
			else if (!strcmp(*av, "-x"))
				mode = None;
			else {
				t = readfile(*av, NULL);
				s = mustach_cJSON_write(t, 0, o, Mustach_With_AllExtensions, uwrite, NULL);
				if (s != 0)
					fprintf(stderr, "Template error %d\n", s);
				free(t);
			}
		}
		cJSON_Delete(o);
	}
	return 0;
}
