#include <stdio.h>
#include <string.h>

#include <plutovg.h>

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "plutovg test: %s\n", message); \
            goto cleanup; \
        } \
    } while (0)

int main(void)
{
    int result = 1;
    plutovg_surface_t* surface = NULL;
    plutovg_canvas_t* canvas = NULL;
    plutovg_matrix_t matrix;
    plutovg_matrix_t inverse;
    plutovg_rect_t extents;
    float x = 0;
    float y = 0;
    unsigned char* pixels = NULL;
    FILE* png = NULL;
    unsigned char signature[8];

    CHECK(plutovg_version() == 10303, "version number mismatch");
    CHECK(strcmp(plutovg_version_string(), "1.3.3") == 0, "version string mismatch");

    plutovg_matrix_init_translate(&matrix, 3, 5);
    plutovg_matrix_map(&matrix, 1, 2, &x, &y);
    CHECK(x == 4 && y == 7, "matrix translation failed");
    CHECK(plutovg_matrix_invert(&matrix, &inverse), "matrix inversion failed");
    plutovg_matrix_map(&inverse, x, y, &x, &y);
    CHECK(x == 1 && y == 2, "inverse matrix mapping failed");

    surface = plutovg_surface_create(32, 32);
    CHECK(surface != NULL, "surface creation failed");
    CHECK(plutovg_surface_get_width(surface) == 32, "surface width mismatch");
    CHECK(plutovg_surface_get_height(surface) == 32, "surface height mismatch");
    CHECK(plutovg_surface_get_stride(surface) == 128, "surface stride mismatch");
    CHECK(plutovg_surface_get_data(surface) != NULL, "surface data is null");
    CHECK(plutovg_surface_get_reference_count(surface) == 1, "surface reference count mismatch");

    canvas = plutovg_canvas_create(surface);
    CHECK(canvas != NULL, "canvas creation failed");
    CHECK(plutovg_surface_get_reference_count(surface) == 2, "canvas did not retain surface");

    plutovg_canvas_set_rgb(canvas, 1, 0, 0);
    plutovg_canvas_rect(canvas, 4, 4, 24, 24);
    CHECK(plutovg_canvas_fill_contains(canvas, 16, 16), "fill hit test failed");
    CHECK(!plutovg_canvas_fill_contains(canvas, 1, 1), "fill miss test failed");
    plutovg_canvas_fill_extents(canvas, &extents);
    CHECK(extents.x <= 4 && extents.y <= 4, "fill extents origin mismatch");
    CHECK(extents.w >= 24 && extents.h >= 24, "fill extents size mismatch");
    plutovg_canvas_fill(canvas);

    pixels = plutovg_surface_get_data(surface);
    CHECK(pixels[16 * 128 + 16 * 4] != 0 || pixels[16 * 128 + 16 * 4 + 1] != 0 ||
              pixels[16 * 128 + 16 * 4 + 2] != 0 || pixels[16 * 128 + 16 * 4 + 3] != 0,
          "rasterized center pixel is empty");
    CHECK(pixels[4] == 0 && pixels[5] == 0 && pixels[6] == 0 && pixels[7] == 0,
          "outside pixel was modified");

    plutovg_canvas_set_line_width(canvas, 2);
    CHECK(plutovg_canvas_get_line_width(canvas) == 2, "line width getter mismatch");
    plutovg_canvas_circle(canvas, 16, 16, 8);
    plutovg_canvas_set_rgb(canvas, 0, 0, 1);
    plutovg_canvas_fill(canvas);

    CHECK(plutovg_surface_write_to_png(surface, "plutovg-test.png"), "PNG encoding failed");
    png = fopen("plutovg-test.png", "rb");
    CHECK(png != NULL, "PNG output cannot be opened");
    CHECK(fread(signature, 1, sizeof(signature), png) == sizeof(signature),
          "PNG output is truncated");
    CHECK(signature[0] == 0x89 && signature[1] == 'P' && signature[2] == 'N' && signature[3] == 'G',
          "PNG signature mismatch");
    fclose(png);
    png = NULL;
    remove("plutovg-test.png");

    plutovg_canvas_destroy(canvas);
    canvas = NULL;
    CHECK(plutovg_surface_get_reference_count(surface) == 1, "canvas release failed");

    result = 0;
    printf("plutovg consumer test: version, matrix, rasterization, and PNG output OK\n");

cleanup:
    if (png != NULL)
        fclose(png);
    remove("plutovg-test.png");
    if (canvas != NULL)
        plutovg_canvas_destroy(canvas);
    if (surface != NULL)
        plutovg_surface_destroy(surface);
    return result;
}
