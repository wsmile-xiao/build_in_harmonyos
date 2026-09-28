/* libtiff 4.7.2.2 功能探针（相对 bootstrap 4.7.2 空壳 dlopen 探针的升级）
 *
 * - 直接链接 libtiff（消费方真实形态，验证 cpp_info.libs 可用）
 * - 核心路径：编译期/运行期版本断言、错误路径、strip LE/BE PACKBITS
 *   roundtrip（逐字节）、tiled roundtrip（逐字节）——全部依赖内建编解码，
 *   任何构建下都应全绿
 * - 编解码后端矩阵：DEFLATE / ZSTD / LZMA / JPEG / WEBP / LERC / JBIG
 *   各自写图再读回比对。仅 -DPROBE_ALL_BACKENDS（真机/CI 构建，8 后端已配齐）时执行；
 *   矩阵内某后端未构建时 SKIP（不判失败），已构建但 roundtrip 不绿则 FAIL
 *   （R34 反空壳：证明运行期真实可用）。
 * - 无损后端（DEFLATE/ZSTD/LZMA/JBIG/LERC(zError=0)）逐字节比对；
 *   有损后端（JPEG/WEBP，默认质量）按容差比对。
 */
#include <tiffio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_assert = 0;
static int g_fail = 0;

#define CHECK(cond, msg) do { \
    int _n = ++g_assert; \
    if (cond) { printf("PASS [%02d] %s\n", _n, msg); } \
    else { g_fail++; printf("FAIL [%02d] %s\n", _n, msg); } \
} while (0)

/* 期望的上游源码版本（制品 revision 4.7.2.2 与上游 4.7.2 解耦，R37） */
#ifndef EXPECT_TIFFLIB_VERSION
#define EXPECT_TIFFLIB_VERSION "4.7.2"
#endif

/* ---------- 基础工具 ---------- */

static int set_common_fields(TIFF *t, uint32_t w, uint32_t h, uint16_t spp, uint16_t bps, uint16_t photo) {
    if (!TIFFSetField(t, TIFFTAG_IMAGEWIDTH, w) ||
        !TIFFSetField(t, TIFFTAG_IMAGELENGTH, h) ||
        !TIFFSetField(t, TIFFTAG_SAMPLESPERPIXEL, spp) ||
        !TIFFSetField(t, TIFFTAG_BITSPERSAMPLE, bps) ||
        !TIFFSetField(t, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG) ||
        !TIFFSetField(t, TIFFTAG_PHOTOMETRIC, photo) ||
        !TIFFSetField(t, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT))
        return -4;
    return 0;
}

/* pattern 0 = 高频棋盘型（无损后端用）；pattern 1 = 平滑渐变（有损后端用） */
static unsigned char px(uint32_t x, uint32_t y, int pattern) {
    return pattern ? (unsigned char)((x + y) * 2 & 0xff) : (unsigned char)((x * 7 + y * 13) & 0xff);
}

/* ---------- 8bit 灰度 strip 写/验 ---------- */
/* 返回：0 成功 / -1 IO 失败 / -3 该后端未构建（COMPRESSION SetField 被拒）/ -4 字段设置失败 */

static int write_strip8(const char *path, int be, uint32_t w, uint32_t h, uint16_t comp, int pattern) {
    TIFF *t = TIFFOpen(path, be ? "wb" : "w");
    if (!t) return -1;
    if (set_common_fields(t, w, h, 1, 8, PHOTOMETRIC_MINISBLACK) != 0) { TIFFClose(t); return -4; }
    if (!TIFFSetField(t, TIFFTAG_COMPRESSION, comp)) { TIFFClose(t); return -3; }
    unsigned char *row = (unsigned char *)malloc(w);
    if (!row) { TIFFClose(t); return -1; }
    for (uint32_t y = 0; y < h; y++) {
        for (uint32_t x = 0; x < w; x++) row[x] = px(x, y, pattern);
        if (TIFFWriteScanline(t, row, y, 0) < 0) { free(row); TIFFClose(t); return -1; }
    }
    free(row);
    /* TIFFClose 为 void；写目录失败（如编解码器未配置）时文件写不出，
       由 verify 步骤的 TIFFOpen 失败传导为 FAIL */
    TIFFClose(t);
    return 0;
}

