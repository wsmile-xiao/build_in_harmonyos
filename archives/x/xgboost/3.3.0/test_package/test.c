#include <stdio.h>
#include <xgboost/c_api.h>

int main(void) {
    // Test 1: C API link check — verifies xgboost library is linkable
    const char *err = XGBGetLastError();
    printf("xgboost 3.3.0: C API linked OK (XGBGetLastError=%s)\n", err ? err : "(null)");

    // Test 2: DMatrix creation — verifies xgboost runtime functionality
    DMatrixHandle handle = NULL;
    float data[4] = {1.0f, 2.0f, 3.0f, 4.0f};
    int ret = XGDMatrixCreateFromMat((float*)data, 2, 2, 0.0f, &handle);
    if (ret == 0 && handle != NULL) {
        printf("xgboost 3.3.0: DMatrix creation OK\n");
        XGDMatrixFree(handle);
    } else {
        const char *detail = XGBGetLastError();
        printf("xgboost 3.3.0: DMatrix creation FAILED (ret=%d, detail: %s)\n",
               ret, detail ? detail : "(null)");
        return 1;
    }

    return 0;
}
