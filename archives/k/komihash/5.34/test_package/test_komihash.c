/*
 * Consumer test for the installed komihash package.
 *
 * Calls the public API of the library and asserts real behaviour:
 *   1. one-shot komihash matches the README reference vector;
 *   2. KOMIHASH_VER_STR matches the packaged release;
 *   3. streamed hashing equals one-shot hashing on split input;
 *   4. komirand produces distinct successive outputs;
 *   5. komirand updates its seed state;
 *   6. komihash_seedless agrees with komihash under seed 0 for the
 *      reference input (documented "no seed" convenience variant).
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "komihash.h"

static int failures = 0;

static void check(int cond, const char* what)
{
	if(cond)
		printf("PASS: %s\n", what);
	else
	{
		printf("FAIL: %s\n", what);
		failures++;
	}
}

int main(void)
{
	const char s1[] = "This is a test of komihash.";
	const size_t s1_len = strlen(s1);

	check(komihash(s1, s1_len, 0) == UINT64_C(0x5b13177fc68b4f96),
		"komihash matches README reference vector");

	check(strcmp(KOMIHASH_VER_STR, "5.34") == 0,
		"KOMIHASH_VER_STR is 5.34");

	{
		komihash_stream_t ctx;
		const size_t half = s1_len / 2;

		komihash_stream_init(&ctx, 0);
		komihash_stream_update(&ctx, s1, half);
		komihash_stream_update(&ctx, s1 + half, s1_len - half);
		check(komihash_stream_final(&ctx) == komihash(s1, s1_len, 0),
			"streamed hash equals one-shot hash");
	}

	{
		uint64_t seed1 = 0;
		uint64_t seed2 = 0;
		const uint64_t r1 = komirand(&seed1, &seed2);
		const uint64_t r2 = komirand(&seed1, &seed2);

		check(r1 != r2, "komirand successive outputs differ");
		check(seed1 != 0 || seed2 != 0, "komirand updates its seed state");
	}

	check(komihash_seedless(s1, s1_len) == komihash(s1, s1_len, 0),
		"komihash_seedless agrees with komihash(seed=0)");

	if(failures != 0)
	{
		printf("%d check(s) FAILED\n", failures);
		return 1;
	}
	printf("all komihash consumer checks passed\n");
	return 0;
}