static int verify_strip8(const char *path, int be, uint32_t w, uint32_t h, uint16_t comp, int pattern, int tol) {
    TIFF *t = TIFFOpen(path, "r");
    if (!t) return -1;
    uint32_t v32; uint16_t v16;
    CHECK(TIFFGetField(t, TIFFTAG_IMAGEWIDTH, &v32) && v32 == w, "readback ImageWidth");
    CHECK(TIFFGetField(t, TIFFTAG_IMAGELENGTH, &v32) && v32 == h, "readback ImageLength");
    CHECK(TIFFGetField(t, TIFFTAG_BITSPERSAMPLE, &v16) && v16 == 8, "readback BitsPerSample");
    CHECK(TIFFGetField(t, TIFFTAG_SAMPLESPERPIXEL, &v16) && v16 == 1, "readback SamplesPerPixel");
    CHECK(TIFFGetField(t, TIFFTAG_COMPRESSION, &v16) && v16 == comp, "readback Compression tag");
    CHECK((TIFFIsByteSwapped(t) != 0) == (be != 0), "byte order matches writer");
    unsigned char *row = (unsigned char *)malloc(w);
    if (!row) { TIFFClose(t); return -1; }
    int bad = 0, maxdiff = 0;
    for (uint32_t y = 0; y < h; y++) {
        if (TIFFReadScanline(t, row, y, 0) < 0) { bad++; break; }
        for (uint32_t x = 0; x < w; x++) {
            int d = (int)row[x] - (int)px(x, y, pattern);
            if (d < 0) d = -d;
            if (d > maxdiff) maxdiff = d;
            if (d > tol) { bad++; break; }
        }
    }
    CHECK(bad == 0, "pixel roundtrip within tolerance");
    free(row);
    TIFFClose(t);
    return bad;
}

/* ---------- 8bit 灰度 tiled 写/验（LERC 要求 tiled；核心路径也复用） ---------- */

static int write_tiled8(const char *path, uint32_t w, uint32_t h, uint32_t tw, uint32_t th,
                        uint16_t comp, int lerc_lossless) {
    TIFF *t = TIFFOpen(path, "w");
    if (!t) return -1;
    if (set_common_fields(t, w, h, 1, 8, PHOTOMETRIC_MINISBLACK) != 0) { TIFFClose(t); return -4; }
    if (!TIFFSetField(t, TIFFTAG_TILEWIDTH, tw) ||
        !TIFFSetField(t, TIFFTAG_TILELENGTH, th)) { TIFFClose(t); return -4; }
    if (!TIFFSetField(t, TIFFTAG_COMPRESSION, comp)) { TIFFClose(t); return -3; }
    if (lerc_lossless && !TIFFSetField(t, TIFFTAG_LERC_MAXZERROR, 0.0)) { TIFFClose(t); return -3; }
    tmsize_t tsize = TIFFTileSize(t);
    unsigned char *buf = (unsigned char *)malloc((size_t)tsize);
    if (!buf) { TIFFClose(t); return -1; }
    for (uint32_t ty = 0; ty < h; ty += th) {
        for (uint32_t tx = 0; tx < w; tx += tw) {
            for (uint32_t y = 0; y < th; y++)
                for (uint32_t x = 0; x < tw; x++)
                    buf[y * tw + x] = (unsigned char)(((tx + x) * 7 + (ty + y) * 13) & 0xff);
            if (TIFFWriteTile(t, buf, tx, ty, 0, 0) < 0) { free(buf); TIFFClose(t); return -1; }
        }
    }
    free(buf);
    /* TIFFClose 为 void；写目录失败（如编解码器未配置）时文件写不出，
       由 verify 步骤的 TIFFOpen 失败传导为 FAIL */
    TIFFClose(t);
    return 0;
}

