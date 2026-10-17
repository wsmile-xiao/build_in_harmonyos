// HarmonyOS 消费者验证：真实调用 fir1 公开 API
// 覆盖: 系数数组构造 -> 冲激响应滤波 -> 步进响应累积 -> getTaps -> getCoeff 回读
#include "Fir1.h"

#include <math.h>
#include <stdio.h>

// 自包含断言（throw on mismatch），保证与库行为一致
inline void check(int b, const char* t) {
	if (b) return;
	fprintf(stderr, "FAIL: %s\n", t);
	throw t;
}

int main(int, char**) {
	// 1) 数组构造 + 冲激响应
	const double c[] = {1, 3, 2, -5, 8, -8, 7, 9};
	Fir1 fir(c);
	check(8 == fir.getTaps(), "nTaps not set for array ctor.");
	double v = 0;
	for (int i = 0; i < 9; i++) {
		v = fir.filter(i == 1 ? 1.0 : 0.0);
		if (i > 0) {
			check(round(c[i - 1]) == round(v),
			      "Impulse response calc mismatch.");
		}
	}

	// 2) LMS 自适应收敛（正弦对消）
	Fir1 lmsFir(10);
	check(10 == lmsFir.getTaps(), "nTaps not set for LMS ctor.");
	lmsFir.setLearningRate(0.1);
	double output_signal = 0;
	for (int i = 0; i < 100; i++) {
		double input_signal = cos(2 * M_PI / 20 * i) * 0.1;
		double ref_noise = sin(2 * M_PI / 20 * i);
		double canceller = lmsFir.filter(ref_noise);
		output_signal = input_signal - canceller;
		lmsFir.lms_update(output_signal);
	}
	check(fabs(output_signal) < 1E-5,
	      "LMS did not cancel the sine wave with the cosine wave.");

	// 3) getCoeff 回读 + 零填充
	double w[10];
	for (int i = 0; i < 10; i++) w[i] = (double)rand() / RAND_MAX;
	Fir1 fir2(w, 10);
	double w_out[12];
	fir2.getCoeff(w_out, 10);
	for (int i = 0; i < 10; i++) {
		check(w_out[i] == w[i], "getCoeff returned erroneous value.");
	}
	w_out[10] = w_out[11] = 1.0;
	fir2.getCoeff(w_out, 12);
	check(w_out[10] == 0 && w_out[11] == 0,
	      "getCoeff failed to zero-pad returned data.");

	printf("fir1 1.8.0 consumer test: OK (impulse/LMS/getCoeff)\n");
	return 0;
}
