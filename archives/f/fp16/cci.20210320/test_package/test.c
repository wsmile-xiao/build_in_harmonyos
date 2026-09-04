#include <stdio.h>
#include <stdint.h>
#include <math.h>

#include <fp16.h>

int main(void) {
	/* Real consumer test: exercise the fp16 conversion API and verify results. */
	unsigned failures = 0;

	/* IEEE: 1.0f <-> 0x3C00 */
	const uint16_t one_half = fp16_ieee_from_fp32_value(1.0f);
	if (one_half != UINT16_C(0x3C00)) {
		fprintf(stderr, "FAIL: fp16_ieee_from_fp32_value(1.0f)=0x%04X (expected 0x3C00)\n", one_half);
		failures++;
	}
	const float one_back = fp16_ieee_to_fp32_value(one_half);
	if (one_back != 1.0f) {
		fprintf(stderr, "FAIL: fp16_ieee_to_fp32_value(0x3C00)=%g (expected 1.0)\n", one_back);
		failures++;
	}

	/* IEEE: -2.0f <-> 0xC000, bit representation */
	if (fp16_ieee_from_fp32_value(-2.0f) != UINT16_C(0xC000)) {
		fprintf(stderr, "FAIL: fp16_ieee_from_fp32_value(-2.0f) != 0xC000\n");
		failures++;
	}
	if (fp16_ieee_to_fp32_bits(fp16_ieee_from_fp32_value(-2.0f)) != UINT32_C(0xC0000000)) {
		fprintf(stderr, "FAIL: -2.0f bit roundtrip mismatch\n");
		failures++;
	}

	/* Alt format: 0x7C00 maps to 65536.0 (2^16), NOT infinity in alt format */
	const float alt_val = fp16_alt_to_fp32_value(UINT16_C(0x7C00));
	if (alt_val != 65536.0f) {
		fprintf(stderr, "FAIL: fp16_alt_to_fp32_value(0x7C00)=%g (expected 65536.0)\n", alt_val);
		failures++;
	}

	/* Roundtrip consistency at a denormal boundary: IEEE 0x0001 -> 2^-24 */
	const float denorm = fp16_ieee_to_fp32_value(UINT16_C(0x0001));
	if (denorm != 5.9604644775390625e-8f) {
		fprintf(stderr, "FAIL: fp16_ieee_to_fp32_value(0x0001)=%g (expected 2^-24)\n", denorm);
		failures++;
	}

	if (failures == 0) {
		printf("test_fp16: OK (fp16 conversion API verified)\n");
		return 0;
	}
	printf("test_fp16: FAILED (%u checks failed)\n", failures);
	return 1;
}