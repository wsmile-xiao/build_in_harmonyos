#include <stdio.h>

/* do_quantsmooth is exported by libjpegqs.a; declared with a locally
 * compatible prototype so the reference is resolved against the packaged
 * archive without pulling jpeglib.h internals into this translation unit. */
extern int do_quantsmooth(void);

int main(void) {
    void *sym = (void *)do_quantsmooth;
    if (sym == 0) {
        printf("CONSUMER: null symbol\n");
        return 1;
    }
    printf("CONSUMER: do_quantsmooth resolved at %p\n", sym);
    return 0;
}
