#include <libpsortb/svmloc/binding.h>
#include <cstdio>
#include <cstring>

extern "C" int get_mtx_index(int row, int col, int row_size);
extern "C" void itoa(char *output, int number);
extern "C" void ftoa(char *output, double number, int precision);

int main()
{
    SVM *model = createSVM(C_SVC, LINEAR, 1, 0.0, 0.0, 1.0, 0.5, 0.1);
    if (!model)
        return 1;
    const bool svm_ok = model->getSVMType() == C_SVC &&
                        model->getKernelType() == LINEAR;
    destroySVM(model);
    if (!svm_ok || get_mtx_index(2, 3, 8) != 19)
        return 2;
    char output[64];
    itoa(output, -42);
    if (std::strcmp(output, "-42") != 0)
        return 3;
    ftoa(output, 1.25, 2);
    if (std::strcmp(output, "1.25") != 0)
        return 4;
    std::puts("LIBPSORTB_CONSUMER_PASS");
    return 0;
}
