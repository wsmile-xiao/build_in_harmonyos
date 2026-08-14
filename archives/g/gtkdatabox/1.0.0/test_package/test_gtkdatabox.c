#include <gtkdatabox.h>
#include <gtkdatabox_graph.h>
#include <gtkdatabox_points.h>
#include <gtkdatabox_lines.h>
#include <gtkdatabox_bars.h>
#include <gtkdatabox_offset_bars.h>
#include <gtkdatabox_regions.h>
#include <gtkdatabox_markers.h>
#include <gtkdatabox_cross_simple.h>
#include <gtkdatabox_grid.h>
#include <gtkdatabox_ruler.h>
#include <gtkdatabox_scale.h>
#include <gtkdatabox_xyc_graph.h>
#include <gtkdatabox_xyyc_graph.h>

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

#define CHECK_GRAPH(graph) do { \
    GtkDataboxGraph *_graph = (graph); \
    CHECK(_graph != NULL && GTK_DATABOX_IS_GRAPH(_graph)); \
    gtk_databox_graph_set_hide(_graph, TRUE); \
    CHECK(gtk_databox_graph_get_hide(_graph) == TRUE); \
    gtk_databox_graph_set_size(_graph, 5); \
    CHECK(gtk_databox_graph_get_size(_graph) == 5); \
    gtk_databox_graph_set_color(_graph, &color); \
    CHECK(gtk_databox_graph_get_color(_graph) != NULL); \
} while (0)

