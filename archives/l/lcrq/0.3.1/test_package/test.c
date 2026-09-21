/* SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only */
/* test_package for lcrq/0.3.1 — exercises the real RaptorQ API:
 * rq_init -> parameter accessors -> rq_oti -> rq_encode -> rq_symbol ->
 * rq_decode (encode/decode roundtrip) -> rq_free */

#include <lcrq.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define F 1024UL /* transfer length (bytes) */
#define T 16     /* symbol size (bytes)  */

int main(void)
{
	rq_t *rq;
	rq_oti_t oti = 0;
	rq_scheme_t scheme = 0;
	uint8_t *data = NULL, *enc = NULL, *dec = NULL;
	uint32_t *esi = NULL;
	uint16_t KP;
	uint32_t nesi;
	int rc = 1;

	rq = rq_init(F, T);
	if (!rq) { fprintf(stderr, "FAIL: rq_init\n"); return 1; }

	/* parameter accessors */
	if (rq_F(rq) != F || rq_T(rq) != T) {
		fprintf(stderr, "FAIL: rq_F/rq_T mismatch\n");
		goto err;
	}

	/* OTI encoding roundtrip (RFC6330 3.3.2/3.3.3) */
	if (rq_oti(rq, &oti, &scheme)) {
		fprintf(stderr, "FAIL: rq_oti\n");
		goto err;
	}
	if (rq_oti_F(oti) != F || rq_oti_T(oti) != T) {
		fprintf(stderr, "FAIL: OTI roundtrip mismatch\n");
		goto err;
	}

	/* payload */
	data = malloc(F);
	if (!data) goto err;
	for (uint64_t i = 0; i < F; i++) data[i] = (uint8_t)(i * 31 + 7);

	/* generate intermediate symbols */
	if (rq_encode(rq, data, F)) {
		fprintf(stderr, "FAIL: rq_encode\n");
		goto err;
	}

	/* generate KP + overhead symbols, record each symbol's ESI */
	KP = rq_KP(rq);
	nesi = (uint32_t)KP + RQ_OVERHEAD;
	enc = calloc(nesi, T);
	esi = calloc(nesi, sizeof(uint32_t));
	if (!enc || !esi) goto err;
	rq_pid_t pid = 0;
	for (uint32_t i = 0; i < nesi; i++) {
		uint8_t sym[T];
		rq_symbol(rq, &pid, sym, RQ_RAND);
		memcpy(enc + (size_t)i * T, sym, T);
		esi[i] = rq_pid2esi(pid);
	}

	/* decode from symbols and verify roundtrip */
	dec = calloc(KP, T);
	if (!dec) goto err;
	if (rq_decode(rq, dec, enc, esi, nesi)) {
		fprintf(stderr, "FAIL: rq_decode\n");
		goto err;
	}
	if (memcmp(dec, data, F)) {
		fprintf(stderr, "FAIL: decode roundtrip mismatch\n");
		goto err;
	}

	printf("lcrq 0.3.1 test_package: encode/decode roundtrip OK (F=%lu, T=%u, KP=%u)\n",
			(unsigned long)F, T, KP);
	rc = 0;
err:
	free(dec);
	free(esi);
	free(enc);
	free(data);
	rq_free(rq);
	return rc;
}
