#include <stdio.h>
#include <gphoto2/gphoto2.h>

int main() {
    /* Verify the libgphoto2 library can be linked and its API called */
    GPContext *ctx = gp_context_new();
    if (ctx == NULL) {
        fprintf(stderr, "Failed to create gphoto2 context\n");
        return 1;
    }
    /* gp_camera_new allocates a camera handle, verifying the core API works */
    Camera *camera;
    int ret = gp_camera_new(&camera);
    if (ret < GP_OK) {
        fprintf(stderr, "Failed to create camera: %d\n", ret);
        gp_context_unref(ctx);
        return 1;
    }
    printf("libgphoto2 context and camera created successfully\n");
    gp_camera_unref(camera);
    gp_context_unref(ctx);
    return 0;
}
