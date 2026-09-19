/*
 * consumer_test.c — brieflz consumer test.
 *
 * Simulates a business upper-layer component/application on HarmonyOS PC
 * that uses brieflz ONLY through its installed public header <brieflz.h>,
 * public API, normal link target and runtime artifacts — exactly how a
 * third-party consumer would consume the packaged library.
 *
 * Public API exercised: blz_max_packed_size / blz_workmem_size /
 * blz_pack_level (level 9) / blz_depack / blz_depack_safe.
 */
#include <brieflz.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHUNKS 64
#define CHUNK_SIZE 1024

int main(void)
{
	unsigned char data[CHUNKS * CHUNK_SIZE];
	unsigned char *packed;
	unsigned char *out;
	unsigned long i;
	unsigned long total_in = 0;
	unsigned long total_packed = 0;
	int rc = 0;

	/* build a compressible business payload (repeated records) */
	for (i = 0; i < CHUNKS * CHUNK_SIZE; ++i) {
		data[i] = (unsigned char) (i % CHUNK_SIZE);
	}

	packed = malloc(blz_max_packed_size(CHUNKS * CHUNK_SIZE));
	out = malloc(CHUNKS * CHUNK_SIZE);
	if (!packed || !out) {
		printf("[consumer] FAIL: malloc\n");
		return 1;
	}

	/* compress chunk-by-chunk with level 9 via public API */
	for (i = 0; i < CHUNKS; ++i) {
		unsigned long plen = blz_pack_level(data + i * CHUNK_SIZE, packed,
		                                    CHUNK_SIZE,
		                                    malloc(blz_workmem_size(CHUNK_SIZE)),
		                                    9);
		unsigned long olen;
		if (plen == BLZ_ERROR) {
			printf("[consumer] FAIL: blz_pack_level chunk %lu\n", i);
			rc = 1;
			break;
		}
		total_packed += plen;
		total_in += CHUNK_SIZE;

		/* exact-size decompress via blz_depack */
		olen = blz_depack(packed, out, CHUNK_SIZE);
		if (olen != CHUNK_SIZE ||
		    memcmp(data + i * CHUNK_SIZE, out, CHUNK_SIZE) != 0) {
			printf("[consumer] FAIL: blz_depack round-trip chunk %lu\n", i);
			rc = 1;
			break;
		}
	}

	if (rc == 0) {
		/* safe-decoder spot check on one corrupt byte: must not overrun */
		unsigned long plen = blz_pack_level(data, packed, CHUNK_SIZE,
		                                    malloc(blz_workmem_size(CHUNK_SIZE)),
		                                    9);
		unsigned char saved = packed[0];
		packed[0] ^= 0x5A;
		{
			unsigned long r = blz_depack_safe(packed, plen, out, CHUNK_SIZE);
			if (r != BLZ_ERROR && r > CHUNK_SIZE) {
				printf("[consumer] FAIL: corrupt input overran dst (%lu)\n", r);
				rc = 1;
			}
		}
		packed[0] = saved;

		printf("[consumer] brieflz consumer test OK: packed %lu -> %lu bytes "
		       "(%.2f%%), round-trip verified\n",
		       total_in, total_packed,
		       total_in ? (100.0 * (double) total_packed / (double) total_in) : 0.0);
	}

	free(packed);
	free(out);
	return rc;
}