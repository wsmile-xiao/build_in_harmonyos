#include <dlfcn.h>
#include <stdio.h>
#ifndef TARGET_SO
#define TARGET_SO "libtcl9.0.so"
#endif
typedef void *(*Tcl_CreateInterp_t)(void);
int main(void) {
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    printf("tcl: dlopen %s ok\n", TARGET_SO);
    /* R34: 实质依赖被测包 API — dlsym 取 Tcl_CreateInterp 并调用 */
    Tcl_CreateInterp_t p_interp = (Tcl_CreateInterp_t)dlsym(h, "Tcl_CreateInterp");
    if (!p_interp) { fprintf(stderr, "dlsym Tcl_CreateInterp failed: %s\n", dlerror()); dlclose(h); return 1; }
    void *interp = p_interp();
    if (!interp) { fprintf(stderr, "FAIL: Tcl_CreateInterp() returned NULL\n"); dlclose(h); return 1; }
    printf("tcl: Tcl_CreateInterp() ok (interp=%p)\n", interp);
    dlclose(h);
    return 0;
}
