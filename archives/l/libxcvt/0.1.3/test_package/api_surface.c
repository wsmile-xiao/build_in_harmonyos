#include <libxcvt/libxcvt.h>

#define DECLARE_SYMBOL(name) \
    static __typeof__(&name) volatile probe_##name = &name

/* libxcvt.so.0 exported API (libxcvt.h) */
DECLARE_SYMBOL(libxcvt_gen_mode_info);

int main(void) {
    /* Force a live relocation against the exported symbol so that any
     * missing implementation in libxcvt.so.0 fails at link or load time,
     * not silently at runtime. */
    (void)probe_libxcvt_gen_mode_info;
    return 0;
}
