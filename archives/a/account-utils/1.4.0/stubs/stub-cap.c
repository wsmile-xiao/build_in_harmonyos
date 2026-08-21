/* libcap stub implementations */
#include <stdlib.h>
#include "sys/capability.h"

cap_t cap_get_proc(void) { return NULL; }
int cap_set_proc(cap_t cap) { (void) cap; return 0; }
int cap_free(void *obj) { (void) obj; return 0; }
int cap_clear(cap_t cap) { (void) cap; return 0; }
int cap_set_flag(cap_t cap, int flag, int ncap, const int *caps, int value) {
    (void) cap; (void) flag; (void) ncap; (void) caps; (void) value;
    return 0;
}
char *cap_to_text(cap_t cap, unsigned int *len) { (void) cap; (void) len; return NULL; }
cap_t cap_from_text(const char *text) { (void) text; return NULL; }
int cap_get_flag(cap_t cap, int capvalue, int flag, unsigned int *ret) {
    (void) cap; (void) capvalue; (void) flag;
    if (ret) *ret = 0;
    return 0;
}

cap_t cap_get_file(const char *path) { (void) path; return NULL; }
