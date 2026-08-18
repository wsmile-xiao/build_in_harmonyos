#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <stlink.h>

/* Real consumer test: links libstlink and calls stlink_parse_ihex(), a pure
 * Intel HEX parser that requires no USB hardware. A tiny valid HEX file is
 * written to disk and the parsed bytes/address/size are asserted. */

static const char *kHex =
    ":10010000214601360121470136007EFE09D2190140\n"
    ":00000001FF\n";

int main(void)
{
	const char *path = "test_input.hex";
	FILE *f = fopen(path, "w");
	if (f == NULL) {
		fprintf(stderr, "FAIL: cannot write %s\n", path);
		return 1;
	}
	fputs(kHex, f);
	fclose(f);

	uint8_t *mem = NULL;
	uint32_t size = 0, begin = 0;
	int32_t rc = stlink_parse_ihex(path, 0xFF, &mem, &size, &begin);

	if (rc != 0) {
		fprintf(stderr, "FAIL: stlink_parse_ihex rc=%d\n", rc);
		return 1;
	}
	if (begin != 0x0100) {
		fprintf(stderr, "FAIL: begin=0x%x, expected 0x0100\n", begin);
		return 1;
	}
	if (size != 16) {
		fprintf(stderr, "FAIL: size=%u, expected 16\n", size);
		return 1;
	}
	/* First data byte of the record :100100002146... */
	if (mem[0] != 0x21) {
		fprintf(stderr, "FAIL: mem[0]=0x%02x, expected 0x21\n", mem[0]);
		return 1;
	}
	if (mem[15] != 0x01) {
		fprintf(stderr, "FAIL: mem[15]=0x%02x, expected 0x01\n", mem[15]);
		return 1;
	}

	printf("stlink_parse_ihex ok: begin=0x%x size=%u\n", begin, size);
	free(mem);
	remove(path);
	printf("test stlink 1.8.0: OK\n");
	return 0;
}
