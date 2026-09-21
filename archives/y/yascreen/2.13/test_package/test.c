#include <stdio.h>
#include <string.h>

#include <yascreen.h>

#define BUF_SIZE 65536

static char outbuf[BUF_SIZE];
static size_t outlen = 0;

static ssize_t capture(yascreen *s, const void *data, size_t len)
{
	(void)s;
	if (outlen + len < BUF_SIZE) {
		memcpy(outbuf + outlen, data, len);
		outlen += len;
	}
	return (ssize_t)len;
}

int main(void)
{
	yascreen *s = yascreen_init(20, 10);
	if (!s) {
		fprintf(stderr, "FAIL: yascreen_init returned NULL\n");
		return 1;
	}

	if (yascreen_sx(s) != 20 || yascreen_sy(s) != 10) {
		fprintf(stderr, "FAIL: initial size %dx%d != 20x10\n", yascreen_sx(s), yascreen_sy(s));
		return 1;
	}

	/* Route all library output into a buffer so the test runs without a TTY. */
	if (yascreen_setout(s, capture) != 0) {
		fprintf(stderr, "FAIL: yascreen_setout rejected the callback\n");
		return 1;
	}

	if (yascreen_putsxy(s, 0, 0, 0, "hello") < 0) {
		fprintf(stderr, "FAIL: yascreen_putsxy reported failure\n");
		return 1;
	}
	if (yascreen_update(s) < 0) {
		fprintf(stderr, "FAIL: yascreen_update reported failure\n");
		return 1;
	}
	if (!strstr(outbuf, "hello")) {
		fprintf(stderr, "FAIL: flushed output does not contain the written text\n");
		return 1;
	}

	if (yascreen_resize(s, 30, 12) != 0) {
		fprintf(stderr, "FAIL: yascreen_resize reported failure\n");
		return 1;
	}
	if (yascreen_sx(s) != 30 || yascreen_sy(s) != 12) {
		fprintf(stderr, "FAIL: size after resize %dx%d != 30x12\n", yascreen_sx(s), yascreen_sy(s));
		return 1;
	}

	yascreen_clear(s);
	yascreen_free(s);

	printf("yascreen consumer test: all assertions passed\n");
	return 0;
}
