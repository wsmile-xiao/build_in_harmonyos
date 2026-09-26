/*
 * test_package/pic_probe.c — 鸿蒙特有验证（参考 zlib 1.3.2.1 PIC-DSO 探针做法，E539/E541）。
 *
 * libtiff 以动态库（libtiff.so）交付，本探针验证从「下游 DSO 消费者」视角：
 * 把消费 libtiff 的真实读写代码编成 -fPIC 共享库 libtiff_probe.so，再由
 * dlopen 运行器加载执行。覆盖两点：
 *   1) libtiff.so 可被 DSO 链接（导出 ABI 完整，R_AARCH64 重定位可解析）；
 *   2) libtiff.so 的 NEEDED 依赖（zlib/jpeg/zstd/webp/lerc/jbig/lzma/deflate）
 *      在 HarmonyOS XPM 环境下可正常解析加载（自签 .so + 依赖链完整）。
 */
#include <tiffio.h>
#include <string.h>

/* 写一张 4x2 灰度图（DEFLATE 压缩）到 path，成功返回 0。 */
int tiff_probe_write_gray(const char *path) {
    TIFF *out = TIFFOpen(path, "w");
    if (!out) return -1;
    unsigned char row[4];
    TIFFSetField(out, TIFFTAG_IMAGEWIDTH, 4);
    TIFFSetField(out, TIFFTAG_IMAGELENGTH, 2);
    TIFFSetField(out, TIFFTAG_SAMPLESPERPIXEL, 1);
    TIFFSetField(out, TIFFTAG_BITSPERSAMPLE, 8);
    TIFFSetField(out, TIFFTAG_ROWSPERSTRIP, 2);
    TIFFSetField(out, TIFFTAG_COMPRESSION, COMPRESSION_DEFLATE);
    TIFFSetField(out, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);
    TIFFSetField(out, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
    for (int y = 0; y < 2; y++) {
        for (int x = 0; x < 4; x++) row[x] = (unsigned char)(y * 4 + x);
        if (TIFFWriteScanline(out, row, y, 0) < 0) { TIFFClose(out); return -2; }
    }
    TIFFClose(out);
    return 0;
}

/* 读回 path 第 y 行到 out（调用方提供 4 字节缓冲）。注意压缩流不支持随机访问，
 * 调用方必须从 y=0 开始顺序读（libtiff 约束），本探针内部重开文件即从头读。 */
int tiff_probe_read_row(const char *path, int y, unsigned char *out) {
    TIFF *in = TIFFOpen(path, "r");
    if (!in) return -1;
    unsigned char tmp[4];
    for (int i = 0; i <= y; i++)
        if (TIFFReadScanline(in, i < y ? tmp : out, i, 0) < 0) { TIFFClose(in); return -2; }
    TIFFClose(in);
    return 0;
}

const char *tiff_probe_version(void) { return TIFFGetVersion(); }
