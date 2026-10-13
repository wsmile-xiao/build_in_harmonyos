/* Consumer test for libgrapheme 3.0.0 (Conan L1 test_package).
 *
 * Exercises six representative UTF-8 APIs. Every passing check prints
 * exactly one "CHECK-OK: <name>" line; the test_package recipe counts
 * those lines as the machine evidence for HMBS_TEST_PACKAGE_RESULT.
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <grapheme.h>

static int failures = 0;

static void
check(bool ok, const char *name)
{
	if (ok) {
		printf("CHECK-OK: %s\n", name);
	} else {
		printf("CHECK-FAIL: %s\n", name);
		failures++;
	}
}

int
main(void)
{
	/* 1. UTF-8 decoding of a single ASCII byte. */
	{
		uint_least32_t cp = 0;
		size_t len = grapheme_decode_utf8("A", 1, &cp);
		check(len == 1 && cp == UINT32_C(0x41), "decode-utf8-ascii");
	}

	/* 2. UTF-8 encoding of U+0041. */
	{
		char buf[4];
		size_t len;
		memset(buf, 0, sizeof(buf));
		len = grapheme_encode_utf8(UINT32_C(0x41), buf, sizeof(buf));
		check(len == 1 && buf[0] == 'A', "encode-utf8-ascii");
	}

	/* 3. Grapheme cluster: LATIN SMALL LETTER E (U+0065) followed by
	 * COMBINING ACUTE ACCENT (U+0301, 2 UTF-8 bytes) forms a single
	 * user-perceived character of 3 bytes (UAX #29 GB9 x Extend). */
	{
		static const char text[] = { 'e', '\xcc', '\x81', '\0' };
		size_t br = grapheme_next_character_break_utf8(text, 3);
		check(br == 3, "character-break-combining");
	}

	/* 4. Word segmentation: first word of "hello world" is 5 bytes. */
	{
		size_t br = grapheme_next_word_break_utf8("hello world", 11);
		check(br == 5, "word-break-english");
	}

	/* 5. Case conversion to uppercase. */
	{
		char buf[16];
		size_t ret;
		memset(buf, 0, sizeof(buf));
		ret = grapheme_to_uppercase_utf8("hello", 5, buf, sizeof(buf));
		check(ret == 5 && memcmp(buf, "HELLO", 5) == 0,
		      "to-uppercase-utf8");
	}

	/* 6. Lowercase detection over the whole input. */
	{
		size_t caselen = 0;
		bool ret = grapheme_is_lowercase_utf8("hello", 5, &caselen);
		check(ret && caselen == 5, "is-lowercase-utf8");
	}

	if (failures == 0) {
		printf("consumer: all checks passed.\n");
	}
	return failures ? 1 : 0;
}
