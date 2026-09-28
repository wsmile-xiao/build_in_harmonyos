/* Consumer smoke test — lasem-render 0.5.1 (MathML/SVG math rendering).
 *
 * Uses only the publicly installed headers (lsmdom.h / lsmdomtypes.h —
 * the MathML/SVG internals are not part of the installed API surface).
 * Actually exercises the public lasem DOM API end-to-end:
 *   1. lsm_dom_document_new_from_memory — parse an inline MathML string
 *   2. lsm_dom_document_get_document_element — DOM root access (math node)
 *   3. lsm_dom_document_create_view + resolution setup
 *   4. lsm_dom_view_get_size_pixels — layout measurement (pango shaping)
 *   5. lsm_dom_view_render onto a caller-provided cairo context — full
 *      render path (MathML layout -> pango glyph shaping -> raster output)
 *   6. lsm_shutdown — library teardown
 *
 * Note: cairo calls are kept minimal (surface/ctx create + status check +
 * destroy) — they link against the same libcairo the lasem library itself
 * was linked with (see liblasem-0.6.so NEEDED entries).
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#include <cairo.h>
#include <lsmdom.h>

static const char *mathml_doc =
    "<math xmlns=\"http://www.w3.org/1998/Math/MathML\">"
    "  <mrow>"
    "    <msup><mi>a</mi><mn>2</mn></msup>"
    "    <mo>+</mo>"
    "    <msup><mi>b</mi><mn>2</mn></msup>"
    "    <mo>=</mo>"
    "    <msup><mi>c</mi><mn>2</mn></msup>"
    "  </mrow>"
    "</math>";

int main(void) {
    LsmDomDocument *document;
    LsmDomElement *root;
    LsmDomView *view;
    cairo_surface_t *surface;
    cairo_t *cairo;
    unsigned int width, height;
    const char *root_name;
    char tmpfile[] = "lasem_smoke_XXXXXX.mml";
    char fontconf[] = "lasem_fonts_XXXXXX.conf";
    int fd;
    FILE *fp;

    /* OHOS ships no /etc/fonts/fonts.conf — without a fontconfig config
     * pango cannot find any font and the MathML layout metrics explode
     * (gigapixel heights, cairo returns CAIRO_STATUS_INVALID_SIZE). Point
     * FONTCONFIG_FILE at a minimal config that exposes /system/fonts,
     * exactly like a desktop session would. */
    fd = mkstemps(fontconf, 5);
    if (fd >= 0) {
        char absconf[512];
        fp = fdopen(fd, "w");
        fputs("<?xml version=\"1.0\"?>\n"
              "<!DOCTYPE fontconfig SYSTEM \"fonts.dtd\">\n"
              "<fontconfig>\n"
              "  <dir>/system/fonts</dir>\n"
              "  <cachedir>/data/tmp/fontconfig-cache</cachedir>\n"
              "</fontconfig>\n", fp);
        fclose(fp);
        /* fontconfig resolves FONTCONFIG_FILE relative to its cwd, which
         * differs between test harnesses — always hand it the absolute
         * path of the temp config we just wrote. */
        if (getcwd(absconf, sizeof(absconf) - 1) != NULL) {
            char full[768];
            snprintf(full, sizeof(full), "%s/%s", absconf, fontconf);
            setenv("FONTCONFIG_FILE", full, 1);
        } else {
            remove(fontconf);
        }
    }

    /* 1: write the inline MathML to a temp file and load it through the
     *    same public loader the lasem-render CLI uses (new_from_path). */
    fd = mkstemps(tmpfile, 4);
    if (fd < 0) {
        fprintf(stderr, "FAIL: cannot create temp file\n");
        return 1;
    }
    fp = fdopen(fd, "w");
    fputs(mathml_doc, fp);
    fclose(fp);

    document = lsm_dom_document_new_from_path(tmpfile, NULL);
    remove(tmpfile);
    if (!LSM_IS_DOM_DOCUMENT(document)) {
        fprintf(stderr, "FAIL: lsm_dom_document_new_from_path returned no document\n");
        remove(fontconf);
        return 1;
    }

    /* 2: DOM root element must be the <math> node */
    root = lsm_dom_document_get_document_element(document);
    if (!LSM_IS_DOM_ELEMENT(root)) {
        fprintf(stderr, "FAIL: document has no root element\n");
        g_object_unref(document);
        return 1;
    }
    root_name = lsm_dom_node_get_node_name(LSM_DOM_NODE(root));
    if (root_name == NULL || strcmp(root_name, "math") != 0) {
        fprintf(stderr, "FAIL: root element is <%s>, expected <math>\n",
                root_name ? root_name : "()");
        g_object_unref(document);
        return 1;
    }

    /* 3: create the rendering view, mirror the upstream suite.c setup:
     *    viewport 480x360 px at 96 dpi before measuring the size. */
    view = lsm_dom_document_create_view(document);
    if (!LSM_IS_DOM_VIEW(view)) {
        fprintf(stderr, "FAIL: lsm_dom_document_create_view returned no view\n");
        g_object_unref(document);
        return 1;
    }
    lsm_dom_view_set_resolution(view, 96);
    {
        LsmBox viewport = {0.0, 0.0, 480.0, 360.0};
        lsm_dom_view_set_viewport_pixels(view, &viewport);
    }

    /* 4: layout measurement — exercises pango text shaping.
     * NOTE: lsm_dom_view_get_size_pixels uses the *initial* values of
     * width/height as the starting layout viewport (see lsmdomview.c —
     * width_pt = *width * 72.0 / resolution_ppi), so they MUST be
     * initialized (garbage stack values make the layout explode to
     * gigapixel heights). */
    width = 0;
    height = 0;
    lsm_dom_view_get_size_pixels(LSM_DOM_VIEW(view), &width, &height, NULL);
    if (width == 0 || height == 0) {
        fprintf(stderr, "FAIL: rendered MathML has zero size (%ux%u)\n", width, height);
        g_object_unref(view);
        g_object_unref(document);
        return 1;
    }

    /* 5: full render onto a cairo image surface */
    surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, width, height);
    cairo = cairo_create(surface);
    if (cairo_status(cairo) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "FAIL: cairo_create failed (status %d)\n", cairo_status(cairo));
        cairo_destroy(cairo);
        cairo_surface_destroy(surface);
        g_object_unref(view);
        g_object_unref(document);
        return 1;
    }
    lsm_dom_view_render(LSM_DOM_VIEW(view), cairo, 1, 1);
    if (cairo_status(cairo) != CAIRO_STATUS_SUCCESS) {
        fprintf(stderr, "FAIL: render failed (cairo status %d)\n", cairo_status(cairo));
        cairo_destroy(cairo);
        cairo_surface_destroy(surface);
        g_object_unref(view);
        g_object_unref(document);
        return 1;
    }
    cairo_destroy(cairo);
    cairo_surface_destroy(surface);

    g_object_unref(view);
    g_object_unref(document);

    /* 6: library teardown */
    lsm_shutdown();
    remove(fontconf);

    printf("PASS: lasem-render 0.5.1 MathML render smoke test "
           "(a^2+b^2=c^2 parsed, root=<math>, laid out %ux%u px, rendered to cairo ARGB32)\n",
           width, height);
    return 0;
}
