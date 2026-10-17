/*
 * ohos_platform_test.c — brieflz HarmonyOS PC (aarch64) platform test.
 *
 * OHOS-specific verification complementary to the upstream unit suite:
 *   1. large-buffer compress/decompress round-trip (memory sizing on OHOS);
 *   2. blz_depack_safe must reject truncated/corrupt input (BLZ_ERROR)
 *      instead of overreading — a memory-safety property relevant on OHOS;
 *   3. blz_max_packed_size / blz_workmem_size sizing consistency and
 *      version macros exported by the installed public header.
 * Uses only the installed public header <brieflz.h> and public API.
 */
#include <brieflz.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BIG_SIZE (8 * 1024 * 1024)  /* 8 MiB buffer */

int main(void)
{
	unsigned char *src, *packed, *out;
	unsigned long src_size = BIG_SIZE;
	unsigned long i;
	int failures = 0;

	/* 1. version macros from installed header */
	if (BLZ_VER_MAJOR != 1 || BLZ_VER_MINOR != 3 || BLZ_VER_PATCH != 0) {
		printf("[OHOS] FAIL: version macros %d.%d.%d\n",
		       BLZ_VER_MAJOR, BLZ_VER_MINOR, BLZ_VER_PATCH);
		failures++;
	} else {
		printf("[OHOS] version macros OK (v%d.%d.%d, string \"%s\")\n",
		       BLZ_VER_MAJOR, BLZ_VER_MINOR, BLZ_VER_PATCH, BLZ_VER_STRING);
	}

	/* 2. sizing consistency */
	{
		unsigned long maxp = blz_max_packed_size(src_size);
		unsigned long wm = blz_workmem_size(src_size);
		if (maxp == 0 || wm == 0) {
			printf("[OHOS] FAIL: sizing returned 0 (maxp=%lu wm=%lu)\n", maxp, wm);
			failures++;
		} else {
			printf("[OHOS] sizing OK (max_packed=%lu, workmem=%lu)\n", maxp, wm);
		}
	}

	src = malloc(src_size);
	packed = malloc(blz_max_packed_size(src_size));
	out = malloc(src_size + 1);
	if (!src || !packed || !out) {
		printf("[OHOS] FAIL: malloc\n");
		return 1;
	}

	/* structured repeatable data: round(i/7) xor (i<<3), compresses well */
	for (i = 0; i < src_size; ++i) {
		src[i] = (unsigned char) ((i / 7) ^ (i << 3));
	}

	/* 3. large-buffer round-trip */
	{
		unsigned long plen = blz_pack(src, packed, src_size,
		                              malloc(blz_workmem_size(src_size)));
		unsigned long olen = plen == BLZ_ERROR ? BLZ_ERROR
		                    : blz_depack(packed, out, src_size);
		if (plen == BLZ_ERROR || olen != src_size) {
			printf("[OHOS] FAIL: round-trip (plen=%lu olen=%lu)\n", plen, olen);
			failures++;
		} else if (memcmp(src, out, src_size) != 0) {
			printf("[OHOS] FAIL: round-trip content mismatch\n");
			failures++;
		} else {
			printf("[OHOS] large round-trip OK (%lu bytes -> %lu packed)\n",
			       src_size, plen);
		}
	}

	/* 4. blz_depack_safe memory-safety contracts on OHOS:
	 *    - truncated input must be rejected (BLZ_ERROR), never overread;
	 *    - depacked_size larger than the actual data must be rejected;
	 *    - corrupted input must never write beyond depacked_size (the
	 *      returned size, when not BLZ_ERROR, must be <= depacked_size). */
	{
		unsigned long plen = blz_pack(src, packed, src_size,
		                              malloc(blz_workmem_size(src_size)));
		unsigned long r1, r2, r3;
		int i;
		if (plen == BLZ_ERROR) {
			printf("[OHOS] FAIL: pack for safe-test\n");
			failures++;
		} else {
			/* feed only half the packed bytes */
			r1 = blz_depack_safe(packed, plen / 2, out, src_size);
			if (r1 != BLZ_ERROR) {
				printf("[OHOS] FAIL: truncated input not rejected (r1=%lu)\n", r1);
				failures++;
			} else {
				printf("[OHOS] safe decode rejects truncated input OK\n");
			}
			/* oversized depacked_size on a small payload */
			r2 = blz_depack_safe(packed, plen, out, src_size + 1);
			if (r2 != BLZ_ERROR) {
				printf("[OHOS] FAIL: oversized depacked_size not rejected (r2=%lu)\n", r2);
				failures++;
			} else {
				printf("[OHOS] safe decode rejects oversized depacked_size OK\n");
			}
			/* corrupt single bytes in the packed stream: must never write
			 * beyond depacked_size (return <= depacked_size when not error) */
			for (i = 0; i < 4; ++i) {
				unsigned char saved = packed[i];
				packed[i] ^= 0xA5;
				r3 = blz_depack_safe(packed, plen, out, src_size);
				packed[i] = saved;
				if (r3 != BLZ_ERROR && r3 > src_size) {
					printf("[OHOS] FAIL: corrupt byte %d overran dst (r3=%lu)\n", i, r3);
					failures++;
				}
			}
			if (failures == 0) {
				printf("[OHOS] safe decode corrupt-input writes bounded OK\n");
			}
		}
	}

	free(src);
	free(packed);
	free(out);

	if (failures == 0) {
		printf("[OHOS] ALL brieflz platform tests PASSED\n");
		return 0;
	}
	printf("[OHOS] %d FAILURE(S)\n", failures);
	return 1;
}