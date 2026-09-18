#include <oneapi/dnnl/dnnl.h>
#include <stdio.h>

int main(void) {
    dnnl_engine_t engine = NULL;
    dnnl_status_t st = dnnl_engine_create(&engine, dnnl_cpu, 0);
    if (st != dnnl_success || engine == NULL) {
        fprintf(stderr, "dnnl_engine_create failed %d\n", (int)st);
        return 1;
    }
    dnnl_engine_destroy(engine);
    printf("onednn version=3.13 engine=cpu ok\n");
    return 0;
}
