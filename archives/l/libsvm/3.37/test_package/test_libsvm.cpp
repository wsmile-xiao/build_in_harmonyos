#include <svm.h>

int main(void) {
    struct svm_parameter param;
    param.svm_type = C_SVC;
    param.kernel_type = LINEAR;
    param.degree = 3;
    param.gamma = 0.0;
    param.coef0 = 0.0;
    param.nu = 0.5;
    param.cache_size = 100;
    param.C = 1.0;
    param.eps = 1e-3;
    param.p = 0.1;
    param.shrinking = 1;
    param.probability = 0;
    param.nr_weight = 0;
    param.weight_label = nullptr;
    param.weight = nullptr;

    struct svm_problem prob;
    prob.l = 0;
    prob.x = nullptr;
    prob.y = nullptr;

    const char *err = svm_check_parameter(&prob, &param);
    return (err == nullptr) ? 0 : 1;
}
