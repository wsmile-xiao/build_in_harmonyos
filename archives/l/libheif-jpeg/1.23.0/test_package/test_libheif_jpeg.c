/* test_package/test_libheif_jpeg.c — libheif-jpeg 1.23.0 消费者验证（R34：真实调用交付面 API）
 *
 * 验证四件事：
 *   1. 链接：find_package(libheif) 找到本包交付的宿主（CMakeDeps，目标 libheif::libheif）；
 *   2. 版本指纹：头文件与运行期库都是 1.23.0（不是设备上其它 libheif）；
 *   3. 运行：LIBHEIF_PLUGIN_PATH / LD_LIBRARY_PATH 由本包 package_info() 的 runenv_info
 *      经 VirtualRunEnv（env="conanrun"）带出，且与编译期钉死的
 *      LIBHEIF_PLUGIN_DIRECTORY 一致；
 *   4. 功能：宿主 dlopen 交付的两个插件模块后
 *        - heif_have_decoder_for_format(heif_compression_JPEG) == 1（libheif-jpegdec.so）
 *        - heif_have_encoder_for_format(heif_compression_JPEG) == 1（libheif-jpegenc.so）
 *      并做一次 JPEG 编码 → JPEG 解码往返（HEIF 图像 → .jpg → HEIF 图像），
 *      外加反证：本包没交付的后端（HEVC/AV1/JPEG2000）必须为 0。
 *
 * 每个 check() 计一行统计；断言总数 = 源码中 check( 调用数（= 25，见 MANIFEST.yml）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libheif/heif.h"

static int g_pass = 0;
static int g_fail = 0;

static int check(int cond, const char* what)
{
    if (cond) {
        g_pass++;
        printf("  [ok]   %s\n", what);
    } else {
        g_fail++;
        printf("  [FAIL] %s\n", what);
    }
    return cond;
}

/* 前置步骤失败时用的合成错误码，保证后续 check 仍然执行（宁可多报 FAIL 也不早退掩盖） */
static struct heif_error bad(const char* why)
{
    struct heif_error e;
    e.code = heif_error_Usage_error;
    e.subcode = heif_suberror_Unspecified;
    e.message = why;
    return e;
}

