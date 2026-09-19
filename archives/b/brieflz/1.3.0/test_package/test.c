/*
 * test.c — brieflz consumer test (Conan L1 / consumer gate)
 *
 * Verifies a real third-party usage scenario: compress a buffer with the
 * public brieflz API (blz_pack / blz_depack_safe / blz_max_packed_size /
 * blz_workmem_size), then decompress and compare round-trip content.
 * Uses only the installed public header <brieflz.h> and the exported
 * library; this is NOT a copy of the upstream unit test.
 */
#include <brieflz.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
	const char *text = "BriefLZ consumer test on HarmonyOS PC: "
	                   "The quick brown fox jumps over the lazy dog. "
	                   "0123456789 abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ";
	unsigned long in_len = (unsigned long) strlen(text);
	unsigned long max_packed = blz_max_packed_size(in_len);
	unsigned long workmem_size = blz_workmem_size(in_len);
	void *workmem = malloc(workmem_size);
	void *packed = malloc(max_packed);
	void *out = malloc(in_len + 1);
	unsigned long packed_len = 0;
	unsigned long out_len = 0;
	int rc = 1;

	if (!workmem || !packed || !out) {
		printf("consumer test: malloc failed\n");
		goto done;
	}

	/* Compress via public API */
	packed_len = blz_pack((const void *) text, packed, in_len, workmem);
	if (packed_len == BLZ_ERROR || packed_len == 0) {
		printf("consumer test: blz_pack failed (rc=%lu)\n", packed_len);
		goto done;
	}

	/* Decompress via public safe API (depacked_size must equal the exact
	 * original length; blz_depack_safe fails if a larger size is passed) */
	out_len = blz_depack_safe(packed, packed_len, out, in_len);
	if (out_len != in_len) {
		printf("consumer test: blz_depack_safe size mismatch "
		       "(got %lu, want %lu)\n", out_len, in_len);
		goto done;
	}

	if (memcmp(text, out, in_len) != 0) {
		printf("consumer test: round-trip content mismatch\n");
		goto done;
	}

	printf("consumer test: OK (input=%lu packed=%lu, round-trip verified)\n",
	       in_len, packed_len);
	rc = 0;

done:
	free(workmem);
	free(packed);
	free(out);
	return rc;
}
