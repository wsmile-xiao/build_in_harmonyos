#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libopenblas.so"
#endif
int main(void){
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if(!h){ fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：解析 BLAS 与 LAPACK 真实导出符号，证明库 API 可用。 */
    if(!dlsym(h, "cblas_dgemm")){ fprintf(stderr, "cblas_dgemm not found\n"); dlclose(h); return 1; }
    if(!dlsym(h, "dgesv_")){ fprintf(stderr, "dgesv_ (LAPACK) not found\n"); dlclose(h); return 1; }
    printf("openblas: dlopen %s ok, cblas_dgemm + dgesv_ resolved\n", TARGET_SO);
    dlclose(h);
    return 0;
}