static int verify_tiled8(const char *path, uint32_t w, uint32_t h, uint32_t tw, uint32_t th, uint16_t comp) {
    TIFF *t = TIFFOpen(path, "r");
    if (!t) return -1;
    uint32_t v32; uint16_t v16;
    CHECK(TIFFIsTiled(t) != 0, "tiled file detected");
    CHECK(TIFFGetField(t, TIFFTAG_TILEWIDTH, &v32) && v32 == tw, "readback TileWidth");
    CHECK(TIFFGetField(t, TIFFTAG_TILELENGTH, &v32) && v32 == th, "readback TileLength");
    CHECK(TIFFGetField(t, TIFFTAG_COMPRESSION, &v16) && v16 == comp, "readback Compression tag");
    tmsize_t tsize = TIFFTileSize(t);
    unsigned char *buf = (unsigned char *)malloc((size_t)tsize);
    if (!buf) { TIFFClose(t); return -1; }
    int bad = 0;
    for (uint32_t ty = 0; ty < h; ty += th) {
        for (uint32_t tx = 0; tx < w; tx += tw) {
            if (TIFFReadTile(t, buf, tx, ty, 0, 0) < 0) { bad++; break; }
            for (uint32_t y = 0; y < th; y++)
                for (uint32_t x = 0; x < tw; x++)
                    if (buf[y * tw + x] != (unsigned char)(((tx + x) * 7 + (ty + y) * 13) & 0xff)) { bad++; break; }
        }
    }
    CHECK(bad == 0, "tile pixel roundtrip (byte-exact)");
    free(buf);
    TIFFClose(t);
    return bad;
}

/* ---------- 8bit RGB strip（JPEG/WEBP 用，有损按容差） ---------- */

static int write_rgb8(const char *path, uint32_t w, uint32_t h, uint16_t comp, uint16_t photo) {
    TIFF *t = TIFFOpen(path, "w");
    if (!t) return -1;
    if (set_common_fields(t, w, h, 3, 8, photo) != 0) { TIFFClose(t); return -4; }
    if (!TIFFSetField(t, TIFFTAG_COMPRESSION, comp)) { TIFFClose(t); return -3; }
    /* JPEG 需要显式 RGB 颜色模式；伪标签 JPEGCOLORMODE 由 JPEG codec 注册，
       必须放在 COMPRESSION 之后设置（否则 Unknown pseudo-tag）；WEBP 无此 tag 需求 */
    if (comp == COMPRESSION_JPEG &&
        !TIFFSetField(t, TIFFTAG_JPEGCOLORMODE, JPEGCOLORMODE_RGB)) { TIFFClose(t); return -4; }
    unsigned char *row = (unsigned char *)malloc((size_t)w * 3);
    if (!row) { TIFFClose(t); return -1; }
    for (uint32_t y = 0; y < h; y++) {
        for (uint32_t x = 0; x < w; x++) {
            row[x * 3 + 0] = (unsigned char)((x * 5 + y * 3) & 0xff);
            row[x * 3 + 1] = (unsigned char)((x * 2 + y * 4) & 0xff);
            row[x * 3 + 2] = (unsigned char)((x * 4 + y * 2) & 0xff);
        }
        if (TIFFWriteScanline(t, row, y, 0) < 0) { free(row); TIFFClose(t); return -1; }
    }
    free(row);
    /* TIFFClose 为 void；写目录失败（如编解码器未配置）时文件写不出，
       由 verify 步骤的 TIFFOpen 失败传导为 FAIL */
    TIFFClose(t);
    return 0;
}

