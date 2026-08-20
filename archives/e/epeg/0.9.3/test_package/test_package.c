/*
 * epeg 0.9.3 consumer smoke test.
 *
 * The cross-compile environment has no JPEG test image, so this test
 * focuses on API linkability and basic parameter validation:
 *   1. epeg_close(NULL) must be a safe no-op (the library checks !im).
 *   2. epeg_memory_open(NULL, 0) must return NULL (invalid/empty data
 *      triggers the JPEG error handler via setjmp/longjmp → NULL return).
 * Both calls exercise the libjpeg-turbo and libexif linkage path without
 * requiring valid JPEG data.
 */

#include <stddef.h>

#include <Epeg.h>

int main(void) {
    /* epeg_close(NULL) is a documented safe no-op (returns immediately). */
    epeg_close(NULL);

    /* epeg_memory_open(NULL, 0) must fail and return NULL: the JPEG
     * decompression setup (_epeg_open_header) calls jpeg_read_header on
     * empty data, which triggers the fatal-error handler that longjmps
     * back to the setjmp guard → epeg_close + return NULL. */
    Epeg_Image *im = epeg_memory_open(NULL, 0);
    if (im != NULL) {
        epeg_close(im);
        return 1;
    }

    return 0;
}
