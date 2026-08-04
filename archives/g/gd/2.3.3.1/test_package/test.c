/* gd 2.3.3 真实功能断言。
 *
 * 编解码往返是**有效的依赖接入判据** —— 已核实 gd 在缺依赖时是**空桩**而非兜底：
 *   src/gd_png.c:1093   的 #else 分支（无 HAVE_LIBPNG）  返回 NULL / _noPngError()
 *   src/gd_jpeg.c:1207  的 #else 分支（无 HAVE_LIBJPEG） 返回 NULL / _noJpegError()
 * 所以 PNG/JPEG 往返过了，就证明 libpng/libjpeg 真接上了。
 * 对照 hwloc 的 topology-xml-nolibxml.c —— 那是**能用的**内置实现，
 * XML 往返过了也推不出 libxml2 接上，那种情况只能靠 DT_NEEDED 判。
 *
 * graphviz 的 gd 插件只用 GIF/WBMP/JPEG/PNG 四种格式
 * （plugin/gd/gvdevice_gd.c:211-222），所以断言覆盖这几条主路径。
 *
 * 不用 dlopen 探针：解析到 gdImageCreateTrueColor 不等于编解码真能跑。
 */
#include <gd.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define W 64
#define H 48

/* 四个互不相近的纯色。truecolor 路径（PNG/JPEG）直接用；
 * GIF 路径另建调色板图（见 test_gif 的说明——truecolor 转调色板会抖动）。 */
static const struct { int r, g, b; } PALETTE[4] = {
    {255,   0,   0},
    {  0, 255,   0},
    {  0,   0, 255},
    {255, 255, 255},
};

/* 画 4 个纵向色带，第 x 列的颜色由 x/(W/4) 决定 —— 每个像素该是什么色可手算 */
static void paint(gdImagePtr im)
{
    int x, y;
    for (y = 0; y < H; y++)
        for (x = 0; x < W; x++) {
            int i = x / (W / 4);
            gdImageSetPixel(im, x, y, gdTrueColor(PALETTE[i].r, PALETTE[i].g, PALETTE[i].b));
        }
}

static int expect_idx(int x) { return x / (W / 4); }

static int test_version(void)
{
    const char *vs = gdVersionString();
    printf("gd 版本: %s / 宏 %d.%d.%d\n", vs ? vs : "(null)",
           GD_MAJOR_VERSION, GD_MINOR_VERSION, GD_RELEASE_VERSION);
    if (!vs || !*vs) { printf("FAIL gdVersionString 为空\n"); return 1; }
    /* 运行期与编译期不一致 = 头和库不是同一次构建的（包本身的缺陷），
     * 只比对其中一个发现不了 */
    if (gdMajorVersion() != GD_MAJOR_VERSION) {
        printf("FAIL 运行期主版本 %d != 编译期宏 %d（头库错配）\n",
               gdMajorVersion(), GD_MAJOR_VERSION);
        return 1;
    }
    if (GD_MAJOR_VERSION != 2 || GD_MINOR_VERSION != 3) {
        printf("FAIL 版本 %d.%d 不是 2.3\n", GD_MAJOR_VERSION, GD_MINOR_VERSION);
        return 1;
    }
    return 0;
}

static int test_pixels(gdImagePtr im)
{
    int x;
    if (gdImageSX(im) != W || gdImageSY(im) != H) {
        printf("FAIL 尺寸 %dx%d != %dx%d\n", gdImageSX(im), gdImageSY(im), W, H);
        return 1;
    }
    if (!gdImageTrueColor(im)) { printf("FAIL 不是 truecolor 图\n"); return 1; }
    /* 每条色带取中点，逐通道比对 */
    for (x = 0; x < 4; x++) {
        int px = x * (W / 4) + (W / 8);
        int c  = gdImageGetPixel(im, px, H / 2);
        int r = gdTrueColorGetRed(c), g = gdTrueColorGetGreen(c), b = gdTrueColorGetBlue(c);
        if (r != PALETTE[x].r || g != PALETTE[x].g || b != PALETTE[x].b) {
            printf("FAIL 第 %d 带 (%d,%d) = (%d,%d,%d)，期望 (%d,%d,%d)\n",
                   x, px, H / 2, r, g, b, PALETTE[x].r, PALETTE[x].g, PALETTE[x].b);
            return 1;
        }
    }
    printf("像素读写 OK: 4 条色带逐通道与手算一致\n");
    return 0;
}