static int verify_rgb8(const char *path, uint32_t w, uint32_t h, uint16_t comp, int tol) {
    TIFF *t = TIFFOpen(path, "r");
    if (!t) return -1;
    if (comp == COMPRESSION_JPEG) {
        /* JPEGCOLORMODE 是 JPEG codec 注册的伪标签：先触发目录读取
           （TIFFGetField 隐式 TIFFReadDirectory）注册 codec，再设置 */
        uint32_t _trig;
        if (!TIFFGetField(t, TIFFTAG_IMAGEWIDTH, &_trig) ||
            !TIFFSetField(t, TIFFTAG_JPEGCOLORMODE, JPEGCOLORMODE_RGB)) { TIFFClose(t); return -1; }
    }
    uint32_t v32; uint16_t v16;
    CHECK(TIFFGetField(t, TIFFTAG_IMAGEWIDTH, &v32) && v32 == w, "readback ImageWidth");
    CHECK(TIFFGetField(t, TIFFTAG_IMAGELENGTH, &v32) && v32 == h, "readback ImageLength");
    CHECK(TIFFGetField(t, TIFFTAG_SAMPLESPERPIXEL, &v16) && v16 == 3, "readback SamplesPerPixel");
    CHECK(TIFFGetField(t, TIFFTAG_COMPRESSION, &v16) && v16 == comp, "readback Compression tag");
    unsigned char *row = (unsigned char *)malloc((size_t)w * 3);
    if (!row) { TIFFClose(t); return -1; }
    int bad = 0, maxdiff = 0;
    for (uint32_t y = 0; y < h; y++) {
        if (TIFFReadScanline(t, row, y, 0) < 0) { bad++; break; }
        for (uint32_t x = 0; x < w; x++) {
            unsigned char want[3] = {
                (unsigned char)((x * 5 + y * 3) & 0xff),
                (unsigned char)((x * 2 + y * 4) & 0xff),
                (unsigned char)((x * 4 + y * 2) & 0xff)};
            for (int c = 0; c < 3; c++) {
                int d = (int)row[x * 3 + c] - (int)want[c];
                if (d < 0) d = -d;
                if (d > maxdiff) maxdiff = d;
                if (d > tol) { bad++; break; }
            }
        }
    }
    CHECK(bad == 0, "RGB pixel roundtrip within tolerance");
    free(row);
    TIFFClose(t);
    return bad;
}

/* ---------- 1bit 二值 strip（JBIG 用，无损逐字节） ---------- */

static int write_jbig1(const char *path, uint32_t w, uint32_t h) {
    TIFF *t = TIFFOpen(path, "w");
    if (!t) return -1;
    if (set_common_fields(t, w, h, 1, 1, PHOTOMETRIC_MINISWHITE) != 0) { TIFFClose(t); return -4; }
    /* JBIG-KIT 需要分辨率参数 */
    if (!TIFFSetField(t, TIFFTAG_XRESOLUTION, 72.0) ||
        !TIFFSetField(t, TIFFTAG_YRESOLUTION, 72.0) ||
        !TIFFSetField(t, TIFFTAG_RESOLUTIONUNIT, RESUNIT_INCH)) { TIFFClose(t); return -4; }
    if (!TIFFSetField(t, TIFFTAG_COMPRESSION, COMPRESSION_JBIG)) { TIFFClose(t); return -3; }
    /* JBIG 编码器只注册 encodestrip（无 encoderow），且要求整图恰好一条 strip：
       整图铺进一条 strip 缓冲，TIFFWriteEncodedStrip 一次写入（rowsperstrip = 高）。 */
    uint32_t rowbytes = (w + 7) / 8;
    if (!TIFFSetField(t, TIFFTAG_ROWSPERSTRIP, h)) { TIFFClose(t); return -4; }
    unsigned char *buf = (unsigned char *)calloc(1, (size_t)rowbytes * h);
    if (!buf) { TIFFClose(t); return -1; }
    for (uint32_t y = 0; y < h; y++)
        for (uint32_t x = 0; x < w; x++)
            if (((x + y) & 1) == 0) buf[y * rowbytes + (x >> 3)] |= (unsigned char)(0x80 >> (x & 7));
    if (TIFFWriteEncodedStrip(t, 0, buf, (tmsize_t)((size_t)rowbytes * h)) < 0) { free(buf); TIFFClose(t); return -1; }
    free(buf);
    /* TIFFClose 为 void；写目录失败（如编解码器未配置）时文件写不出，
       由 verify 步骤的 TIFFOpen 失败传导为 FAIL */
    TIFFClose(t);
    return 0;
}

