#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <infiniband/verbs.h>
#include <rdma/rdma_cma.h>

/* test_package: substantively exercises the installed rdma-core public API
 * (R34: no print-only shell). Uses only public headers/libs of the package:
 * libibverbs (ibv_get_device_list/count/name) + librdmacm (rdma_get_devices). */
int main(void)
{
    struct ibv_device **dev_list;
    struct ibv_context **rdma_ctxs;
    int num_verbs = 0, num_cma = 0, i;

    /* libibverbs public API: enumerate verbs devices. Without RDMA
     * hardware on OHOS the list is NULL with num_verbs=0 (normal), so
     * guard the free call. */
    dev_list = ibv_get_device_list(&num_verbs);
    if (!dev_list && num_verbs != 0) {
        fprintf(stderr, "ibv_get_device_list failed\n");
        return 1;
    }
    for (i = 0; i < num_verbs; i++) {
        if (!dev_list[i]->name) {
            fprintf(stderr, "device %d has no name\n", i);
            return 1;
        }
        printf("verbs device %d: %s\n", i, dev_list[i]->name);
    }
    if (dev_list)
        ibv_free_device_list(dev_list);
    rdma_ctxs = rdma_get_devices(&num_cma);
    if (!rdma_ctxs && num_cma != 0) {
        fprintf(stderr, "rdma_get_devices failed\n");
        return 2;
    }
    for (i = 0; i < num_cma; i++) {
        if (!rdma_ctxs[i] || !rdma_ctxs[i]->device ||
            !rdma_ctxs[i]->device->name) {
            fprintf(stderr, "rdma device %d has no name\n", i);
            return 2;
        }
        printf("rdma-cm device %d: %s\n", i, rdma_ctxs[i]->device->name);
    }
    if (rdma_ctxs)
        rdma_free_devices(rdma_ctxs);

    printf("rdma-core test_package: PASS (verbs devices=%d, rdmacm devices=%d)\n",
           num_verbs, num_cma);
    return 0;
}
