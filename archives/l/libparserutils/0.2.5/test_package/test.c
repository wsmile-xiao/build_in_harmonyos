/*
 * test_package smoke test for libparserutils 0.2.5
 *
 * Exercises the public C API of the library (R34: must actually call the
 * package's API, not just print a string):
 *   - parserutils_buffer   (append + readback)
 *   - parserutils_stack    (push/pop)
 *   - parserutils_vector   (append/peek/length)
 *   - parserutils_charset_mibenum (UTF-8 <-> 106)
 *   - parserutils_charset_utf8    (to_ucs4 / length)
 *   - parserutils_inputstream     (create/append/peek/advance/destroy)
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <parserutils/parserutils.h>
#include <parserutils/charset/mibenum.h>
#include <parserutils/charset/utf8.h>
#include <parserutils/input/inputstream.h>
#include <parserutils/utils/buffer.h>
#include <parserutils/utils/stack.h>
#include <parserutils/utils/vector.h>

int main(void)
{
	/* 1. buffer: create, append, verify contents */
	parserutils_buffer *buf = NULL;
	if (parserutils_buffer_create(&buf) != PARSERUTILS_OK || buf == NULL) {
		fprintf(stderr, "buffer_create failed\n");
		return 1;
	}
	static const uint8_t hello[] = "hello";
	if (parserutils_buffer_append(buf, hello, 5) != PARSERUTILS_OK) {
		fprintf(stderr, "buffer_append failed\n");
		return 2;
	}
	if (buf->length != 5 || memcmp(buf->data, hello, 5) != 0) {
		fprintf(stderr, "buffer contents wrong (len=%zu)\n", buf->length);
		return 3;
	}
	parserutils_buffer_destroy(buf);

	/* 2. stack: push then pop */
	parserutils_stack *st = NULL;
	if (parserutils_stack_create(sizeof(int), 4, &st) != PARSERUTILS_OK ||
	    st == NULL) {
		fprintf(stderr, "stack_create failed\n");
		return 4;
	}
	int val = 42;
	if (parserutils_stack_push(st, &val) != PARSERUTILS_OK) {
		fprintf(stderr, "stack_push failed\n");
		return 5;
	}
	int popped = 0;
	if (parserutils_stack_pop(st, &popped) != PARSERUTILS_OK || popped != 42) {
		fprintf(stderr, "stack_pop wrong value (%d)\n", popped);
		return 6;
	}
	parserutils_stack_destroy(st);

	/* 3. vector: append, length, peek */
	parserutils_vector *vec = NULL;
	if (parserutils_vector_create(sizeof(int), 4, &vec) != PARSERUTILS_OK ||
	    vec == NULL) {
		fprintf(stderr, "vector_create failed\n");
		return 7;
	}
	if (parserutils_vector_append(vec, &val) != PARSERUTILS_OK) {
		fprintf(stderr, "vector_append failed\n");
		return 8;
	}
	size_t vlen = 0;
	if (parserutils_vector_get_length(vec, &vlen) != PARSERUTILS_OK ||
	    vlen != 1) {
		fprintf(stderr, "vector length wrong (%zu)\n", vlen);
		return 9;
	}
	const int *vpeek = (const int *) parserutils_vector_peek(vec, 0);
	if (vpeek == NULL || *vpeek != 42) {
		fprintf(stderr, "vector peek wrong\n");
		return 10;
	}
	parserutils_vector_destroy(vec);

	/* 4. charset MIB enum: UTF-8 <-> 106 */
	if (parserutils_charset_mibenum_from_name("UTF-8", 5) != 106) {
		fprintf(stderr, "mibenum_from_name(UTF-8) != 106\n");
		return 11;
	}
	const char *mname = parserutils_charset_mibenum_to_name(106);
	if (mname == NULL || strcmp(mname, "UTF-8") != 0) {
		fprintf(stderr, "mibenum_to_name(106) wrong: %s\n",
				mname ? mname : "(null)");
		return 12;
	}

	/* 5. UTF-8: decode Euro sign (U+20AC), count chars */
	static const uint8_t ustr[] = { 0xE2, 0x82, 0xAC, 0x41 }; /* € A */
	uint32_t ucs4 = 0;
	size_t clen = 0;
	if (parserutils_charset_utf8_to_ucs4(ustr, 4, &ucs4, &clen) !=
	    PARSERUTILS_OK || ucs4 != 0x20AC || clen != 3) {
		fprintf(stderr, "utf8_to_ucs4 failed (ucs4=%u clen=%zu)\n",
				(unsigned) ucs4, clen);
		return 13;
	}
	size_t ulen = 0;
	if (parserutils_charset_utf8_length(ustr, 4, &ulen) != PARSERUTILS_OK ||
	    ulen != 2) {
		fprintf(stderr, "utf8_length wrong (%zu)\n", ulen);
		return 14;
	}

	/* 6. inputstream: create, append, peek (3-byte char), advance */
	parserutils_inputstream *stream = NULL;
	if (parserutils_inputstream_create("UTF-8", 1, NULL, &stream) !=
	    PARSERUTILS_OK || stream == NULL) {
		fprintf(stderr, "inputstream_create failed\n");
		return 15;
	}
	if (parserutils_inputstream_append(stream, ustr, 4) != PARSERUTILS_OK) {
		fprintf(stderr, "inputstream_append failed\n");
		return 16;
	}
	const uint8_t *p = NULL;
	size_t plen = 0;
	if (parserutils_inputstream_peek(stream, 0, &p, &plen) !=
	    PARSERUTILS_OK || plen != 3 || memcmp(p, ustr, 3) != 0) {
		fprintf(stderr, "inputstream_peek failed (plen=%zu)\n", plen);
		return 17;
	}
	parserutils_inputstream_advance(stream, plen);
	parserutils_inputstream_destroy(stream);

	printf("libparserutils API assertions: 17 passed\n");
	return 0;
}
