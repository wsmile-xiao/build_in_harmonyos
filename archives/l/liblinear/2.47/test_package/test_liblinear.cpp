#include <linear.h>

#include <cmath>
#include <cstdio>

int main() {
    struct feature_node samples[4][3] = {
        {{1, -2.0}, {2, -1.0}, {-1, 0.0}},
        {{1, -1.0}, {2, -2.0}, {-1, 0.0}},
        {{1, 1.0}, {2, 2.0}, {-1, 0.0}},
        {{1, 2.0}, {2, 1.0}, {-1, 0.0}},
    };
    struct feature_node *sample_ptrs[4] = {
        samples[0], samples[1], samples[2], samples[3],
    };
    double labels[4] = {-1.0, -1.0, 1.0, 1.0};

    struct problem prob;
    prob.l = 4;
    prob.n = 3;
    prob.y = labels;
    prob.x = sample_ptrs;
    prob.bias = -1.0;

    struct parameter param;
    param.solver_type = L2R_L2LOSS_SVC_DUAL;
    param.eps = 1e-3;
    param.C = 1.0;
    param.nr_weight = 0;
    param.weight_label = nullptr;
    param.weight = nullptr;
    param.p = 0.1;
    param.nu = 0.5;
    param.init_sol = nullptr;
    param.regularize_bias = 1;

    const char *error = check_parameter(&prob, &param);
    if (error != nullptr) {
        std::fprintf(stderr, "invalid parameters: %s\n", error);
        return 1;
    }

    struct model *model_ = train(&prob, &param);
    if (model_ == nullptr) {
        return 2;
    }

    double prediction = predict(model_, samples[3]);
    if (std::fabs(prediction - 1.0) > 1e-9) {
        free_and_destroy_model(&model_);
        destroy_param(&param);
        return 3;
    }

    const char *model_path = "liblinear-test.model";
    if (save_model(model_path, model_) != 0) {
        free_and_destroy_model(&model_);
        destroy_param(&param);
        return 4;
    }

    free_and_destroy_model(&model_);
    struct model *loaded = load_model(model_path);
    bool loaded_ok = loaded != nullptr
        && std::fabs(predict(loaded, samples[0]) + 1.0) <= 1e-9;
    free_and_destroy_model(&loaded);
    destroy_param(&param);
    std::remove(model_path);

    return loaded_ok ? 0 : 5;
}
