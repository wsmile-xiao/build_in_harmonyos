/*
 * test_package 消费者测试 — 真实调用 plutobook C API（R34：禁止空壳测试）
 *
 * 覆盖路径：plutobook_version → plutobook_create → plutobook_load_html
 *           → plutobook_get_page_count → plutobook_pdf_canvas_create
 *           → plutobook_render_document → 产物落盘 → 校验 PDF 魔数与体积
 *
 * 说明：每一步先打印 STEP 行并 fflush，便于在设备/CI 上定位崩溃点
 *      （stdout 无缓冲，SIGSEGV 时不会丢已打印的步骤）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <plutobook.h>

static int failures = 0;

#define STEP(fmt, ...)                                                          \
    do {                                                                        \
        printf("STEP: " fmt "\n", ##__VA_ARGS__);                                \
        fflush(stdout);                                                         \
    } while (0)

#define CHECK(cond, msg)                                                        \
    do {                                                                        \
        if (cond) {                                                             \
            printf("PASS: %s\n", (msg));                                        \
        } else {                                                                \
            printf("FAIL: %s\n", (msg));                                        \
            ++failures;                                                         \
        }                                                                       \
        fflush(stdout);                                                         \
    } while (0)

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    STEP("1 start");
    STEP("2 version_string=%s", plutobook_version_string());
    const char* info = plutobook_build_info();
    STEP("3 build_info len=%zu", info ? strlen(info) : 0);
    STEP("4 version()=%d", plutobook_version());
    CHECK(plutobook_version() > 0, "plutobook_version() > 0");

    STEP("5 create");
    plutobook_t* book = plutobook_create(PLUTOBOOK_PAGE_SIZE_A4, PLUTOBOOK_PAGE_MARGINS_NORMAL,
        PLUTOBOOK_MEDIA_TYPE_PRINT);
    CHECK(book != NULL, "plutobook_create()");
    if (!book)
        return 1;

    static const char html[] =
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<style>h1{color:#003366;font-size:24pt} table{border-collapse:collapse}"
        "td{border:1px solid #333;padding:4px}</style></head>"
        "<body><h1>PlutoBook</h1><p>OpenHarmony cross-build smoke test.</p>"
        "<table><tr><td>alpha</td><td>beta</td></tr>"
        "<tr><td>gamma</td><td>delta</td></tr></table></body></html>";

    STEP("6 load_html");
    // 注意：上游 C 封装的 user_style/user_script/base_url 直接转 std::string_view，
    // 传 NULL 会在 string_view(nullptr) 里 strlen(nullptr) 直接 SIGSEGV（设备 CI 实测
    // Signal 11 / Error 139）；"可选" 必须传空串。
    CHECK(plutobook_load_html(book, html, (int)strlen(html), "", "", ""),
        "plutobook_load_html()");
    STEP("7 get_page_count");
    unsigned int pages = plutobook_get_page_count(book);
    printf("page count: %u\n", pages);
    CHECK(pages >= 1, "plutobook_get_page_count() >= 1");

    const char* out = "plutobook-test.pdf";
    remove(out);
    STEP("8 pdf_canvas_create");
    plutobook_canvas_t* canvas = plutobook_pdf_canvas_create(out, PLUTOBOOK_PAGE_SIZE_A4);
    CHECK(canvas != NULL, "plutobook_pdf_canvas_create()");
    if (canvas) {
        STEP("9 render_document");
        plutobook_render_document(book, canvas);
        STEP("10 canvas_destroy");
        plutobook_canvas_destroy(canvas);
    }
    STEP("11 destroy book");
    plutobook_destroy(book);

    STEP("12 check output file");
    FILE* fp = fopen(out, "rb");
    CHECK(fp != NULL, "pdf output file created");
    if (fp) {
        char magic[4] = {0, 0, 0, 0};
        size_t got = fread(magic, 1, 4, fp);
        fseek(fp, 0, SEEK_END);
        long size = ftell(fp);
        fclose(fp);
        printf("pdf size: %ld bytes\n", size);
        CHECK(got == 4 && memcmp(magic, "%PDF", 4) == 0, "pdf magic is %PDF");
        CHECK(size > 1000, "pdf size > 1000 bytes");
    }

    if (failures) {
        printf("RESULT: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("RESULT: ALL CHECKS PASSED\n");
    fflush(stdout);
    return 0;
}
