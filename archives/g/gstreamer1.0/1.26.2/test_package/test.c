#include <gst/gst.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    gst_init(&argc, &argv);
    const gchar *version = gst_version_string();
    printf("gstreamer version: %s\n", version);
    g_assert(version != NULL);
    printf("gstreamer test: PASS\n");
    return 0;
}
