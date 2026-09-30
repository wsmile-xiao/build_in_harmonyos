#include <stdio.h>
#include <stdlib.h>
#include "offbrand.h"
#include "obstring.h"
#include "obvector.h"

int main(void) {
    obvector *v = obvector_new(4);
    obstring *s1 = obstring_new("hello");
    obstring *s2 = obstring_new("world");
    if (!v || !s1 || !s2) {
        fprintf(stderr, "test_offbrand-lib: allocation failed\n");
        return 1;
    }
    obvector_store_at_index(v, (obj *)s1, 0);
    obvector_store_at_index(v, (obj *)s2, 1);
    if (obvector_length(v) != 2) {
        fprintf(stderr, "test_offbrand-lib: obvector_length != 2\n");
        return 1;
    }
    if (obstring_length((obstring *)obvector_obj_at_index(v, 0)) != 5) {
        fprintf(stderr, "test_offbrand-lib: stored obstring length != 5\n");
        return 1;
    }
    /* vector dealloc releases contained obstring instances */
    ob_release((obj *)v);
    printf("test offbrand-lib 1.0.0: OK (obstring/obvector public API verified)\n");
    return 0;
}