/* PNG 无损：往返后必须**逐像素完全相等** */
static int test_png(gdImagePtr src)
{
    int size = 0, x, y, rc = 1;
    void *buf = gdImagePngPtr(src, &size);
    gdImagePtr im2 = NULL;

    if (!buf || size <= 0) {
        printf("FAIL gdImagePngPtr 返回空 —— libpng 未接入（gd_png.c 的 !HAVE_LIBPNG 分支返回 NULL）\n");
        return 1;
    }
    /* PNG 魔数：编出来的必须真是 PNG，不能只看"非空" */
    if (size < 8 || memcmp(buf, "\x89PNG\r\n\x1a\n", 8) != 0) {
        printf("FAIL 输出不是 PNG（前 8 字节不符）\n"); goto out;
    }
    im2 = gdImageCreateFromPngPtr(size, buf);
    if (!im2) { printf("FAIL gdImageCreateFromPngPtr 返回空\n"); goto out; }
    if (gdImageSX(im2) != W || gdImageSY(im2) != H) {
        printf("FAIL PNG 往返后尺寸 %dx%d\n", gdImageSX(im2), gdImageSY(im2)); goto out;
    }
    for (y = 0; y < H; y += 7)
        for (x = 0; x < W; x += 5) {
            int c1 = gdImageGetPixel(src, x, y), c2 = gdImageGetPixel(im2, x, y);
            if (gdTrueColorGetRed(c1)   != gdTrueColorGetRed(c2)   ||
                gdTrueColorGetGreen(c1) != gdTrueColorGetGreen(c2) ||
                gdTrueColorGetBlue(c1)  != gdTrueColorGetBlue(c2)) {
                printf("FAIL PNG 往返 (%d,%d) 色变了\n", x, y); goto out;
            }
        }
    printf("PNG 往返 OK: %d 字节，魔数正确，逐像素无损 —— libpng 已接入\n", size);
    rc = 0;
out:
    if (im2) gdImageDestroy(im2);
    gdFree(buf);
    return rc;
}

/* JPEG 有损：只能带容差比，且要避开色带边缘（那里振铃最强） */
static int test_jpeg(gdImagePtr src)
{
    int size = 0, x, rc = 1;
    void *buf = gdImageJpegPtr(src, &size, 100);   /* 质量 100，尽量接近无损 */
    gdImagePtr im2 = NULL;
    const int TOL = 12;

    if (!buf || size <= 0) {
        printf("FAIL gdImageJpegPtr 返回空 —— libjpeg 未接入（gd_jpeg.c 的 !HAVE_LIBJPEG 分支）\n");
        return 1;
    }
    if (size < 2 || ((unsigned char *)buf)[0] != 0xFF || ((unsigned char *)buf)[1] != 0xD8) {
        printf("FAIL 输出不是 JPEG（缺 SOI 标记 FFD8）\n"); goto out;
    }
    im2 = gdImageCreateFromJpegPtr(size, buf);
    if (!im2) { printf("FAIL gdImageCreateFromJpegPtr 返回空\n"); goto out; }
    if (gdImageSX(im2) != W || gdImageSY(im2) != H) {
        printf("FAIL JPEG 往返后尺寸 %dx%d\n", gdImageSX(im2), gdImageSY(im2)); goto out;
    }
    for (x = 0; x < 4; x++) {
        int px = x * (W / 4) + (W / 8);        /* 色带中点，离边缘最远 */
        int c  = gdImageGetPixel(im2, px, H / 2);
        int dr = abs(gdTrueColorGetRed(c)   - PALETTE[x].r);
        int dg = abs(gdTrueColorGetGreen(c) - PALETTE[x].g);
        int db = abs(gdTrueColorGetBlue(c)  - PALETTE[x].b);
        if (dr > TOL || dg > TOL || db > TOL) {
            printf("FAIL JPEG 第 %d 带偏差 (%d,%d,%d) 超过容差 %d\n", x, dr, dg, db, TOL);
            goto out;
        }
    }
    printf("JPEG 往返 OK: %d 字节，SOI 正确，色带中点偏差 <= %d —— libjpeg 已接入\n", size, TOL);
    rc = 0;
out:
    if (im2) gdImageDestroy(im2);
    gdFree(buf);
    return rc;
}

