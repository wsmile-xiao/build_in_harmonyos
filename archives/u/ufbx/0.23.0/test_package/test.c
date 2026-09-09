#include <stdio.h>
#include <string.h>
#include "ufbx.h"

int main(void) {
    /* 构造一个最小的 ASCII FBX 文件,验证 ufbx 实际解析 API */
    const char *fbx_data =
        "FBXHeaderExtension:  {\n"
        "\tFBXHeaderVersion: 1003\n"
        "\tFBXVersion: 6100\n"
        "\tCreator: \"ufbx test\"\n"
        "}\n"
        "Objects:  {\n"
        "}\n";

    ufbx_load_opts opts;
    memset(&opts, 0, sizeof(opts));
    ufbx_error error;
    memset(&error, 0, sizeof(error));

    ufbx_scene *scene = ufbx_load_memory(fbx_data, strlen(fbx_data), &opts, &error);
    if (!scene) {
        fprintf(stderr, "ufbx_load_memory failed: %s\n",
                error.description.data ? error.description.data : "unknown");
        return 1;
    }
    printf("ufbx loaded scene: %u meshes, %u nodes\n",
           (unsigned)scene->meshes.count, (unsigned)scene->nodes.count);
    ufbx_free_scene(scene);
    return 0;
}