static int verify_jbig1(const char *path, uint32_t w, uint32_t h) {
    TIFF *t = TIFFOpen(path, "r");
    if (!t) return -1;
    uint32_t v32; uint16_t v16;
    CHECK(TIFFGetField(t, TIFFTAG_IMAGEWIDTH, &v32) && v32 == w, "readback ImageWidth");
    CHECK(TIFFGetField(t, TIFFTAG_IMAGELENGTH, &v32) && v32 == h, "readback ImageLength");
    CHECK(TIFFGetField(t, TIFFTAG_BITSPERSAMPLE, &v16) && v16 == 1, "readback BitsPerSample");
    CHECK(TIFFGetField(t, TIFFTAG_COMPRESSION, &v16) && v16 == COMPRESSION_JBIG, "readback Compression tag");
    /* JBIG 解码器只注册 decodestrip（decoderow 保留 TIFFDefaultDirectory 的
       _TIFFNoRowDecode，TIFFReadScanline 必报 scanline decoding not implemented）：
       整图单条 strip，用 TIFFReadEncodedStrip 一次读出再逐行比对 */
    uint32_t rowbytes = (w + 7) / 8;
    unsigned char *buf = (unsigned char *)malloc((size_t)rowbytes * h);
    if (!buf) { TIFFClose(t); return -1; }
    int bad = 0;
    if (TIFFReadEncodedStrip(t, 0, buf, (tmsize_t)((size_t)rowbytes * h)) < 0) {
        bad = 1;
    } else {
        for (uint32_t y = 0; y < h; y++) {
            for (uint32_t x = 0; x < w; x++) {
                unsigned char bit = (unsigned char)(((x + y) & 1) == 0 ? (0x80 >> (x & 7)) : 0);
                if ((buf[y * rowbytes + (x >> 3)] & (0x80 >> (x & 7))) != bit) { bad++; break; }
            }
        }
    }
    CHECK(bad == 0, "bilevel pixel roundtrip (byte-exact)");
    free(buf);
    TIFFClose(t);
    return bad;
}

/* ---------- 后端矩阵用例包装：不可用 SKIP，可用必须绿 ---------- */

static void codec_case(const char *name, int wrc, int vrc) {
    if (wrc == -3) { printf("SKIP backend %-20s (codec not built into this libtiff)\n", name); return; }
    char msg[96];
    snprintf(msg, sizeof(msg), "%s write prepared", name);
    CHECK(wrc == 0, msg);
    if (wrc != 0) return;
    snprintf(msg, sizeof(msg), "%s verify roundtrip", name);
    CHECK(vrc == 0, msg);
}

