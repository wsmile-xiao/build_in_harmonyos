/* Consumer test for jbig2enc 0.32 (C source — L0 gate requires test sources).
 * Links libjbig2enc and exercises the arithmetic coder (jbig2arith.h):
 * init -> bitimage encode -> tobuffer flush -> datasize — the exact coder
 * path the jbig2 CLI uses for generic regions. */
#include <jbig2arith.h>

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void)
{
    /* 1. Bilevel buffer: 64x64 checkerboard (8x8 blocks). */
    const int W = 64, H = 64;
    unsigned char pix[(W * H + 7) / 8];
    memset(pix, 0, sizeof(pix));
    for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++)
            if ((x / 8 + y / 8) % 2)
                pix[(y * W + x) / 8] |= (unsigned char)(0x80u >> (x % 8));

    /* 2. Arithmetic coder lifecycle. */
    struct jbig2enc_ctx ctx;
    jbig2enc_init(&ctx);
    printf("ok: jbig2enc_init\n");

    /* 3. Encode the bit image (generic region coder path). */
    jbig2enc_bitimage(&ctx, pix, W, H, true);
    printf("ok: jbig2enc_bitimage encoded\n");

    /* 4. Flush to buffer + assert a non-trivial arithmetic-coded size. */
    unsigned char out[4096];
    jbig2enc_tobuffer(&ctx, out);
    unsigned sz = jbig2enc_datasize(&ctx);
    printf("ok: tobuffer flushed, datasize=%u\n", sz);
    if (sz == 0 || sz > sizeof(out)) {
        fprintf(stderr, "unexpected coder datasize %u\n", sz);
        return 1;
    }

    /* 5. Coded stream is deterministic-ish: assert the first bytes form a
     * sane arithmetic-coded stream (nonzero variation). */
    int nonzero = 0;
    for (size_t i = 0; i < (sz < 16 ? sz : 16); i++)
        if (out[i] != 0 && out[i] != 0xFF) { nonzero = 1; break; }
    if (!nonzero && sz > 4) {
        fprintf(stderr, "coded stream looks degenerate\n");
        return 1;
    }
    printf("ok: coded stream varies (nonzero)\n");

    printf("consumer test main completed\n");
    return 0;
}
