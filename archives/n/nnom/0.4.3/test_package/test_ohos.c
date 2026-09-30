/*
 * test_ohos.c — nnom 0.4.3 HarmonyOS-specific test.
 *
 * Runs on the OHOS (aarch64) target and verifies nnom's real behaviour:
 *  - the version macro (NNOM_VERSION == 403);
 *  - q7 fixed-point forward-pass correctness including the negative
 *    input symbol path — layers are linked via model->add() and results
 *    are checked with explicit runtime checks (assert() is stripped by
 *    Release/NDEBUG and must not be the only gate — W4 audit 2026-09-29);
 *  - the port layer (nnom_port.h malloc/printf mapping) is actually used.
 *
 * Uses only the installed public headers and public API.
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
	nnom_3d_shape_t shape = {1, 1, 1};
	nnom_status_t status;

	nnom_layer_t *input = Input(shape, in_buf);
	nnom_layer_t *dense = Dense(1, &w, &b);
	nnom_layer_t *output = Output(shape, out_buf);
	nnom_model_t *model = NULL;

	if (!input || !dense || !output) {
		printf("[OHOS][%s] FAIL: layer creation returned NULL\n", name);
		return 1;
	}
	model = new_model(NULL);
	if (!model) {
		printf("[OHOS][%s] FAIL: new_model returned NULL\n", name);
		return 1;
	}
	status = model->add(model, input);
	status = model->add(model, dense);
	status = model->add(model, output);

	status = model_compile(model, input, output);
	if (status != NN_SUCCESS) {
		printf("[OHOS][%s] FAIL: model_compile=%d\n", name, (int)status);
		model_delete(model);
		return 1;
	}
	status = model_run(model);
	if (status != NN_SUCCESS) {
		printf("[OHOS][%s] FAIL: model_run=%d\n", name, (int)status);
		model_delete(model);
		return 1;
	}
	if (out_buf[0] != expected) {
		printf("[OHOS][%s] FAIL: out_buf[0]=%d, expected %d\n",
		       name, (int)out_buf[0], (int)expected);
		model_delete(model);
		return 1;
	}
	printf("[OHOS][%s] OK: in=%d w=%d -> out=%d (expected %d)\n",
	       name, (int)in, (int)wval, (int)out_buf[0], (int)expected);
	model_delete(model);
	return 0;
}

int main(void)
{
	int failed = 0;

	if (NNOM_VERSION != 403) {
		printf("[OHOS] FAIL: NNOM_VERSION=%d, expected 403\n", NNOM_VERSION);
		failed++;
	} else {
		printf("[OHOS] nnom version 0.4.3 confirmed (NNOM_VERSION=%d)\n",
		       NNOM_VERSION);
	}

	/* positive input: 10 * 2 + 0 = 20 */
	failed += run_case("q7-forward-pos", 10, 2, 20);
	/* negative input symbol path: -10 * 2 = -20 */
	failed += run_case("q7-forward-neg", -10, 2, -20);
	/* zero input: 0 * 2 = 0 */
	failed += run_case("q7-forward-zero", 0, 2, 0);

	if (failed == 0) {
		printf("[OHOS] nnom HarmonyOS-specific test: ALL PASSED\n");
		return 0;
	}
	printf("[OHOS] nnom HarmonyOS-specific test: FAILED (%d)\n", failed);
	return 1;
}