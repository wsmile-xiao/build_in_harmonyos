#include <svm.h>

#include <cmath>
#include <cstdio>

int main() {
    svm_node samples[4][3] = {
        {{1, -2.0}, {2, -1.0}, {-1, 0.0}},
        {{1, -1.0}, {2, -2.0}, {-1, 0.0}},
        {{1, 1.0}, {2, 2.0}, {-1, 0.0}},
        {{1, 2.0}, {2, 1.0}, {-1, 0.0}},
    };
    svm_node *sample_ptrs[4] = {
        samples[0], samples[1], samples[2], samples[3],
    };
    double labels[4] = {-1.0, -1.0, 1.0, 1.0};

    svm_problem problem{};
    problem.l = 4;
    problem.y = labels;
    problem.x = sample_ptrs;

    svm_parameter parameter{};
    parameter.svm_type = C_SVC;
    parameter.kernel_type = LINEAR;
    parameter.degree = 3;
    parameter.gamma = 0.5;
    parameter.cache_size = 16;
    parameter.C = 1.0;
    parameter.eps = 1e-3;
    parameter.nu = 0.5;
    parameter.p = 0.1;
    parameter.shrinking = 1;

    const char *error = svm_check_parameter(&problem, &parameter);
    if (error != nullptr) {
        std::fprintf(stderr, "invalid parameters: %s\n", error);
        return 1;
    }

    svm_model *model = svm_train(&problem, &parameter);
    if (model == nullptr || std::fabs(svm_predict(model, samples[3]) - 1.0) > 1e-9) {
        svm_free_and_destroy_model(&model);
        return 2;
    }

    const char *model_path = "libsvm-test.model";
    if (svm_save_model(model_path, model) != 0) {
        svm_free_and_destroy_model(&model);
        return 3;
    }
    svm_free_and_destroy_model(&model);

    model = svm_load_model(model_path);
    const bool loaded_model_works =
        model != nullptr && std::fabs(svm_predict(model, samples[0]) + 1.0) <= 1e-9;
    svm_free_and_destroy_model(&model);
    svm_destroy_param(&parameter);
    std::remove(model_path);

    return loaded_model_works ? 0 : 4;
}
