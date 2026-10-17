#include <stdio.h>
#include <string.h>
#include <mowgli.h>

int main(void)
{
	/* Exercise mowgli_string API (mowgli_string.c / core) */
	mowgli_string_t *s = mowgli_string_create();
	if (s == NULL) {
		fprintf(stderr, "FAIL: mowgli_string_create returned NULL\n");
		return 1;
	}

	mowgli_string_append(s, "libmowgli-2 ", 12);
	mowgli_string_append_char(s, '2');
	mowgli_string_append(s, ".1.3", 4);

	if (s->pos != 17 || strcmp(s->str, "libmowgli-2 2.1.3") != 0) {
		fprintf(stderr, "FAIL: mowgli_string content mismatch: pos=%zu str='%s'\n",
			s->pos, s->str ? s->str : "(null)");
		mowgli_string_destroy(s);
		return 1;
	}
	printf("PASS: mowgli_string_create/append/append_char -> %s\n", s->str);

	/* Exercise mowgli_strlcpy (core/mowgli_string.c) */
	char buf[32];
	size_t r = mowgli_strlcpy(buf, "mowgli", sizeof(buf));
	if (r != 6 || strcmp(buf, "mowgli") != 0) {
		fprintf(stderr, "FAIL: mowgli_strlcpy returned %zu buf='%s'\n", r, buf);
		mowgli_string_destroy(s);
		return 1;
	}
	printf("PASS: mowgli_strlcpy -> '%s' (len=%zu)\n", buf, r);

	/* Exercise mowgli_alloc/mowgli_free (core/alloc.h) */
	void *p = mowgli_alloc(256);
	if (p == NULL) {
		fprintf(stderr, "FAIL: mowgli_alloc returned NULL\n");
		mowgli_string_destroy(s);
		return 1;
	}
	memset(p, 0xAB, 256);
	mowgli_free(p);
	printf("PASS: mowgli_alloc/mowgli_free\n");

	mowgli_string_destroy(s);
	printf("test libmowgli-2 2.1.3: ALL PASS\n");
	return 0;
}
