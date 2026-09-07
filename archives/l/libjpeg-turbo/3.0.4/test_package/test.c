#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <jpeglib.h>

#ifndef TARGET_SO
#define TARGET_SO "libjpeg.so"
#endif

/* ── 鸿蒙专项: 真实 JPEG 编码→解码往返（libjpeg API 全链路，R40 反空壳/反 stub）── */
static int roundtrip_test(void) {
    const int W = 64, H = 64;
    unsigned char *pixels = (unsigned char *)malloc((size_t)W * H * 3);
    if (!pixels) return -9;
    for (int y = 0; y < H; y++)
        for (int x = 0; x < W; x++) {
            pixels[(y * W + x) * 3 + 0] = (unsigned char)(x * 4);
            pixels[(y * W + x) * 3 + 1] = (unsigned char)(y * 4);
            pixels[(y * W + x) * 3 + 2] = (unsigned char)((x + y) * 2);
        }

    /* encode → 内存 JPEG */
    struct jpeg_compress_struct cinfo;
    struct jpeg_error_mgr jerr;
    unsigned char *jbuf = NULL;
    unsigned long jsize = 0;
    cinfo.err = jpeg_std_error(&jerr);
    jpeg_create_compress(&cinfo);
    jpeg_mem_dest(&cinfo, &jbuf, &jsize);
    cinfo.image_width = W;
    cinfo.image_height = H;
    cinfo.input_components = 3;
    cinfo.in_color_space = JCS_RGB;
    jpeg_set_defaults(&cinfo);
    jpeg_set_quality(&cinfo, 90, TRUE);
    jpeg_start_compress(&cinfo, TRUE);
    while (cinfo.next_scanline < cinfo.image_height) {
        JSAMPROW row = pixels + cinfo.next_scanline * W * 3;
        jpeg_write_scanlines(&cinfo, &row, 1);
    }
    jpeg_finish_compress(&cinfo);
    jpeg_destroy_compress(&cinfo);
    if (!jbuf || jsize == 0) { free(pixels); return -1; }

    /* decode ← 内存 JPEG */
    struct jpeg_decompress_struct dinfo;
    dinfo.err = jpeg_std_error(&jerr);
    jpeg_create_decompress(&dinfo);
    jpeg_mem_src(&dinfo, jbuf, jsize);
    if (jpeg_read_header(&dinfo, TRUE) != JPEG_HEADER_OK) { free(pixels); free(jbuf); return -2; }
    jpeg_start_decompress(&dinfo);
    if (dinfo.output_width != W || dinfo.output_height != H || dinfo.output_components != 3) {
        jpeg_destroy_decompress(&dinfo); free(pixels); free(jbuf); return -3;
    }
    unsigned char *out = (unsigned char *)malloc((size_t)W * H * 3);
    if (!out) { jpeg_destroy_decompress(&dinfo); free(pixels); free(jbuf); return -9; }
    while (dinfo.output_scanline < dinfo.output_height) {
        JSAMPROW row = out + dinfo.output_scanline * W * 3;
        jpeg_read_scanlines(&dinfo, &row, 1);
    }
    jpeg_finish_decompress(&dinfo);
    jpeg_destroy_decompress(&dinfo);

    /* 验证解码输出非平凡（像素有内容，维数一致已在上步核验） */
    int nonzero = 0;
    for (int i = 0; i < W * H * 3; i++) if (out[i]) { nonzero = 1; break; }
    free(out); free(jbuf); free(pixels);
    return nonzero ? 0 : -4;
}

int main(void) {
    /* 鸿蒙 PC 对 dlopen 校验代码签名（sign-so 专项）：真实加载被测共享库 */
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) { fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror()); return 1; }
    /* R34 反空壳：解析被测包真实导出符号 */
    if (!dlsym(h, "jpeg_std_error")) {
        fprintf(stderr, "symbol jpeg_std_error not found: %s\n", dlerror()); dlclose(h); return 1;
    }
    /* 鸿蒙专项：真实 JPEG 编码→解码往返 */
    int rc = roundtrip_test();
    if (rc != 0) {
        fprintf(stderr, "jpeg encode/decode roundtrip failed rc=%d\n", rc); dlclose(h); return 2;
    }
    printf("libjpeg-turbo: dlopen %s ok, 64x64 RGB encode/decode roundtrip PASSED\n", TARGET_SO);
    dlclose(h);
    return 0;
}
