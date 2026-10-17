#include <mfhdf.h>

#include <stdio.h>

int main(void)
{
    const char* path = "consumer_test.hdf";
    int status = 0;
    int32 dims[2] = {2, 3};
    int32 start[2] = {0, 0};
    int32 edges[2] = {2, 3};
    int32 values[6] = {1, 2, 3, 4, 5, 6};
    int32 result[6] = {0, 0, 0, 0, 0, 0};
    int32 file = FAIL;
    int32 dataset = FAIL;

    file = SDstart(path, DFACC_CREATE);
    if (file == FAIL) {
        return 1;
    }
    dataset = SDcreate(file, "values", DFNT_INT32, 2, dims);
    if (dataset == FAIL) {
        status = 2;
        goto cleanup;
    }
    if (SDwritedata(dataset, start, NULL, edges, values) == FAIL) {
        status = 3;
        goto cleanup;
    }
    if (SDendaccess(dataset) == FAIL) {
        status = 4;
    }
    dataset = FAIL;
    if (SDend(file) == FAIL) {
        status = 4;
    }
    file = FAIL;
    if (status != 0) {
        goto cleanup;
    }

    file = SDstart(path, DFACC_READ);
    if (file == FAIL) {
        status = 5;
        goto cleanup;
    }
    dataset = SDselect(file, 0);
    if (dataset == FAIL) {
        status = 5;
        goto cleanup;
    }
    if (SDreaddata(dataset, start, NULL, edges, result) == FAIL) {
        status = 5;
        goto cleanup;
    }
    for (int i = 0; i < 6; ++i) {
        if (result[i] != values[i]) {
            status = 6;
            goto cleanup;
        }
    }

cleanup:
    if (dataset != FAIL && SDendaccess(dataset) == FAIL && status == 0) {
        status = 7;
    }
    if (file != FAIL && SDend(file) == FAIL && status == 0) {
        status = 7;
    }
    remove(path);
    return status;
}
