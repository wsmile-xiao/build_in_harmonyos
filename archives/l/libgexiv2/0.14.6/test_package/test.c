/*
 * test_package/test.c — libgexiv2/0.14.6 消费者测试（Conan L1）。
 *
 * 实质调用被测包（R34）：编译期版本宏、运行期 gexiv2_get_version()、
 * gexiv2_initialize()、GExiv2Metadata 打开真实 JPEG（内嵌 base64，
 * 取自上游 test/data/sample-author-badencoding.jpg，614 B）并做
 * set_tag_string → get_tag_string 往返。
 *
 * 另含 1 个 HarmonyOS 专用用例（__OHOS__ 下编译）：用 dlopen/dlsym 复核
 * OHOS 动态加载器能否在运行时解析 libgexiv2.so.2 并取到导出符号 ——
 * OHOS 的加载器/RPATH 语义与 Linux 不同，且要求 .so 具备合法 .codesign
 * （未签名直接拒载），属平台特有风险点。
 */
#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <glib/gstdio.h>
#include <gexiv2/gexiv2.h>

#ifdef __OHOS__
#include <dlfcn.h>
#endif

/* 上游 test/data/sample-author-badencoding.jpg（614 B）的 base64。 */
static const char *SAMPLE_JPEG_B64 =
    "/9j/4AAQSkZJRgABAQEASABIAAD/4QEYRXhpZgAATU0AKgAAAAgACAEPAAIAAAAESFRDAAEQAAIA"
    "AAAKAAAAbgEaAAUAAAABAAAAeAEbAAUAAAABAAAAgAEoAAMAAAABAAIAAAEyAAIAAAAUAAAAiAE7"
    "AAIAAAASAAAAnIdpAAQAAAABAAAArgAAAABIVEMtUDMzMDAAAAAASAAAAAEAAABIAAAAATIwMDc6"
    "MDY6MjkgMDc6MDE6MTIAwOvl6vHg7eTwIMru+OXr5eIAAAaQAAAHAAAABDAyMTCQAwACAAAAFAAA"
    "APySCQADAAAAAQAAAACgAQADAAAAAf//AACgAgAEAAAAAQAABkCgAwAEAAAAAQAABLAAAAAAMjAw"
    "NzowNjoyOSAwNzowMToxMgD/2wBDAP//////////////////////////////////////////////"
    "////////////////////////////////////////wAALCAABAAEBAREA/8QAHwAAAQUBAQEBAQEA"
    "AAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJx"
    "FDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNk"
    "ZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJ"
    "ytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9oACAEBAAA/AJK//9k=";

static int failures = 0;
static int checks = 0;

static void
check(int condition, const char *message)
{
    checks++;
    printf("    [%s] %s\n", condition ? "PASS" : "FAIL", message);
    if (!condition)
        failures++;
}

int
main(void)
{
    /* 无缓冲：崩溃/异常退出时也不丢已完成用例的输出。 */
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("gexiv2 consumer test (test_package)\n");

    printf("  case 1: version triple\n");
    check(GEXIV2_MAJOR_VERSION == 0 && GEXIV2_MINOR_VERSION == 14
              && GEXIV2_MICRO_VERSION == 6,
          "compile-time macros are 0.14.6");
    check(gexiv2_get_version() == GEXIV2_MAJOR_VERSION * 100 * 100
                                      + GEXIV2_MINOR_VERSION * 100
                                      + GEXIV2_MICRO_VERSION,
          "gexiv2_get_version() matches macros");

    printf("  case 2: initialize + metadata round-trip\n");
    check(gexiv2_initialize() == TRUE, "gexiv2_initialize()");

    gsize raw_len = 0;
    guchar *raw = g_base64_decode(SAMPLE_JPEG_B64, &raw_len);
    check(raw != NULL && raw_len > 0, "embedded JPEG decoded");

    gchar *path = g_build_filename(g_get_tmp_dir(), "gexiv2-test_package.jpg", NULL);
    check(g_file_set_contents(path, (const gchar *) raw, (gssize) raw_len, NULL),
          "sample written to temp file");

    GError *error = NULL;
    GExiv2Metadata *md = gexiv2_metadata_new();
    check(md != NULL, "gexiv2_metadata_new()");
    check(gexiv2_metadata_open_path(md, path, &error) == TRUE,
          "gexiv2_metadata_open_path()");
    if (error) {
        printf("      error: %s\n", error->message);
        g_clear_error(&error);
    }

    /* 注意：get_mime_type 是 (transfer none)，返回内部指针，不得 g_free。 */
    const gchar *mime = gexiv2_metadata_get_mime_type(md);
    check(mime != NULL && strcmp(mime, "image/jpeg") == 0,
          "gexiv2_metadata_get_mime_type() == image/jpeg");

    check(gexiv2_metadata_set_tag_string(md, "Exif.Image.Artist", "OpenHarmony"),
          "gexiv2_metadata_set_tag_string(Exif.Image.Artist)");
    gchar *artist = gexiv2_metadata_get_tag_string(md, "Exif.Image.Artist");
    check(artist != NULL && strcmp(artist, "OpenHarmony") == 0,
          "gexiv2_metadata_get_tag_string() round-trip");
    g_free(artist);  /* get_tag_string 是 (transfer full) */

    gexiv2_metadata_free(md);
    g_remove(path);
    g_free(path);
    g_free(raw);

#ifdef __OHOS__
    printf("  case 3: HarmonyOS-specific — dlopen runtime resolution\n");
    void *handle = dlopen("libgexiv2.so.2", RTLD_NOW | RTLD_LOCAL);
    check(handle != NULL, "dlopen(\"libgexiv2.so.2\") on OHOS loader");
    if (handle != NULL) {
        typedef gint (*version_fn)(void);
        version_fn fn = (version_fn) dlsym(handle, "gexiv2_get_version");
        check(fn != NULL, "dlsym(gexiv2_get_version)");
        if (fn != NULL)
            check(fn() == gexiv2_get_version(),
                  "symbol called through OHOS loader returns same version");
        dlclose(handle);
    }
#else
    printf("  case 3: (skipped — not building for OHOS)\n");
#endif

    printf("  summary: %d checks, %d failed\n", checks, failures);
    printf("%s\n", failures == 0 ? "ALL CHECKS PASSED" : "TEST FAILED");
    return failures == 0 ? 0 : 1;
}
