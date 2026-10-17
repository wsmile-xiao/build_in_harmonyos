/*
 * test_rdma_core.c — Test that rdma-core libibverbs is usable.
 *
 * This test verifies that the rdma-core package provides a working
 * libibverbs API by calling ibv_get_device_list() and checking
 * that it returns without crashing.
 */
#include <infiniband/verbs.h>
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int num_devices = 0;
    struct ibv_device **dev_list;

    /* Get the list of RDMA devices (returns NULL if no devices, which is OK on OHOS) */
    dev_list = ibv_get_device_list(&num_devices);
    if (dev_list) {
        printf("Found %d RDMA device(s)\n", num_devices);
        ibv_free_device_list(dev_list);
    } else {
        /* No RDMA devices is expected on OHOS without RDMA hardware */
        printf("No RDMA devices found (expected on OHOS without RDMA hardware)\n");
    }

    /* Verify the API is callable — the library linked and ran successfully */
    printf("rdma-core libibverbs API test: PASS\n");
    return 0;
}