int main(void) {
    /* 版本与错误路径（4.7.x 起 TIFFLIB_VERSION_STR 含版权全文，纯版本号在 MAJ_MIN_MIC） */
    CHECK(strncmp(TIFFLIB_VERSION_STR_MAJ_MIN_MIC, EXPECT_TIFFLIB_VERSION, strlen(EXPECT_TIFFLIB_VERSION)) == 0,
          "TIFFLIB_VERSION_STR_MAJ_MIN_MIC == " EXPECT_TIFFLIB_VERSION);
    { const char *rt = TIFFGetVersion();
      CHECK(rt != NULL && strstr(rt, EXPECT_TIFFLIB_VERSION) != NULL,
            "runtime TIFFGetVersion reports " EXPECT_TIFFLIB_VERSION); }
    CHECK(TIFFOpen("probe_missing.tif", "r") == NULL, "TIFFOpen on nonexistent path returns NULL");

    /* 核心 roundtrip：PACKBITS/NONE 为内建编解码，任何构建下都必须全绿 */
    CHECK(write_strip8("probe_strip_le.tif", 0, 64, 32, COMPRESSION_PACKBITS, 0) == 0,
          "write strip LE 64x32 PACKBITS");
    CHECK(verify_strip8("probe_strip_le.tif", 0, 64, 32, COMPRESSION_PACKBITS, 0, 0) == 0,
          "verify strip LE PACKBITS");
    CHECK(write_strip8("probe_strip_be.tif", 1, 31, 17, COMPRESSION_PACKBITS, 0) == 0,
          "write strip BE 31x17 PACKBITS");
    CHECK(verify_strip8("probe_strip_be.tif", 1, 31, 17, COMPRESSION_PACKBITS, 0, 0) == 0,
          "verify strip BE PACKBITS");
    CHECK(write_tiled8("probe_tile.tif", 48, 48, 16, 16, COMPRESSION_NONE, 0) == 0,
          "write tiled 48x48 tile16x16 NONE");
    CHECK(verify_tiled8("probe_tile.tif", 48, 48, 16, 16, COMPRESSION_NONE) == 0,
          "verify tiled NONE");

    /* 编解码后端矩阵（8 后端中的 7 个可压缩路径；libdeflate 与 zlib 共用 DEFLATE 路径）。
     * 仅在声明「已配齐 8 后端」的构建（真机/CI，conanfile.py 传 -DPROBE_ALL_BACKENDS）中执行；
     * 本地核心验证构建不定义该宏，跳过矩阵（本地无后端可用，矩阵无意义）。 */
#ifdef PROBE_ALL_BACKENDS
    codec_case("DEFLATE(zlib)", write_strip8("probe_deflate.tif", 0, 24, 12, COMPRESSION_DEFLATE, 0),
               verify_strip8("probe_deflate.tif", 0, 24, 12, COMPRESSION_DEFLATE, 0, 0));
    codec_case("ZSTD", write_strip8("probe_zstd.tif", 0, 24, 12, COMPRESSION_ZSTD, 0),
               verify_strip8("probe_zstd.tif", 0, 24, 12, COMPRESSION_ZSTD, 0, 0));
    codec_case("LZMA", write_strip8("probe_lzma.tif", 0, 24, 12, COMPRESSION_LZMA, 0),
               verify_strip8("probe_lzma.tif", 0, 24, 12, COMPRESSION_LZMA, 0, 0));
    codec_case("JPEG", write_rgb8("probe_jpeg.tif", 16, 16, COMPRESSION_JPEG, PHOTOMETRIC_YCBCR),
               verify_rgb8("probe_jpeg.tif", 16, 16, COMPRESSION_JPEG, 12));
    codec_case("WEBP", write_rgb8("probe_webp.tif", 16, 16, COMPRESSION_WEBP, PHOTOMETRIC_RGB),
               verify_rgb8("probe_webp.tif", 16, 16, COMPRESSION_WEBP, 12));
    codec_case("LERC", write_tiled8("probe_lerc.tif", 32, 32, 16, 16, COMPRESSION_LERC, 1),
               verify_tiled8("probe_lerc.tif", 32, 32, 16, 16, COMPRESSION_LERC));
    codec_case("JBIG", write_jbig1("probe_jbig.tif", 128, 64),
               verify_jbig1("probe_jbig.tif", 128, 64));
#else
    printf("SKIP backend matrix (core-only build; -DPROBE_ALL_BACKENDS enables 7-codec matrix)\n");
#endif

    /* 清理 */
    remove("probe_strip_le.tif"); remove("probe_strip_be.tif"); remove("probe_tile.tif");
    remove("probe_deflate.tif"); remove("probe_zstd.tif"); remove("probe_lzma.tif");
    remove("probe_jpeg.tif"); remove("probe_webp.tif"); remove("probe_lerc.tif");
    remove("probe_jbig.tif");

    printf("\nlibtiff probe: %d/%d assertions passed%s\n",
           g_assert - g_fail, g_assert, g_fail ? " — FAILED" : " — ALL GREEN");
    return g_fail ? 1 : 0;
}
