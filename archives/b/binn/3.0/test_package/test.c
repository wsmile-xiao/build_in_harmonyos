#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "binn.h"

/* Consumer test for binn 3.0: build a real binn object, serialize it to
   a buffer, parse it back and verify round-trip values (R34: must exercise
   the package's actual API, not a print-only shell). */
int main(void) {
    binn *obj = binn_object();
    assert(obj != NULL);

    /* populate object */
    assert(binn_object_set_int32(obj, "id", 42) == TRUE);
    assert(binn_object_set_str(obj, "name", "harmonyos") == TRUE);
    assert(binn_object_set_double(obj, "pi", 3.14159) == TRUE);

    /* serialize: binn_release frees the binn struct but keeps the buffer */
    void *buf = binn_release(obj);
    assert(buf != NULL);
    int len = binn_size(buf);
    assert(len > 0);

    /* parse back */
    binn *obj2 = binn_open(buf);
    assert(obj2 != NULL);

    /* verify round-trip */
    int id = 0;
    assert(binn_object_get_int32(obj2, "id", &id) == TRUE);
    assert(id == 42);

    char *name = NULL;
    assert(binn_object_get_str(obj2, "name", &name) == TRUE);
    assert(name != NULL && strcmp(name, "harmonyos") == 0);

    double pi = 0.0;
    assert(binn_object_get_double(obj2, "pi", &pi) == TRUE);
    assert(pi > 3.1415 && pi < 3.1416);

    binn_free(obj2);
    /* obj 已由 binn_release 释放结构，仅 free buffer */
    free(buf);

    printf("binn 3.0 consumer round-trip OK\n");
    return 0;
}
