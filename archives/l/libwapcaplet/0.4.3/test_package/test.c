/*
 * test_package smoke test for libwapcaplet 0.4.3
 *
 * Exercises the public C API of the library (R34: must actually call the
 * package's API, not just print a string):
 *   - lwc_intern_string / lwc_intern_substring
 *   - lwc_string_data / lwc_string_length
 *   - lwc_string_isequal / lwc_string_caseless_isequal
 *   - lwc_string_hash_value / lwc_string_caseless_hash_value
 *   - lwc_string_tolower
 *   - lwc_string_ref / lwc_string_unref (reference counting)
 *
 * Every failure returns a distinct non-zero exit code; a fully successful
 * run prints the total assertion count and returns 0.
 */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include <libwapcaplet/libwapcaplet.h>

int main(void)
{
	lwc_string *str1 = NULL, *str2 = NULL, *str3 = NULL, *sub = NULL;
	lwc_error err;
	bool res;
	lwc_hash hash;
	unsigned int assertions = 0;

	/* 1. lwc_intern_string: intern + data/length accessors */
	err = lwc_intern_string("hello", 5, &str1);
	if (err != lwc_error_ok || str1 == NULL) {
		fprintf(stderr, "lwc_intern_string failed (%d)\n", (int) err);
		return 1;
	}
	if (lwc_string_length(str1) != 5 ||
	    strncmp(lwc_string_data(str1), "hello", 5) != 0) {
		fprintf(stderr, "lwc_string_data/length wrong\n");
		return 2;
	}
	assertions += 2;

	/* 2. Interning the same string returns the same pointer */
	if (lwc_intern_string("hello", 5, &str2) != lwc_error_ok || str1 != str2) {
		fprintf(stderr, "interning same string != same pointer\n");
		return 3;
	}
	assertions += 1;

	/* 3. Interning a different string returns a different pointer */
	if (lwc_intern_string("world", 5, &str3) != lwc_error_ok || str1 == str3) {
		fprintf(stderr, "interning different string != different pointer\n");
		return 4;
	}
	assertions += 1;

	/* 4. lwc_string_isequal */
	if (lwc_string_isequal(str1, str2, &res) != lwc_error_ok || res != true) {
		fprintf(stderr, "lwc_string_isequal(str1,str2) != true\n");
		return 5;
	}
	if (lwc_string_isequal(str1, str3, &res) != lwc_error_ok || res != false) {
		fprintf(stderr, "lwc_string_isequal(str1,str3) != false\n");
		return 6;
	}
	assertions += 2;

	/* 5. lwc_string_caseless_isequal */
	{
		lwc_string *uc = NULL;
		if (lwc_intern_string("HELLO", 5, &uc) != lwc_error_ok) {
			fprintf(stderr, "lwc_intern_string(HELLO) failed\n");
			return 7;
		}
		if (lwc_string_caseless_isequal(str1, uc, &res) != lwc_error_ok ||
		    res != true) {
			fprintf(stderr, "caseless_isequal(hello,HELLO) != true\n");
			return 8;
		}
		if (lwc_string_caseless_isequal(str1, str3, &res) != lwc_error_ok ||
		    res != false) {
			fprintf(stderr, "caseless_isequal(hello,world) != false\n");
			return 9;
		}
		lwc_string_unref(uc);
	}
	assertions += 2;

	/* 6. lwc_string_hash_value: non-zero and equal for equal strings */
	hash = lwc_string_hash_value(str1);
	if (hash == 0 || lwc_string_hash_value(str2) != hash) {
		fprintf(stderr, "lwc_string_hash_value wrong\n");
		return 10;
	}
	assertions += 2;

	/* 7. lwc_string_caseless_hash_value */
	if (lwc_string_caseless_hash_value(str1, &hash) != lwc_error_ok || hash == 0) {
		fprintf(stderr, "lwc_string_caseless_hash_value failed\n");
		return 11;
	}
	assertions += 1;

	/* 8. lwc_intern_substring */
	if (lwc_intern_substring(str1, 1, 3, &sub) != lwc_error_ok ||
	    lwc_string_length(sub) != 3 ||
	    strncmp(lwc_string_data(sub), "ell", 3) != 0) {
		fprintf(stderr, "lwc_intern_substring(hello,1,3) != 'ell'\n");
		return 12;
	}
	lwc_string_unref(sub);

	/* 9. Out-of-range substring returns lwc_error_range */
	if (lwc_intern_substring(str1, 3, 10, &sub) != lwc_error_range) {
		fprintf(stderr, "out-of-range substring != lwc_error_range\n");
		return 13;
	}
	assertions += 2;

	/* 10. lwc_string_tolower */
	{
		lwc_string *uc = NULL, *lower = NULL;
		if (lwc_intern_string("HeLLo WoRLd", 11, &uc) != lwc_error_ok) {
			fprintf(stderr, "lwc_intern_string(HeLLo WoRLd) failed\n");
			return 14;
		}
		if (lwc_string_tolower(uc, &lower) != lwc_error_ok ||
		    lwc_string_length(lower) != 11 ||
		    strncmp(lwc_string_data(lower), "hello world", 11) != 0) {
			fprintf(stderr, "lwc_string_tolower wrong\n");
			return 15;
		}
		lwc_string_unref(lower);
		lwc_string_unref(uc);
	}
	assertions += 1;

	/* 11. Reference counting: lwc_string_ref increments refcnt */
	{
		lwc_string *r1 = NULL, *r2 = NULL;
		lwc_refcounter before;
		if (lwc_intern_string("refcount", 8, &r1) != lwc_error_ok) {
			fprintf(stderr, "lwc_intern_string(refcount) failed\n");
			return 16;
		}
		before = r1->refcnt;
		r2 = lwc_string_ref(r1);
		if (r2 != r1 || r1->refcnt != before + 1) {
			fprintf(stderr, "lwc_string_ref did not increment refcnt\n");
			return 17;
		}
		lwc_string_unref(r1);
		lwc_string_unref(r2);
	}
	assertions += 1;

	/* 12. Embedded NUL in interned string keeps explicit length */
	{
		const char bin[] = "a\0b";
		lwc_string *n = NULL;
		if (lwc_intern_string(bin, 3, &n) != lwc_error_ok ||
		    lwc_string_length(n) != 3) {
			fprintf(stderr, "embedded NUL string length wrong\n");
			return 18;
		}
		lwc_string_unref(n);
	}
	assertions += 1;

	lwc_string_unref(str1);
	lwc_string_unref(str2);
	lwc_string_unref(str3);

	printf("libwapcaplet API assertions: %u passed\n", assertions);
	return 0;
}