int main(void)
{
    struct heif_error err;

    printf("=== libheif-jpeg 1.23.0 consumer test ===\n");

    /* ---- 1. 版本指纹（头文件 + 运行期） ---- */
    const char* version = heif_get_version();
    printf("heif_get_version() = %s\n", version ? version : "(null)");
    check(version != NULL && strcmp(version, "1.23.0") == 0,
          "heif_get_version() == \"1.23.0\" (运行期库与头文件同版本)");
    check(heif_get_version_number_major() == 1 &&
          heif_get_version_number_minor() == 23 &&
          heif_get_version_number_maintenance() == 0,
          "heif_get_version_number_{major,minor,maintenance}() == 1.23.0");

    /* ---- 2. 插件目录：编译期默认值 vs 运行期环境变量 ---- */
    const char* plugin_dir_macro = LIBHEIF_PLUGIN_DIRECTORY;
    const char* plugin_dir_env = getenv("LIBHEIF_PLUGIN_PATH");
    printf("LIBHEIF_PLUGIN_DIRECTORY = %s\n", plugin_dir_macro);
    printf("LIBHEIF_PLUGIN_PATH      = %s\n", plugin_dir_env ? plugin_dir_env : "(unset)");
    check(strstr(plugin_dir_macro, "libheif") != NULL,
          "编译期 LIBHEIF_PLUGIN_DIRECTORY 指向 <pkg>/lib/libheif");
    check(plugin_dir_env != NULL && strcmp(plugin_dir_env, plugin_dir_macro) == 0,
          "runenv_info 导出的 LIBHEIF_PLUGIN_PATH == LIBHEIF_PLUGIN_DIRECTORY");

    /* ---- 3. 初始化 ---- */
    err = heif_init(NULL);
    printf("heif_init() -> code=%d msg=%s\n", err.code, err.message ? err.message : "");
    check(err.code == heif_error_Ok, "heif_init(NULL) == heif_error_Ok");

    /* ---- 4. 交付面：两个 JPEG 插件都被宿主装载并注册 ---- */
    check(heif_have_decoder_for_format(heif_compression_JPEG) == 1,
          "heif_have_decoder_for_format(JPEG) == 1 (libheif-jpegdec.so 已装载)");
    check(heif_have_encoder_for_format(heif_compression_JPEG) == 1,
          "heif_have_encoder_for_format(JPEG) == 1 (libheif-jpegenc.so 已装载)");

    /* ---- 5. 反证：本包没交付的后端必须为 0（证明不是内建/系统 libheif 顶替） ---- */
    check(heif_have_decoder_for_format(heif_compression_HEVC) == 0,
          "反证 heif_have_decoder_for_format(HEVC) == 0");
    check(heif_have_encoder_for_format(heif_compression_HEVC) == 0,
          "反证 heif_have_encoder_for_format(HEVC) == 0");
    check(heif_have_decoder_for_format(heif_compression_AV1) == 0,
          "反证 heif_have_decoder_for_format(AV1) == 0");
    check(heif_have_encoder_for_format(heif_compression_AV1) == 0,
          "反证 heif_have_encoder_for_format(AV1) == 0");
    check(heif_have_decoder_for_format(heif_compression_JPEG2000) == 0,
          "反证 heif_have_decoder_for_format(JPEG2000) == 0");

    /* ---- 6. 构造一张 16x16 纯色 RGB 图（纯色可让有损 JPEG 往返可判定） ---- */
    const int W = 16;
    const int H = 16;
    const int R = 200, G = 100, B = 50;

    struct heif_context* ctx = heif_context_alloc();
    check(ctx != NULL, "heif_context_alloc() != NULL");
    if (!ctx) {
        printf("RESULT: pass=%d fail=%d\n", g_pass, g_fail);
        return 1;
    }

    struct heif_image* img = NULL;
    err = heif_image_create(W, H, heif_colorspace_RGB, heif_chroma_interleaved_RGB, &img);
    check(err.code == heif_error_Ok && img != NULL, "heif_image_create(16x16, RGB) == ok");

    err = img ? heif_image_add_plane(img, heif_channel_interleaved, W, H, 8)
              : bad("no image");
    check(err.code == heif_error_Ok, "heif_image_add_plane(interleaved, 16x16, 8bit) == ok");

    int stride = 0;
    uint8_t* plane = img ? heif_image_get_plane(img, heif_channel_interleaved, &stride) : NULL;
    check(plane != NULL && stride >= W * 3, "heif_image_get_plane() != NULL");
    if (plane) {
        for (int y = 0; y < H; y++) {
            for (int x = 0; x < W; x++) {
                plane[y * stride + x * 3 + 0] = (uint8_t) R;
                plane[y * stride + x * 3 + 1] = (uint8_t) G;
                plane[y * stride + x * 3 + 2] = (uint8_t) B;
            }
        }
        printf("  source: %dx%d  RGB(%d,%d,%d)  stride=%d\n", W, H, R, G, B, stride);
    }

    /* ---- 7. JPEG 编码（libheif-jpegenc.so） ---- */
    struct heif_encoder* encoder = NULL;
    err = (img != NULL)
              ? heif_context_get_encoder_for_format(ctx, heif_compression_JPEG, &encoder)
              : bad("no image");
    printf("heif_context_get_encoder_for_format(JPEG) -> code=%d\n", err.code);
    check(err.code == heif_error_Ok && encoder != NULL,
          "heif_context_get_encoder_for_format(JPEG) == ok（插件可用，非仅注册）");

    struct heif_image_handle* enc_handle = NULL;
    err = (img != NULL && encoder != NULL)
              ? heif_context_encode_image(ctx, img, encoder, NULL, &enc_handle)
              : bad("no encoder");
    printf("heif_context_encode_image() -> code=%d\n", err.code);
    check(err.code == heif_error_Ok && enc_handle != NULL,
          "heif_context_encode_image() == ok（真实 JPEG 编码）");

    const char* jpeg_path = "test_libheif_jpeg_roundtrip.jpg";
    err = heif_context_write_to_file(ctx, jpeg_path);
    printf("heif_context_write_to_file(%s) -> code=%d\n", jpeg_path, err.code);
    check(err.code == heif_error_Ok, "heif_context_write_to_file() == ok（写出 .jpg）");

    /* ---- 8. JPEG 解码（libheif-jpegdec.so） + 往返一致性 ---- */
    struct heif_context* ctx2 = heif_context_alloc();
    err = ctx2 ? heif_context_read_from_file(ctx2, jpeg_path, NULL) : bad("no context");
    printf("heif_context_read_from_file() -> code=%d\n", err.code);
    check(err.code == heif_error_Ok, "heif_context_read_from_file(.jpg) == ok（JPEG 解码插件读入）");

    struct heif_image_handle* dec_handle = NULL;
    err = ctx2 ? heif_context_get_primary_image_handle(ctx2, &dec_handle) : bad("no context");
    check(err.code == heif_error_Ok && dec_handle != NULL,
          "heif_context_get_primary_image_handle() == ok");

    int dw = dec_handle ? heif_image_handle_get_width(dec_handle) : -1;
    int dh = dec_handle ? heif_image_handle_get_height(dec_handle) : -1;
    printf("decoded handle: %dx%d\n", dw, dh);
    check(dw == W && dh == H, "往返后尺寸仍为 16x16");

    struct heif_image* dec_img = NULL;
    err = dec_handle ? heif_decode_image(dec_handle, &dec_img, heif_colorspace_RGB,
                                         heif_chroma_interleaved_RGB, NULL)
                     : bad("no handle");
    check(err.code == heif_error_Ok && dec_img != NULL, "heif_decode_image(RGB) == ok");

    int ok_pixel = 0;
    if (dec_img) {
        int dstride = 0;
        const uint8_t* dplane =
            heif_image_get_plane_readonly(dec_img, heif_channel_interleaved, &dstride);
        if (dplane) {
            int dr = dplane[0], dg = dplane[1], db = dplane[2];
            printf("  roundtrip pixel[0,0] = RGB(%d,%d,%d)\n", dr, dg, db);
            /* JPEG 有损：纯色块允许 ±10 的量化偏差 */
            ok_pixel = (abs(dr - R) <= 10 && abs(dg - G) <= 10 && abs(db - B) <= 10);
        }
    }
    check(ok_pixel, "往返像素值在 ±10 内（有损 JPEG 编码确实由本包插件完成）");

    /* ---- 9. 生命周期 ---- */
    /* heif_deinit() 在 1.23 返回 void（不是 heif_error）；用「deinit 之后能再次 init」
       作为闭合证据，避免写成恒真断言。 */
    heif_deinit();
    err = heif_init(NULL);
    check(err.code == heif_error_Ok,
          "heif_deinit() 后可再次 heif_init() == ok（生命周期闭合）");
    heif_deinit();

    printf("RESULT: pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
