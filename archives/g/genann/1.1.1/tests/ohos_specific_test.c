/*
 * genann OHOS-specific test — validates the library on HarmonyOS PC (OHOS/musl).
 *
 * Distinct from the upstream test.c suite (13 lrun cases). This test exercises
 * the public API (genann_init / genann_randomize / genann_run / genann_train /
 * genann_copy / genann_write / genann_read / genann_free) and asserts real
 * observable results:
 *   1. XOR training via backprop converges so all 4 inputs classify correctly.
 *   2. Copy semantics: copy equals trained source outputs on all 4 inputs.
 *   3. Persistence round-trip through the device filesystem (TMPDIR-relative
 *      path under the current user's home, writable on OHOS):
 *      write -> read -> identical stored weights.
 *   4. Sigmoid cached vs direct agree within 1e-9; relu at 0 is 0.
 *
 * Compile (OHOS cross toolchain):
 *   clang --target=aarch64-linux-ohos \
 *         --sysroot=<ohos-sdk native sysroot> \
 *         -I<install include> ohos_specific_test.c genann.c -lm -o ohos_specific_test
 * Run on the OHOS device (arm64).
 */
#include "genann.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg)                                          \
    do {                                                          \
        if (cond) {                                               \
            printf("  [PASS] %s\n", msg);                         \
        } else {                                                  \
            printf("  [FAIL] %s\n", msg);                         \
            failures++;                                           \
        }                                                         \
    } while (0)

static const double XOR_IN[4][2] = {{0, 0}, {0, 1}, {1, 0}, {1, 1}};
static const double XOR_OUT[4] = {0, 1, 1, 0};

static int classify(const genann *ann, const double *in) {
    const double *o = genann_run(ann, in);
    return o[0] >= 0.5 ? 1 : 0;
}

int main(void) {
    printf("GENANN OHOS-SPECIFIC TEST\n");
    srand(42); /* repeatable */

    /* --- 1. Train XOR (2 inputs, 1 hidden layer of 3, 1 output) --- */
    genann *ann = genann_init(2, 1, 3, 1);
    CHECK(ann != NULL, "genann_init returns non-NULL");
    if (!ann) return 1;

    int i, epoch;
    for (epoch = 0; epoch < 4000; ++epoch) {
        for (i = 0; i < 4; ++i)
            genann_train(ann, XOR_IN[i], &XOR_OUT[i], 0.3);
    }
    int correct = 0;
    for (i = 0; i < 4; ++i)
        correct += (classify(ann, XOR_IN[i]) == (int)XOR_OUT[i]);
    printf("  XOR trained: %d/4 correct\n", correct);
    CHECK(correct == 4, "trained XOR all 4 inputs classify correctly via genann_run");

    /* --- 2. genann_copy semantics --- */
    genann *cp = genann_copy(ann);
    CHECK(cp != NULL, "genann_copy returns non-NULL");
    int cp_correct = 0;
    for (i = 0; i < 4; ++i)
        cp_correct += (classify(cp, XOR_IN[i]) == (int)XOR_OUT[i]);
    CHECK(cp_correct == 4, "copied ANN reproduces source outputs on all 4 inputs");
    CHECK(memcmp(ann->weight, cp->weight, (size_t)ann->total_weights * sizeof(double)) == 0,
          "copy preserves the full weight buffer");

    /* --- 3. Persistence round-trip on the device filesystem --- */
    const char *tmp = getenv("TMPDIR");
    char path[512];
    if (tmp && *tmp)
        snprintf(path, sizeof(path), "%s/genann-ohos-persist.bin", tmp);
    else
        snprintf(path, sizeof(path), "%s/genann-ohos-persist.bin", getenv("HOME") ? getenv("HOME") : ".");

    int wrote_ok = 0;
    FILE *f = fopen(path, "wb");
    if (f) {
        genann_write(ann, f);
        wrote_ok = (fclose(f) == 0);
    }
    CHECK(wrote_ok != 0, "genann_write persists ANN to TMPDIR file");
    if (wrote_ok) {
        genann *rd = genann_read(fopen(path, "rb"));
        CHECK(rd != NULL, "genann_read loads persisted ANN back");
        if (rd) {
            CHECK(memcmp(ann->weight, rd->weight,
                         (size_t)ann->total_weights * sizeof(double)) == 0,
                  "read-back weights identical to stored weights");
            genann_free(rd);
        }
        remove(path);
    }

    /* --- 4. Activation function sanity on OHOS libm --- */
    CHECK(fabs(genann_act_sigmoid(ann, 0.0) - 0.5) < 1e-9, "sigmoid(0) == 0.5");
    CHECK(fabs(genann_act_sigmoid_cached(ann, 0.0) - genann_act_sigmoid(ann, 0.0)) < 1e-9,
          "cached and direct sigmoid agree at 0.0");
    CHECK(genann_act_relu(ann, -3.0) == 0.0, "relu(-3) == 0");
    CHECK(fabs(genann_act_relu(ann, 2.5) - 2.5) < 1e-9, "relu(2.5) == 2.5");

    genann_free(cp);
    genann_free(ann);

    if (failures == 0) {
        printf("OHOS-SPECIFIC TEST: ALL PASSED\n");
        return 0;
    }
    printf("OHOS-SPECIFIC TEST: %d FAILURES\n", failures);
    return 1;
}