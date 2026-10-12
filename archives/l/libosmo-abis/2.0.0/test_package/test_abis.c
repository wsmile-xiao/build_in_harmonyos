#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <osmocom/abis/subchan_demux.h>
#include <osmocom/abis/trau_frame.h>

/*
 * libosmo-abis consumer test:
 *  1. subch_demux: feed the bytes of an encoded TRAU idle frame (its
 *     first 16 bits are exactly the 16-zero sync header) into the
 *     demultiplexer and verify a complete 40-byte frame is delivered
 *     via the callback.
 *  2. trau_frame: encode the idle frame to bits, decode the bits back
 *     into a decoded_trau_frame, re-encode and verify the bit stream
 *     is byte-identical (round-trip stability).
 */

static int frame_delivered = 0;

static int out_cb(struct subch_demux *dmx, int ch, const ubit_t *data, int len, void *p)
{
	if (ch == 0 && len == TRAU_FRAME_BITS) {
		frame_delivered = 1;
		printf("ok: subch_demux delivered frame on channel %d (%d bits)\n",
		       ch, len);
	}
	return 0;
}

static void test_subch_demux(void)
{
	struct subch_demux dmx;
	const ubit_t *frame_bits = trau_idle_frame();
	uint8_t buf[TRAU_FRAME_BITS / 2];
	int i;

	/* Feed the frame the way upstream tests/subchan_demux_test.c does:
	 * subch_demux_in() takes TWO bits per input byte for subchannel 0
	 * (bits 0..1 of the byte), earlier bit in the LSB.  The idle frame's
	 * first 16 bits are the all-zero sync header and bit 17 is the 'one'
	 * that completes it (encode_fr() writes trau_bits[16] = 1), so the
	 * demux resyncs at bit 17 (out_idx reset to 17) and the remaining
	 * 303 frame bits fill the buffer to exactly TRAU_FRAME_BITS,
	 * triggering one callback with a complete frame. */
	memset(buf, 0, sizeof(buf));
	for (i = 0; i < TRAU_FRAME_BITS; i++)
		if (frame_bits[i])
			buf[i >> 1] |= (uint8_t)(1 << (i & 1));

	memset(&dmx, 0, sizeof(dmx));
	subch_demux_init(&dmx);
	dmx.chan_activ = 1;
	dmx.out_cb = out_cb;

	subch_demux_in(&dmx, buf, sizeof(buf));
}

static void test_trau_frame(void)
{
	struct decoded_trau_frame fr;
	ubit_t encoded[TRAU_FRAME_BITS];
	ubit_t reencoded[TRAU_FRAME_BITS];

	memset(&fr, 0, sizeof(fr));

	/* round-trip: idle frame bits -> decode -> re-encode */
	memcpy(reencoded, trau_idle_frame(), TRAU_FRAME_BITS * sizeof(ubit_t));
	if (decode_trau_frame(&fr, reencoded) != 0) {
		printf("FAIL: decode_trau_frame returned error\n");
		exit(1);
	}
	printf("ok: decode_trau_frame\n");

	if (encode_trau_frame(encoded, &fr) != 0) {
		printf("FAIL: encode_trau_frame returned error\n");
		exit(1);
	}
	printf("ok: encode_trau_frame\n");

	if (memcmp(encoded, reencoded, TRAU_FRAME_BITS * sizeof(ubit_t)) != 0) {
		printf("FAIL: encode/decode round-trip mismatch\n");
		exit(1);
	}
	printf("ok: trau encode/decode round-trip stable\n");
}

int main(void)
{
	test_subch_demux();
	if (!frame_delivered) {
		printf("FAIL: subch_demux delivered no complete frame\n");
		return 1;
	}
	test_trau_frame();
	printf("consumer test: PASS\n");
	return 0;
}
