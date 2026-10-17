/*
 * test_nnom.c — nnom 0.4.3 consumer test (R34: real public-API usage).
 *
 * Builds a tiny input -> dense -> output model through the public nnom
 * API, links the layers with model->add(), runs one forward pass and
 * verifies the quantized result with explicit runtime checks (NOT
 * assert(), which Release/NDEBUG strips — see W4 audit of 2026-09-29).
 */
#include <stdio.h>
#include <stdint.h>

#include "nnom.h"

static int run_case(const char *name, int8_t in, int8_t wval, int8_t expected)
{
	int8_t in_buf[1] = {in};
	int8_t w_val[1] = {wval};
	int8_t b_val[1] = {0};
	nnom_weight_t w = {w_val, 0};
	nnom_bias_t b = {b_val, 0};
	int8_t out_buf[1] = {0};
	nnom_3d_shape_t in_shape = {1, 1, 1};
	nnom_3d_shape_t out_shape = {1, 1, 1};
	nnom_status_t status;

	nnom_layer_t *input = Input(in_shape, in_buf);
	nnom_layer_t *dense = Dense(1, &w, &b);
	nnom_layer_t *output = Output(out_shape, out_buf);
	nnom_model_t *model = NULL;

	if (!input || !dense || !output) {
		printf("[%s] FAIL: layer creation returned NULL\n", name);
		return 1;
	}
	model = new_model(NULL);
	if (!model) {
		printf("[%s] FAIL: new_model returned NULL\n", name);
		return 1;
	}
	/* link layers explicitly — without model->add the dense layer never runs */
	status = model->add(model, input);
	status = model->add(model, dense);
	status = model->add(model, output);

	status = model_compile(model, input, output);
	if (status != NN_SUCCESS) {
		printf("[%s] FAIL: model_compile=%d\n", name, (int)status);
		model_delete(model);
		return 1;
	}
	status = model_run(model);
	if (status != NN_SUCCESS) {
		printf("[%s] FAIL: model_run=%d\n", name, (int)status);
		model_delete(model);
		return 1;
	}
	if (out_buf[0] != expected) {
		printf("[%s] FAIL: out_buf[0]=%d, expected %d\n",
		       name, (int)out_buf[0], (int)expected);
		model_delete(model);
		return 1;
	}
	printf("[%s] OK: in=%d w=%d -> out=%d (expected %d)\n",
	       name, (int)in, (int)wval, (int)out_buf[0], (int)expected);
	model_delete(model);
	return 0;
}

int main(void)
{
	int failed = 0;
	/* positive path: 10 * 2 + 0 = 20 */
	failed += run_case("q7-forward-pos", 10, 2, 20);
	/* negative input symbol path: -10 * 2 = -20 */
	failed += run_case("q7-forward-neg", -10, 2, -20);
	/* zero input: 0 * 2 = 0 */
	failed += run_case("q7-forward-zero", 0, 2, 0);

	if (failed == 0) {
		printf("nnom consumer test PASSED\n");
		return 0;
	}
	printf("nnom consumer test FAILED (%d case(s))\n", failed);
	return 1;
}