/* test_package consumer test for mlp.h 0.10.0 (header-only)
 *
 * Trains an XOR network via the public MLP.h API and verifies the
 * trained outputs match the XOR truth table within tolerance.
 * Only public headers/API are used (R34: real API call + observable result).
 */
#define MLP_IMPLEMENTATION
#include "MLP.h"

#include <math.h>
#include <stdio.h>

#define N_SAMPLES   4
#define N_FEATURES  2
#define N_OUTPUTS   1

int main(void) {
    double inputs[N_SAMPLES * N_FEATURES] = {
        0, 0,
        0, 1,
        1, 0,
        1, 1
    };
    double targets[N_SAMPLES * N_OUTPUTS] = {
        0,
        1,
        1,
        0
    };

    Dataset train = MLP_Create_Dataset(
        inputs, targets, N_SAMPLES, N_FEATURES, N_OUTPUTS);

    /* 2 -> 5 -> 1 network */
    Network net = MLP_Create_Network(&(NetworkConfig){
        .topology       = (size_t[]){2, 5, 1},
        .topology_size  = 3,
        .activations    = (Activation[]){ACT_RELU, ACT_SIGMOID},
        .initializers   = MLP_AUTO_INITIALIZERS,
        .loss           = LOSS_BINARY_CROSS_ENTROPY
    });

    TrainOptions opt = MLP_DefaultTrainOptions();
    opt.learning_rate = 1e-1;
    opt.max_epochs    = 5000;
    opt.stop_loss     = 1e-6;

    if (!MLP_Train(&net, &train, &opt)) {
        fprintf(stderr, "Training failed: %s\n",
                MLP_ErrorString(MLP_GetLastError()));
        MLP_Destroy_Network(&net);
        return 1;
    }

    double predictions[N_SAMPLES * N_OUTPUTS];
    Dataset test = MLP_Create_Dataset(
        inputs, predictions, N_SAMPLES, N_FEATURES, N_OUTPUTS);

    if (!MLP_Predict_Dataset(&net, &test, predictions)) {
        fprintf(stderr, "Prediction failed: %s\n",
                MLP_ErrorString(MLP_GetLastError()));
        MLP_Destroy_Network(&net);
        return 1;
    }

    int failures = 0;
    double max_err = 0.0;
    for (int i = 0; i < N_SAMPLES; i++) {
        double out = predictions[i];
        double expected = targets[i];
        double err = fabs(out - expected);
        if (err > max_err) max_err = err;
        if (err > 0.1) failures++;
        printf("XOR(%d,%d) -> %.3f (expected %d)\n",
               (int)inputs[i * N_FEATURES], (int)inputs[i * N_FEATURES + 1],
               out, (int)expected);
    }

    MLP_Destroy_Network(&net);

    printf("max_error=%.4f failures=%d\n", max_err, failures);
    if (failures > 0 || max_err > 0.1) {
        fprintf(stderr, "XOR training verification FAILED\n");
        return 1;
    }
    printf("XOR training verification PASSED\n");
    return 0;
}
