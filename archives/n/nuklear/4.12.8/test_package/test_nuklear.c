#define NK_INCLUDE_FIXED_TYPES
#define NK_INCLUDE_STANDARD_BOOL
#define NK_INCLUDE_STANDARD_IO
#define NK_INCLUDE_STANDARD_VARARGS
#define NK_INCLUDE_DEFAULT_ALLOCATOR
#define NK_IMPLEMENTATION
#include <nuklear.h>

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static void check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "check failed: %s\n", message);
        exit(1);
    }
}

static int float_equal(float lhs, float rhs)
{
    return fabsf(lhs - rhs) < 0.0001f;
}

int main(void)
{
    char memory[64 * 1024];
    struct nk_context ctx;
    struct nk_rect rect;
    struct nk_vec2 pos;
    struct nk_vec2 size;
    struct nk_color rgb;
    struct nk_color rgba;

    check(nk_init_fixed(&ctx, memory, sizeof(memory), 0), "context init");
    nk_clear(&ctx);

    rect = nk_rect(1.0f, 2.0f, 3.0f, 4.0f);
    check(float_equal(rect.x, 1.0f), "rect x");
    check(float_equal(rect.y, 2.0f), "rect y");
    check(float_equal(rect.w, 3.0f), "rect width");
    check(float_equal(rect.h, 4.0f), "rect height");

    pos = nk_rect_pos(rect);
    size = nk_rect_size(rect);
    check(float_equal(pos.x, 1.0f) && float_equal(pos.y, 2.0f), "rect pos");
    check(float_equal(size.x, 3.0f) && float_equal(size.y, 4.0f), "rect size");

    rgb = nk_rgb(10, 20, 30);
    check(rgb.r == 10 && rgb.g == 20 && rgb.b == 30 && rgb.a == 255, "rgb");

    rgba = nk_rgba(1, 2, 3, 4);
    check(rgba.r == 1 && rgba.g == 2 && rgba.b == 3 && rgba.a == 4, "rgba");

    check(nk_strlen("nuklear") == 7, "strlen");

    nk_input_begin(&ctx);
    nk_input_scroll(&ctx, nk_vec2(0.0f, 1.0f));
    check(float_equal(ctx.input.mouse.scroll_delta.y, 1.0f), "scroll input");
    nk_input_end(&ctx);
    check(float_equal(ctx.input.mouse.scroll_delta.y, 1.0f), "input end");

    nk_clear(&ctx);
    return 0;
}
