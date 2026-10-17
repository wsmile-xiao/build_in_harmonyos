/*
 * harmonyos_compose_test.c — HarmonyOS 专项测试（R05 新增）for appstream 1.2.0
 *
 * 通过 libappstream-compose 公开 API（安装头 appstream-compose.h / asc-media.h，
 * 链接 libappstream-compose.a 正常目标）驱动真实的 media worker 进程处理一张
 * PNG 图片，验证 R05 修复链端到端可用：
 *   1. asc_media_supports_image_format("png") == TRUE
 *      （vips/8.18.4.1 启用 PNG loader 后 mediaworker backend 具备 PNG 能力）
 *   2. asc_media_supports_image_format("jxl") == FALSE
 *      （libjxl 在 ohpcd 与系统均不可得，能力如实为缺）
 *   3. asc_media_process_image 真实处理 PNG：原始尺寸 136x144、按高 64 等比
 *      缩放后 60x64、超出仅降级策略的 4000 宽目标被跳过 —— 与上游
 *      as-test_compose MediaImage 断言一致，但经公开 API 走完整 worker 链
 *
 * 不包含库私有头文件，不调用内部符号，不复用库内部测试构建目录。
 */
#include <appstream-compose.h>
#include <asc-media.h>
#include <glib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                               \
    do {                                                               \
        if (!(cond)) {                                                 \
            fprintf(stderr, "FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
            failures++;                                                \
        } else {                                                       \
            printf("ok: %s\n", msg);                                   \
        }                                                              \
    } while (0)

static gchar *
asx_load_png_sample (const gchar *datadir, gsize *len_out, GError **error)
{
    g_autofree gchar *fname = NULL;
    gchar *data = NULL;
    gsize len = 0;

    fname = g_build_filename (datadir, "appstream-logo.png", NULL);
    if (!g_file_get_contents (fname, &data, &len, error))
        return NULL;
    *len_out = len;
    return data;
}

int
main (int argc, char **argv)
{
    const gchar *datadir;
    g_autoptr(AscMedia) media = NULL;
    g_autoptr(GError) error = NULL;
    g_autoptr(GBytes) img_bytes = NULL;
    g_autoptr(AscImageSource) source = NULL;
    g_autoptr(GPtrArray) targets = NULL;
    g_autofree gchar *data = NULL;
    g_autofree gchar *out_dir = NULL;
    gsize data_len = 0;
    AscImageTarget *target;
    gboolean ret;

    if (argc <= 1) {
        fprintf(stderr, "Usage: %s <datadir>\n", argv[0]);
        return 2;
    }
    datadir = argv[1];

    /* 读取官方样例 PNG（tests/samples/compose/appstream-logo.png） */
    data = asx_load_png_sample (datadir, &data_len, &error);
    CHECK(data != NULL, "load appstream-logo.png sample");
    if (data == NULL) {
        fprintf(stderr, "  error: %s\n", error ? error->message : "?");
        return 1;
    }
    img_bytes = g_bytes_new_take (g_steal_pointer (&data), data_len);

    /* 公开 API：创建 media 客户端并拉起真实 worker 进程 */
    media = asc_media_new ();
    CHECK(media != NULL, "asc_media_new() returns object");
    if (media == NULL)
        return 1;

    ret = asc_media_ensure_worker (media, NULL, &error);
    CHECK(ret, "asc_media_ensure_worker() spawns media worker");
    if (!ret) {
        fprintf(stderr, "  worker error: %s\n", error ? error->message : "?");
        return 1;
    }

    /* 能力查询：PNG 必须可用（R05 核心：vips 8.18.4.1 启用 PNG） */
    CHECK(asc_media_supports_image_format (media, "png"),
          "asc_media_supports_image_format(png) == TRUE (vips PNG enabled)");
    /* 能力查询：JPEG-XL 如实不可用（libjxl 缺） */
    CHECK(!asc_media_supports_image_format (media, "jxl"),
          "asc_media_supports_image_format(jxl) == FALSE (libjxl absent)");

    /* 公开 API：处理图片（先只读尺寸，不渲染） */
    source = asc_image_source_new (img_bytes);
    CHECK(source != NULL, "asc_image_source_new() succeeds");
    if (source == NULL)
        return 1;

    ret = asc_media_process_image (media, source, NULL, NULL, NULL, &error);
    CHECK(ret, "asc_media_process_image() reads image dimensions");
    if (!ret) {
        fprintf(stderr, "  process error: %s\n", error ? error->message : "?");
        return 1;
    }
    CHECK(asc_image_source_get_width (source) == 136, "source width == 136");
    CHECK(asc_image_source_get_height (source) == 144, "source height == 144");

    /* 公开 API：渲染 3 个目标（原尺寸 / 等比缩放 / 仅降级超界跳过） */
    out_dir = g_build_filename (datadir, "..", "harmonyos-compose-out", NULL);
    if (g_file_test (out_dir, G_FILE_TEST_EXISTS))
        as_utils_delete_dir_recursive (out_dir);

    targets = g_ptr_array_new_with_free_func ((GDestroyNotify) asc_image_target_free);
    g_ptr_array_add (targets, asc_image_target_new ("orig.png", ASC_IMAGE_SCALE_MODE_NONE, 0, 0));
    g_ptr_array_add (targets,
                     asc_image_target_new ("64.png", ASC_IMAGE_SCALE_MODE_FIT_HEIGHT, 0, 64));
    target = asc_image_target_new ("4000.png", ASC_IMAGE_SCALE_MODE_FIT_WIDTH, 4000, 0);
    asc_image_target_set_only_downscale (target, TRUE);
    g_ptr_array_add (targets, target);

    ret = asc_media_process_image (media, source, targets, out_dir, NULL, &error);
    CHECK(ret, "asc_media_process_image() renders targets");
    if (!ret) {
        fprintf(stderr, "  render error: %s\n", error ? error->message : "?");
        return 1;
    }

    target = g_ptr_array_index (targets, 0);
    CHECK(!asc_image_target_get_skipped (target), "orig.png not skipped");
    CHECK(asc_image_target_get_error_message (target) == NULL, "orig.png no error");
    CHECK(asc_image_target_get_result_width (target) == 136, "orig.png width == 136");
    CHECK(asc_image_target_get_result_height (target) == 144, "orig.png height == 144");

    target = g_ptr_array_index (targets, 1);
    CHECK(!asc_image_target_get_skipped (target), "64.png not skipped");
    CHECK(asc_image_target_get_error_message (target) == NULL, "64.png no error");
    CHECK(asc_image_target_get_result_height (target) == 64, "64.png height == 64");
    CHECK(asc_image_target_get_result_width (target) == 60, "64.png width == 60");

    target = g_ptr_array_index (targets, 2);
    CHECK(asc_image_target_get_skipped (target), "4000.png skipped (only-downscale)");
    CHECK(asc_image_target_get_error_message (target) == NULL, "4000.png no error");

    {
        g_autofree gchar *orig = g_build_filename (out_dir, "orig.png", NULL);
        g_autofree gchar *scaled = g_build_filename (out_dir, "64.png", NULL);
        CHECK(g_file_test (orig, G_FILE_TEST_EXISTS), "orig.png written to out dir");
        CHECK(g_file_test (scaled, G_FILE_TEST_EXISTS), "64.png written to out dir");
    }

    if (failures == 0) {
        printf("\nPASS: appstream-compose HarmonyOS media test (all checks ok)\n");
        return 0;
    }
    fprintf(stderr, "\nFAIL: %d check(s) failed\n", failures);
    return 1;
}
