/*
 * genann consumer test — business upper-layer simulation.
 *
 * Uses ONLY the installed public header (genann.h) and public API:
 * genann_init / genann_train / genann_run / genann_free. Trains a
 * feedforward ANN on XOR with backprop for a bounded number of epochs
 * and asserts the network classifies the 4 boolean inputs correctly —
 * a real observable result of calling the public API (no print-only
 * stub, no private headers, no internal symbols).
 */
#include <genann.h>
#include <stdio.h>
#include <stdlib.h>

static const double TRAIN_IN[4][2] = {{0, 0}, {0, 1}, {1, 0}, {1, 1}};
static const double TRAIN_OUT[4] = {0, 1, 1, 0};

int main(void) {
    genann *ann = genann_init(2, 1, 3, 1);
    if (!ann) {
        fprintf(stderr, "genann_init failed\n");
        return 1;
    }

    int epoch, i;
    for (epoch = 0; epoch < 4000; ++epoch) {
        for (i = 0; i < 4; ++i) {
            genann_train(ann, TRAIN_IN[i], &TRAIN_OUT[i], 0.3);
        }
    }

    int correct = 0;
    for (i = 0; i < 4; ++i) {
        const double *out = genann_run(ann, TRAIN_IN[i]);
        if ((out[0] >= 0.5 ? 1 : 0) == (int)TRAIN_OUT[i]) {
            correct++;
        }
    }

    genann_free(ann);

    printf("consumer_test: XOR classification correct %d/4\n", correct);
    return correct == 4 ? 0 : 1;
}