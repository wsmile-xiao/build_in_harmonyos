/* test_package/ohos_svg_check.c — 鸿蒙特有测试的可执行载荷
 *
 * 与 test_package.c（消费者 API 测试）不同，本程序是 OHOS 特有
 * 链路检查的运行环节。三类对象各司其职：
 *   [P] libsvg-cairo.a   — 最终 Conan 包产物（静态归档，仅做归档级验证）
 *   [S] libsvg-cairo-ohos.so.0 — 测试派生的共享库（消费者打包场景模拟）
 *   [E] ohos_svg_check（本文件）— OHOS 运行时消费者产物
 * test_ohos.sh 先直接验证 [P] 的归档成员架构（ar archive、ELF64 LE
 * AArch64 REL 成员），再用 --whole-archive 把 [P] 链接成 [S]，链接并
 * 运行 [E]，对消费者产物执行 OHOS 属性与运行验证：
 *   ohos_svg_check [E]  ->  libsvg-cairo-ohos.so [S]  ->  libcairo.so / libxml2.so ...
 * 其中 [S] 的全部 svg_cairo_* 符号都来自最终 Conan 包内的
 * libsvg-cairo.a；真实 SVG 解析 + 渲染由本可执行文件 [E] 完成。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <cairo.h>
#include <svg-cairo.h>

/* 64x64 全黑画布上绘制 40x40 白色矩形，四个检查点断言像素 */
#define SURF_W 64
#define SURF_H 64
#define RECT_SIZE 40

static const char *make_svg_doc(void)
{
    static char doc[512];
    snprintf(doc, sizeof(doc),
             "<?xml version=\"1.0\"?>"
             "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"%d\" height=\"%d\""
             " viewBox=\"0 0 %d %d\">"
             "<rect x=\"12\" y=\"12\" width=\"%d\" height=\"%d\" fill=\"#ffffff\"/>"
             "</svg>",
             SURF_W, SURF_H, SURF_W, SURF_H, RECT_SIZE, RECT_SIZE);
    return doc;
}

static int check_pixel(const unsigned char *data, int stride,
                       int x, int y, const char *what,
                       int want_zero)
{
    const unsigned char *px = data + y * stride + x * 4;
    int v = px[0] | px[1] | px[2];
    if (want_zero ? (v != 0) : (v == 0)) {
        fprintf(stderr, "[ohos_svg_check] FAIL: %s @(%d,%d) rgb=(%d,%d,%d)\n",
                what, x, y, px[0], px[1], px[2]);
        return 1;
    }
    return 0;
}

int main(void)
{
    const char *svg_doc = make_svg_doc();
    unsigned char *pixels = NULL;
    unsigned char *before = NULL;
    cairo_surface_t *surface = NULL;
    cairo_t *cr = NULL;
    svg_cairo_t *svgc = NULL;
    svg_cairo_status_t status;
    int stride, failures = 0;
    unsigned long count_before, count_after;
    unsigned int w = 0, h = 0;

    printf("[ohos_svg_check] OHOS-specific runtime check for libsvg-cairo\n");

    /* ── 1. 真实 SVG 解析 ── */
    status = svg_cairo_create(&svgc);
    if (status != SVG_CAIRO_STATUS_SUCCESS || !svgc) {
        fprintf(stderr, "[ohos_svg_check] FAIL: svg_cairo_create\n");
        return 1;
    }
    status = svg_cairo_parse_buffer(svgc, svg_doc, strlen(svg_doc));
    if (status != SVG_CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "[ohos_svg_check] FAIL: parse_buffer returned %d\n", status);
        svg_cairo_destroy(svgc);
        return 1;
    }
    printf("[ohos_svg_check] parse OK\n");

    /* ── 2. 尺寸解析 ── */
    svg_cairo_get_size(svgc, &w, &h);
    if (w != SURF_W || h != SURF_H) {
        fprintf(stderr, "[ohos_svg_check] FAIL: size %ux%u != %dx%d\n", w, h, SURF_W, SURF_H);
        svg_cairo_destroy(svgc);
        return 1;
    }
    printf("[ohos_svg_check] size OK (%ux%u)\n", w, h);

    /* ── 3. 真实渲染（headless cairo image surface）── */
    pixels = (unsigned char *)calloc(1, SURF_W * SURF_H * 4);
    before = (unsigned char *)calloc(1, SURF_W * SURF_H * 4);
    if (!pixels || !before) {
        fprintf(stderr, "[ohos_svg_check] FAIL: calloc\n");
        return 1;
    }
    surface = cairo_image_surface_create_for_data(
        pixels, CAIRO_FORMAT_ARGB32, SURF_W, SURF_H, SURF_W * 4);
    cr = cairo_create(surface);
    if (cairo_status(cr) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "[ohos_svg_check] FAIL: cairo_create: %s\n",
                cairo_status_to_string(cairo_status(cr)));
        return 1;
    }

    /* 渲染前基线 */
    stride = cairo_image_surface_get_stride(surface);
    memcpy(before, pixels, (size_t)(stride * SURF_H));

    status = svg_cairo_render(svgc, cr);
    if (status != SVG_CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "[ohos_svg_check] FAIL: render returned %d\n", status);
        return 1;
    }
    cairo_surface_flush(surface);
    printf("[ohos_svg_check] render OK\n");

    /* ── 4. 确定性像素断言 ── */
    count_before = 0;
    count_after = 0;
    for (int i = 0; i < stride * SURF_H; i++) {
        if (before[i])
            count_before++;
        if (pixels[i])
            count_after++;
    }
    if (count_after <= count_before) {
        fprintf(stderr, "[ohos_svg_check] FAIL: render drew nothing "
                        "(nonzero bytes %lu -> %lu)\n",
                count_before, count_after);
        return 1;
    }

    failures += check_pixel(pixels, stride, SURF_W / 2, SURF_H / 2, "white center", 0);
    failures += check_pixel(pixels, stride, 2, 2, "black corner", 1);
    failures += check_pixel(pixels, stride, 2, SURF_H / 2, "black left edge", 1);
    failures += check_pixel(pixels, stride, SURF_W - 3, SURF_H - 3, "black right edge", 1);
    if (failures) {
        fprintf(stderr, "[ohos_svg_check] FAIL: %d pixel assertion(s) failed\n", failures);
        return 1;
    }
    printf("[ohos_svg_check] pixels OK (nonzero %lu -> %lu)\n",
           count_before, count_after);

    /* ── 5. 清理 ── */
    cairo_destroy(cr);
    cairo_surface_destroy(surface);
    svg_cairo_destroy(svgc);
    free(pixels);
    free(before);

    printf("[ohos_svg_check] ALL OK\n");
    return 0;
}