int main(int argc, char **argv) {
    int result = EXIT_FAILURE;
    gfloat x[3] = { -1.0f, 0.0f, 2.0f };
    gfloat y[3] = { 3.0f, -2.0f, 5.0f };
    gfloat y1[3] = { -1.0f, 0.0f, 1.0f };
    gfloat y2[3] = { 1.0f, 2.0f, 3.0f };
    gfloat hline_vals[2] = { 0.0f, 1.0f };
    gfloat vline_vals[2] = { 0.0f, 2.0f };
    GdkRGBA color = { 0.1, 0.4, 0.8, 1.0 };
    GtkDataboxGraph *points = NULL;
    GtkDataboxGraph *lines = NULL;
    GtkDataboxGraph *bars = NULL;
    GtkDataboxGraph *offset_bars = NULL;
    GtkDataboxGraph *regions = NULL;
    GtkDataboxGraph *markers = NULL;
    GtkDataboxGraph *cross = NULL;
    GtkDataboxGraph *grid = NULL;
    GtkDataboxGraph *grid_array = NULL;
    GtkWidget *ruler = NULL;
    GtkWidget *box = NULL;
    GtkDataboxGraph *box_graph = NULL;
    GList *graphs = NULL;
    gfloat min_x = 0.0f;
    gfloat max_x = 0.0f;
    gfloat min_y = 0.0f;
    gfloat max_y = 0.0f;
    gfloat left = 0.0f;
    gfloat right = 0.0f;
    gfloat top = 0.0f;
    gfloat bottom = 0.0f;

    CHECK(g_type_is_a(gtk_databox_get_type(), GTK_TYPE_WIDGET));
    CHECK(g_type_is_a(gtk_databox_scale_type_get_type(), G_TYPE_ENUM));
    CHECK(g_type_is_a(gtk_databox_graph_get_type(), G_TYPE_OBJECT));
    CHECK(g_type_is_a(gtk_databox_xyc_graph_get_type(), GTK_DATABOX_TYPE_GRAPH));
    CHECK(g_type_is_a(gtk_databox_xyyc_graph_get_type(), GTK_DATABOX_TYPE_GRAPH));

    points = gtk_databox_points_new(3, x, y, &color, 2);
    CHECK(points != NULL);
    CHECK(GTK_DATABOX_IS_POINTS(points));
    CHECK(GTK_DATABOX_IS_XYC_GRAPH(points));
    CHECK(gtk_databox_xyc_graph_get_length(GTK_DATABOX_XYC_GRAPH(points)) == 3);
    CHECK(gtk_databox_xyc_graph_get_maxlen(GTK_DATABOX_XYC_GRAPH(points)) >= 3);
    CHECK(gtk_databox_xyc_graph_get_X(GTK_DATABOX_XYC_GRAPH(points)) == x);
    CHECK(gtk_databox_xyc_graph_get_Y(GTK_DATABOX_XYC_GRAPH(points)) == y);
    CHECK(gtk_databox_graph_calculate_extrema(points, &min_x, &max_x, &min_y, &max_y) == 0);
    CHECK(min_x == -1.0f && max_x == 2.0f && min_y == -2.0f && max_y == 5.0f);
    CHECK_GRAPH(points);

    lines = gtk_databox_lines_new(3, x, y, &color, 2);
    CHECK(lines != NULL);
    CHECK(GTK_DATABOX_IS_LINES(lines));
    CHECK(GTK_DATABOX_IS_XYC_GRAPH(lines));
    CHECK_GRAPH(lines);

    bars = gtk_databox_bars_new(3, x, y, &color, 2);
    CHECK(bars != NULL);
    CHECK(GTK_DATABOX_IS_BARS(bars));
    CHECK(GTK_DATABOX_IS_XYC_GRAPH(bars));
    CHECK_GRAPH(bars);

    offset_bars = gtk_databox_offset_bars_new(3, x, y1, y2, &color, 2);
    CHECK(offset_bars != NULL);
    CHECK(GTK_DATABOX_IS_OFFSET_BARS(offset_bars));
    CHECK(GTK_DATABOX_IS_XYYC_GRAPH(offset_bars));
    CHECK_GRAPH(offset_bars);

    regions = gtk_databox_regions_new(3, x, y1, y2, &color);
    CHECK(regions != NULL);
    CHECK(GTK_DATABOX_IS_REGIONS(regions));
    CHECK(GTK_DATABOX_IS_XYYC_GRAPH(regions));
    CHECK_GRAPH(regions);

    markers = gtk_databox_markers_new(3, x, y, &color, 2, GTK_DATABOX_MARKERS_TRIANGLE);
    CHECK(markers != NULL);
    CHECK(GTK_DATABOX_IS_MARKERS(markers));
    CHECK(GTK_DATABOX_IS_XYC_GRAPH(markers));
    gtk_databox_markers_set_position(GTK_DATABOX_MARKERS(markers), 0, GTK_DATABOX_MARKERS_N);
    gtk_databox_markers_set_label(GTK_DATABOX_MARKERS(markers), 0, GTK_DATABOX_MARKERS_TEXT_NE, "probe", FALSE);
    CHECK_GRAPH(markers);

    cross = gtk_databox_cross_simple_new(&color, 2);
    CHECK(cross != NULL);
    CHECK(GTK_DATABOX_IS_CROSS_SIMPLE(cross));
    CHECK_GRAPH(cross);

    grid = gtk_databox_grid_new(2, 3, &color, 1);
    CHECK(grid != NULL);
    CHECK(GTK_DATABOX_IS_GRID(grid));
    CHECK(gtk_databox_grid_get_hlines(GTK_DATABOX_GRID(grid)) == 2);
    CHECK(gtk_databox_grid_get_vlines(GTK_DATABOX_GRID(grid)) == 3);
    gtk_databox_grid_set_line_style(GTK_DATABOX_GRID(grid), GTK_DATABOX_GRID_DOTTED_LINES);
    CHECK(gtk_databox_grid_get_line_style(GTK_DATABOX_GRID(grid)) == GTK_DATABOX_GRID_DOTTED_LINES);
    CHECK_GRAPH(grid);

    grid_array = gtk_databox_grid_array_new(2, 2, hline_vals, vline_vals, &color, 1);
    CHECK(grid_array != NULL);
    CHECK(GTK_DATABOX_IS_GRID(grid_array));
    CHECK(gtk_databox_grid_get_hline_vals(GTK_DATABOX_GRID(grid_array)) == hline_vals);
    CHECK(gtk_databox_grid_get_vline_vals(GTK_DATABOX_GRID(grid_array)) == vline_vals);
    CHECK_GRAPH(grid_array);

    if (gtk_init_check(&argc, &argv)) {
        box = gtk_databox_new();
        CHECK(box != NULL);
        CHECK(GTK_IS_WIDGET(box));
        CHECK(GTK_IS_DATABOX(box));

        ruler = gtk_databox_ruler_new(GTK_ORIENTATION_HORIZONTAL);
        CHECK(ruler != NULL);
        CHECK(GTK_IS_WIDGET(ruler));
        CHECK(GTK_DATABOX_IS_RULER(ruler));

        gtk_databox_set_ruler_x(GTK_DATABOX(box), GTK_DATABOX_RULER(ruler));
        CHECK(gtk_databox_get_ruler_x(GTK_DATABOX(box)) == GTK_DATABOX_RULER(ruler));

        gtk_databox_set_scale_type_x(GTK_DATABOX(box), GTK_DATABOX_SCALE_LOG);
        gtk_databox_set_scale_type_y(GTK_DATABOX(box), GTK_DATABOX_SCALE_LOG2);
        CHECK(gtk_databox_get_scale_type_x(GTK_DATABOX(box)) == GTK_DATABOX_SCALE_LOG);
        CHECK(gtk_databox_get_scale_type_y(GTK_DATABOX(box)) == GTK_DATABOX_SCALE_LOG2);

        gtk_databox_set_total_limits(GTK_DATABOX(box), -10.0f, 10.0f, 10.0f, -10.0f);
        gtk_databox_get_total_limits(GTK_DATABOX(box), &left, &right, &top, &bottom);
        CHECK(left == -10.0f && right == 10.0f && top == 10.0f && bottom == -10.0f);

        gtk_databox_set_enable_selection(GTK_DATABOX(box), TRUE);
        gtk_databox_set_enable_zoom(GTK_DATABOX(box), TRUE);
        CHECK(gtk_databox_get_enable_selection(GTK_DATABOX(box)) == TRUE);
        CHECK(gtk_databox_get_enable_zoom(GTK_DATABOX(box)) == TRUE);

        box_graph = gtk_databox_points_new(3, x, y, &color, 2);
        CHECK(box_graph != NULL);
        CHECK(gtk_databox_graph_add(GTK_DATABOX(box), box_graph) == 0);
        graphs = gtk_databox_get_graphs(GTK_DATABOX(box));
        CHECK(g_list_length(graphs) == 1);
        CHECK(gtk_databox_auto_rescale(GTK_DATABOX(box), 0.0f) == 0);
        CHECK(gtk_databox_graph_remove(GTK_DATABOX(box), box_graph) == 0);
    }

    result = EXIT_SUCCESS;
    fprintf(stderr, "PASS: %d assertions\n", assertions);

cleanup:
    if (box_graph != NULL) {
        g_object_unref(box_graph);
    }
    if (grid_array != NULL) {
        g_object_unref(grid_array);
    }
    if (grid != NULL) {
        g_object_unref(grid);
    }
    if (cross != NULL) {
        g_object_unref(cross);
    }
    if (markers != NULL) {
        g_object_unref(markers);
    }
    if (regions != NULL) {
        g_object_unref(regions);
    }
    if (offset_bars != NULL) {
        g_object_unref(offset_bars);
    }
    if (bars != NULL) {
        g_object_unref(bars);
    }
    if (lines != NULL) {
        g_object_unref(lines);
    }
    if (points != NULL) {
        g_object_unref(points);
    }
    if (ruler != NULL && GTK_IS_WIDGET(ruler)) {
        gtk_widget_destroy(ruler);
    }
    if (box != NULL && GTK_IS_WIDGET(box)) {
        gtk_widget_destroy(box);
    }
    return result;
}