#include <gegl.h>
#include <stdio.h>

int main(void) {
    /* Initialize GEGL */
    gegl_init(NULL, NULL);

    /* Create a simple graph: load → save */
    GeglNode *graph = gegl_node_new();
    if (!graph) {
        fprintf(stderr, "FAIL: gegl_node_new returned NULL\n");
        gegl_exit();
        return 1;
    }
    GeglNode *load = gegl_node_new_child(graph,
        "operation", "gegl:load",
        "path", "test_input.png",
        NULL);

    /* Verify the node was created */
    if (!load) {
        fprintf(stderr, "FAIL: gegl_node_new_child returned NULL\n");
        gegl_exit();
        return 1;
    }

    /* Check the operation name */
    const gchar *op = gegl_node_get_operation(load);
    if (!op || g_strcmp0(op, "gegl:load") != 0) {
        fprintf(stderr, "FAIL: operation='%s' (expected 'gegl:load')\n", op ? op : "(null)");
        gegl_exit();
        return 1;
    }

    printf("test gegl 0.4.70: OK (graph created, operation=%s)\n", op);
    gegl_exit();
    return 0;
}
