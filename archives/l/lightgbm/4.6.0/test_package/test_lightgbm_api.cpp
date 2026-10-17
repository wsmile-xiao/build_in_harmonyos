#include <LightGBM/c_api.h>

#include <stdio.h>

static int check_lgbm(int rc, const char *step) {
    if (rc != 0) {
        fprintf(stderr, "%s failed: %s\n", step, LGBM_GetLastError());
        return 1;
    }
    return 0;
}

int main(void) {
    float values[] = {
        0.0f, 1.0f,
        1.0f, 0.0f,
    };
    DatasetHandle dataset = NULL;

    if (check_lgbm(
            LGBM_DatasetCreateFromMat(
                values,
                C_API_DTYPE_FLOAT32,
                2,
                2,
                1,
                "max_bin=4 min_data_in_bin=1 min_data_in_leaf=1",
                NULL,
                &dataset),
            "LGBM_DatasetCreateFromMat")) {
        return 1;
    }
    if (dataset == NULL) {
        fprintf(stderr, "LGBM_DatasetCreateFromMat returned a null dataset\n");
        return 1;
    }

    if (check_lgbm(LGBM_DatasetFree(dataset), "LGBM_DatasetFree")) {
        return 1;
    }

    return 0;
}