/* GIF 是 gd 内置编解码（无外部依赖）。
 *
 * **必须用调色板图作源**，不能拿 truecolor 图转：
 * gd 的 truecolor→调色板量化默认带**抖动（dithering）**，纯红 (255,0,0)
 * 会变成 (252,2,4)（本机实测）。那是量化行为正常，不是编解码缺陷。
 * 拿 truecolor 图测 GIF，等于把「量化精度」和「GIF 编解码正确性」混在一起，
 * 只能被迫放宽容差 —— 而放宽容差就等于让断言跑在近似值上，
 * 真出编解码 bug 时反而看不出来。
 * GIF 本就是调色板格式，用调色板图测才是对的配对，往返可要求**逐像素精确相等**。
 */
static int test_gif(void)
{
    int size = 0, x, y, rc = 1, i;
    gdImagePtr src = NULL, im2 = NULL;
    void *buf = NULL;
    int idx[4];

    src = gdImageCreate(W, H);              /* 调色板图，非 truecolor */
    if (!src) { printf("FAIL gdImageCreate 返回空\n"); return 1; }
    for (i = 0; i < 4; i++) {
        idx[i] = gdImageColorAllocate(src, PALETTE[i].r, PALETTE[i].g, PALETTE[i].b);
        if (idx[i] < 0) { printf("FAIL gdImageColorAllocate 第 %d 个失败\n", i); goto out; }
    }
    for (y = 0; y < H; y++)
        for (x = 0; x < W; x++)
            gdImageSetPixel(src, x, y, idx[expect_idx(x)]);

    buf = gdImageGifPtr(src, &size);
    if (!buf || size <= 0) { printf("FAIL gdImageGifPtr 返回空\n"); goto out; }
    if (size < 6 || memcmp(buf, "GIF8", 4) != 0) {
        printf("FAIL 输出不是 GIF（缺 GIF8 签名）\n"); goto out;
    }
    im2 = gdImageCreateFromGifPtr(size, buf);
    if (!im2) { printf("FAIL gdImageCreateFromGifPtr 返回空\n"); goto out; }
    for (y = 0; y < H; y += 11)
        for (x = 0; x < W; x += 9) {
            int i = expect_idx(x);
            int c = gdImageGetPixel(im2, x, y);
            /* 往返回来是调色板图，取色要经 gdImageRed/Green/Blue */
            int r = gdImageRed(im2, c), g = gdImageGreen(im2, c), b = gdImageBlue(im2, c);
            if (r != PALETTE[i].r || g != PALETTE[i].g || b != PALETTE[i].b) {
                printf("FAIL GIF 往返 (%d,%d) = (%d,%d,%d)，期望 (%d,%d,%d)\n",
                       x, y, r, g, b, PALETTE[i].r, PALETTE[i].g, PALETTE[i].b);
                goto out;
            }
        }
    printf("GIF 往返 OK: %d 字节，签名正确，4 色调色板化无损\n", size);
    rc = 0;
out:
    if (im2) gdImageDestroy(im2);
    if (src) gdImageDestroy(src);
    if (buf) gdFree(buf);
    return rc;
}

int main(void)
{
    gdImagePtr im;

    if (test_version()) return 1;

    im = gdImageCreateTrueColor(W, H);
    if (!im) { printf("FAIL gdImageCreateTrueColor 返回空\n"); return 1; }
    paint(im);

    if (test_pixels(im)) { gdImageDestroy(im); return 1; }
    if (test_png(im))    { gdImageDestroy(im); return 1; }
    if (test_jpeg(im))   { gdImageDestroy(im); return 1; }
    if (test_gif())      { gdImageDestroy(im); return 1; }

    gdImageDestroy(im);
    printf("gd 2.3.3: 全部断言通过\n");
    return 0;
}
