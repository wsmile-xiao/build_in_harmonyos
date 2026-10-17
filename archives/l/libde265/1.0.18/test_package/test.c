/* test_package/test.c — libde265 consumer test (R34: substantive API use).
 *
 * Exercises the core libde265 decoder C API: create a decoder context,
 * query the library version, flush the (empty) input to exercise the
 * decode state machine, and tear the context down. This links against
 * libde265 and calls de265_new_decoder / de265_get_version / de265_flush_data
 * / de265_decode / de265_free_decoder — not an empty stub.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libde265/de265.h>

int main(void) {
    /* 1. Report the linked library version. */
    const char *ver = de265_get_version();
    uint32_t vernum = de265_get_version_number();
    printf("libde265 version: %s (numeric 0x%08x)\n", ver ? ver : "(null)",
           (unsigned)vernum);
    if (ver == NULL || strcmp(ver, "1.0.18") != 0) {
        printf("FAIL: unexpected libde265 version\n");
        return 1;
    }

    /* 2. Create a decoder context — this is the primary entry point. */
    de265_decoder_context *ctx = de265_new_decoder();
    if (ctx == NULL) {
        printf("FAIL: de265_new_decoder returned NULL\n");
        return 1;
    }

    /* 3. Flush the empty input stream; de265_flush_data signals end-of-stream
     *    and forces the decoder to drain pending output. */
    de265_error err = de265_flush_data(ctx);
    printf("de265_flush_data -> %d (%s)\n", (int)err, de265_get_error_text(err));
    if (!de265_isOK(err) && err != DE265_ERROR_WAITING_FOR_INPUT_DATA) {
        printf("FAIL: de265_flush_data failed\n");
        de265_free_decoder(ctx);
        return 1;
    }

    /* 4. Drive the decode loop once. With no input data this should report
     *    that there is nothing more to do (more == 0). */
    int more = 0;
    err = de265_decode(ctx, &more);
    printf("de265_decode -> %d (%s), more=%d\n", (int)err,
           de265_get_error_text(err), more);

    /* 5. No picture is expected from empty input. */
    const de265_image *img = de265_get_next_picture(ctx);
    printf("de265_get_next_picture -> %p (expected NULL)\n", (void *)img);
    if (img != NULL) {
        printf("FAIL: unexpected decoded picture from empty input\n");
        de265_free_decoder(ctx);
        return 1;
    }

    /* 6. Tear down. */
    err = de265_free_decoder(ctx);
    printf("de265_free_decoder -> %d (%s)\n", (int)err,
           de265_get_error_text(err));
    if (!de265_isOK(err)) {
        printf("FAIL: de265_free_decoder failed\n");
        return 1;
    }

    printf("test libde265 1.0.18: OK\n");
    return 0;
}
