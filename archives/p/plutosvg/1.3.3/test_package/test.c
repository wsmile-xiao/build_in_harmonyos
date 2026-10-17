#include <plutosvg.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int ver = plutosvg_version();
    const char* vs = plutosvg_version_string();
    if (ver <= 0 || vs == NULL || vs[0] == '\0') {
        fprintf(stderr, "plutosvg version failed\n");
        return 1;
    }

    static const char svg[] =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"8\" height=\"8\">"
        "<rect width=\"8\" height=\"8\" fill=\"#ff0000\"/>"
        "</svg>";

    plutosvg_document_t* doc = plutosvg_document_load_from_data(
        svg, (int)strlen(svg), -1.f, -1.f, NULL, NULL);
    if (!doc) {
        fprintf(stderr, "plutosvg load failed\n");
        return 1;
    }

    float w = plutosvg_document_get_width(doc);
    float h = plutosvg_document_get_height(doc);
    if (w <= 0.f || h <= 0.f) {
        fprintf(stderr, "plutosvg bad size %f %f\n", w, h);
        plutosvg_document_destroy(doc);
        return 1;
    }

    plutovg_surface_t* surface = plutosvg_document_render_to_surface(
        doc, NULL, (int)w, (int)h, NULL, NULL, NULL);
    if (!surface) {
        fprintf(stderr, "plutosvg render failed\n");
        plutosvg_document_destroy(doc);
        return 1;
    }

    plutovg_surface_destroy(surface);
    plutosvg_document_destroy(doc);
    printf("plutosvg version=%s size=%.0fx%.0f\n", vs, w, h);
    return 0;
}
