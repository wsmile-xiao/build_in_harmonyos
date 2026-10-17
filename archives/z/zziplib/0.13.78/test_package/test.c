#include <stdio.h>
#include <zzip/lib.h>

int main(void) {
    /* zziplib has no runtime version function; use zzip_strerror which
       accepts an errcode and returns a static string without needing a
       real zip file. ZZIP_OUTOFMEM maps to a non-NULL message. */
    zzip_char_t* msg = zzip_strerror(ZZIP_OUTOFMEM);
    if (msg == NULL) {
        fprintf(stderr, "FAIL: zzip_strerror(ZZIP_OUTOFMEM) returned NULL\n");
        return 1;
    }
    printf("zziplib strerror test: %s\n", msg);
    return 0;
}
