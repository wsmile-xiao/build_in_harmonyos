#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <lqr.h>

/* R34: must genuinely call the library API — no stub test.
 * 4 real checks against a small in-memory RGB image:
 *   1. lqr_carver_new returns a live carver
 *   2. width/height/channels round-trip matches the input
 *   3. lqr_carver_init succeeds (LQR_OK)
 *   4. lqr_carver_resize to a smaller size succeeds and dims update
 */
int main(void) {
    const int W = 8, H = 8, C = 3;
    guchar *buffer = (guchar *) malloc((size_t)(W * H * C));
    if (!buffer) {
        printf("FAIL: malloc test buffer\n");
        return 1;
    }
    for (int i = 0; i < W * H * C; i++) {
        buffer[i] = (guchar)(i & 0xFF);
    }

    LqrCarver *carver = lqr_carver_new(buffer, W, H, C);
    if (!carver) {
        printf("FAIL: lqr_carver_new returned NULL\n");
        fflush(stdout);
        free(buffer);
        return 1;
    }
    /* Ownership fix: lqr_carver_destroy() does g_free(r->rgb) unless
     * preserve_in_buffer is set, so without this the malloc'd input
     * buffer would be freed twice (once by destroy, once by our
     * free() below) -> heap corruption / SIGTRAP on hardened
     * allocators. Preserve keeps our original buffer ours; the
     * library owns any resized buffers it allocates later. */
    lqr_carver_set_preserve_input_image(carver);
    printf("CHECK-OK: lqr_carver_new\n");
    fflush(stdout);

    if (lqr_carver_get_width(carver) != W ||
        lqr_carver_get_height(carver) != H ||
        lqr_carver_get_channels(carver) != C) {
        printf("FAIL: dims mismatch got %d x %d x %d, want %d x %d x %d\n",
               lqr_carver_get_width(carver), lqr_carver_get_height(carver),
               lqr_carver_get_channels(carver), W, H, C);
        fflush(stdout);
        lqr_carver_destroy(carver);
        free(buffer);
        return 1;
    }
    printf("CHECK-OK: dims %d x %d x %d\n", W, H, C);
    fflush(stdout);

    if (lqr_carver_init(carver, 1, 0.0f) != LQR_OK) {
        printf("FAIL: lqr_carver_init did not return LQR_OK\n");
        fflush(stdout);
        lqr_carver_destroy(carver);
        free(buffer);
        return 1;
    }
    printf("CHECK-OK: lqr_carver_init\n");
    fflush(stdout);

    if (lqr_carver_resize(carver, 6, 6) != LQR_OK) {
        printf("FAIL: lqr_carver_resize did not return LQR_OK\n");
        fflush(stdout);
        lqr_carver_destroy(carver);
        free(buffer);
        return 1;
    }
    if (lqr_carver_get_width(carver) != 6 ||
        lqr_carver_get_height(carver) != 6) {
        printf("FAIL: resized dims got %d x %d, want 6 x 6\n",
               lqr_carver_get_width(carver), lqr_carver_get_height(carver));
        fflush(stdout);
        lqr_carver_destroy(carver);
        free(buffer);
        return 1;
    }
    printf("CHECK-OK: resize 8x8 -> 6x6\n");
    fflush(stdout);

    lqr_carver_destroy(carver);
    free(buffer);
    printf("test liblqr 0.4.2: OK (4/4 checks)\n");
    fflush(stdout);
    return 0;
}
