/* Conan test_package for goocanvas 3.0.0 — exercises real public APIs. */
#include <goocanvas.h>

#include <stdio.h>
#include <stdlib.h>

static int assertions = 0;

#define CHECK(expr) do { \
    assertions++; \
    if (!(expr)) { \
        fprintf(stderr, "FAIL [%d]: %s\n", assertions, #expr); \
        goto cleanup; \
    } \
} while (0)

int main(int argc, char **argv) {
    int result = EXIT_FAILURE;
    GooCanvasItem *root = NULL;
    GooCanvasItem *rect = NULL;
    GooCanvasItem *ellipse = NULL;
    GooCanvasItem *text = NULL;
    gdouble x = 0.0, width = 0.0;
    GooCanvasBounds bounds = { 0, 0, 0, 0 };

    /* Type registration (GObject system, no display needed). */
    CHECK(g_type_is_a(goo_canvas_get_type(), GTK_TYPE_WIDGET));
    CHECK(g_type_is_a(goo_canvas_item_get_type(), G_TYPE_OBJECT));
    CHECK(g_type_is_a(goo_canvas_item_model_get_type(), G_TYPE_OBJECT));

    /* Root group. */
    root = goo_canvas_group_new(NULL);
    CHECK(root != NULL);
    CHECK(GOO_IS_CANVAS_ITEM(root));
    CHECK(goo_canvas_item_get_parent(root) == NULL);
    CHECK(goo_canvas_item_get_n_children(root) == 0);

    /* Rectangle item with NULL parent (parent owns it, so we unref manually). */
    rect = goo_canvas_rect_new(NULL, 10.0, 20.0, 100.0, 50.0,
                               "fill-color", "red", NULL);
    CHECK(rect != NULL);
    CHECK(GOO_IS_CANVAS_ITEM(rect));
    g_object_get(rect, "x", &x, "width", &width, NULL);
    CHECK(x == 10.0);
    CHECK(width == 100.0);
    g_object_set(rect, "x", 25.0, "width", 200.0, NULL);
    g_object_get(rect, "x", &x, "width", &width, NULL);
    CHECK(x == 25.0);
    CHECK(width == 200.0);

    /* Ellipse + text items. */
    ellipse = goo_canvas_ellipse_new(NULL, 50.0, 50.0, 30.0, 40.0,
                                     "line-width", 2.0, NULL);
    CHECK(ellipse != NULL);
    CHECK(GOO_IS_CANVAS_ITEM(ellipse));

    text = goo_canvas_text_new(NULL, "goocanvas test", 5.0, 5.0, -1.0,
                               GOO_CANVAS_ANCHOR_NW, NULL);
    CHECK(text != NULL);
    CHECK(GOO_IS_CANVAS_ITEM(text));

    /* Item bounds query (real geometry computation). */
    goo_canvas_item_get_bounds(rect, &bounds);
    CHECK(bounds.x1 == 25.0);
    CHECK(bounds.y1 == 20.0);

    /* Model creation + property round-trip. */
    {
        GooCanvasItemModel *model = goo_canvas_rect_model_new(NULL, 0.0, 0.0, 10.0, 10.0, NULL);
        gdouble mw = 0.0;
        CHECK(model != NULL);
        CHECK(GOO_IS_CANVAS_ITEM_MODEL(model));
        g_object_get(model, "width", &mw, NULL);
        CHECK(mw == 10.0);
        g_object_unref(model);
    }

    /* If a display is available (gtk_init_check), exercise the widget. */
    if (gtk_init_check(&argc, &argv)) {
        GtkWidget *widget = goo_canvas_new();
        GooCanvas *canvas = NULL;
        GooCanvasItem *canvas_root = NULL;
        gdouble left = 0.0, top = 0.0, right = 0.0, bottom = 0.0;
        CHECK(widget != NULL);
        CHECK(GOO_IS_CANVAS(widget));
        canvas = GOO_CANVAS(widget);
        canvas_root = goo_canvas_get_root_item(canvas);
        CHECK(canvas_root != NULL);
        CHECK(GOO_IS_CANVAS_ITEM(canvas_root));
        goo_canvas_set_bounds(canvas, 0.0, 0.0, 1000.0, 1000.0);
        goo_canvas_get_bounds(canvas, &left, &top, &right, &bottom);
        CHECK(left == 0.0 && top == 0.0 && right == 1000.0 && bottom == 1000.0);
        g_object_unref(widget);
    }

    result = EXIT_SUCCESS;
    fprintf(stderr, "PASS: %d assertions\n", assertions);

cleanup:
    if (text != NULL) {
        g_object_unref(text);
    }
    if (ellipse != NULL) {
        g_object_unref(ellipse);
    }
    if (rect != NULL) {
        g_object_unref(rect);
    }
    if (root != NULL) {
        g_object_unref(root);
    }
    return result;
}
