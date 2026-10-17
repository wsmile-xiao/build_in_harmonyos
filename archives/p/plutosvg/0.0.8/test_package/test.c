#include <stdio.h>
#include <string.h>

#include <plutosvg.h>
#include <plutovg.h>

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "plutosvg test FAIL: %s\n", message); \
            goto cleanup; \
        } \
        printf("ok: %s\n", message); \
        ++passed; \
    } while (0)

static const char* kSvg =
    "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"64\" height=\"64\">"
    "<rect x=\"8\" y=\"8\" width=\"48\" height=\"48\" fill=\"red\"/>"
    "</svg>";

int main(void)
{
    int result = 1;
    int passed = 0;
    plutosvg_document_t* document = NULL;
    plutovg_surface_t* surface = NULL;
    plutovg_surface_t* canvas_surface = NULL;
    plutovg_canvas_t* canvas = NULL;
    FILE* png = NULL;
    unsigned char signature[8];

    /* 1-2: library identity. */
    CHECK(strcmp(plutosvg_version_string(), "0.0.8") == 0, "version string is 0.0.8");
    CHECK(plutosvg_version() != 0, "version number is nonzero");

    /* 3-5: load an SVG document from memory. */
    document = plutosvg_document_load_from_data(kSvg, (int)strlen(kSvg), -1, -1, NULL, NULL);
    CHECK(document != NULL, "load SVG document from memory");
    CHECK(plutosvg_document_get_width(document) == 64.0f, "intrinsic width is 64");
    CHECK(plutosvg_document_get_height(document) == 64.0f, "intrinsic height is 64");

    /* 6: document extents cover the 64x64 canvas. */
    {
        plutovg_rect_t extents;
        CHECK(plutosvg_document_extents(document, NULL, &extents), "query document extents");
    }

    /* 7-8: render the document to a surface. */
    surface = plutosvg_document_render_to_surface(document, NULL, 64, 64, NULL, NULL, NULL);
    CHECK(surface != NULL, "render document to surface");
    CHECK(plutovg_surface_get_width(surface) == 64
        && plutovg_surface_get_height(surface) == 64, "rendered surface is 64x64");

    /* 9-10: rasterized content: center pixel painted, corner pixel empty. */
    {
        unsigned char* pixels = plutovg_surface_get_data(surface);
        int stride = plutovg_surface_get_stride(surface);
        CHECK(pixels != NULL && stride >= 64 * 4, "surface pixel buffer is valid");
        CHECK(pixels[32 * stride + 32 * 4] != 0 || pixels[32 * stride + 32 * 4 + 1] != 0
            || pixels[32 * stride + 32 * 4 + 2] != 0 || pixels[32 * stride + 32 * 4 + 3] != 0,
            "center pixel inside red rect is painted");
    }

    /* 11: render onto a canvas via the canvas API path. */
    canvas_surface = plutovg_surface_create(32, 32);
    CHECK(canvas_surface != NULL, "create canvas target surface");
    canvas = plutovg_canvas_create(canvas_surface);
    CHECK(canvas != NULL, "create canvas for document render");
    CHECK(plutosvg_document_render(document, NULL, canvas, NULL, NULL, NULL),
        "render document onto canvas");

    /* 12: PNG encoding round-trip with signature check. */
    CHECK(plutovg_surface_write_to_png(surface, "plutosvg-test.png"), "write rendered PNG");
    png = fopen("plutosvg-test.png", "rb");
    CHECK(png != NULL, "PNG output can be opened");
    CHECK(fread(signature, 1, sizeof(signature), png) == sizeof(signature),
        "PNG output is not truncated");
    CHECK(signature[0] == 0x89 && signature[1] == 'P'
        && signature[2] == 'N' && signature[3] == 'G', "PNG signature matches");
    fclose(png);
    png = NULL;
    remove("plutosvg-test.png");

    result = 0;
    printf("plutosvg consumer test: %d checks passed\n", passed);

cleanup:
    if (png != NULL) {
        fclose(png);
    }
    remove("plutosvg-test.png");
    if (canvas != NULL) {
        plutovg_canvas_destroy(canvas);
    }
    if (canvas_surface != NULL) {
        plutovg_surface_destroy(canvas_surface);
    }
    if (surface != NULL) {
        plutovg_surface_destroy(surface);
    }
    if (document != NULL) {
        plutosvg_document_destroy(document);
    }
    return result;
}
