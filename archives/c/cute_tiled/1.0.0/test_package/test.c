/* test_cute_tiled — 实质调用 cute_tiled 1.0.0 公共 API（tinytiled.h v1.00） */
#define TINYTILED_IMPLEMENTATION
#include <cute_tiled.h>

#include <stdio.h>
#include <string.h>

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "test_map.json";
    tinytiled_map_t* map = tinytiled_load_map_from_file(path, NULL);
    if (!map) {
        fprintf(stderr, "FAIL: failed to load map %s\n", path);
        return 1;
    }
    if (map->width <= 0 || map->height <= 0) {
        fprintf(stderr, "FAIL: invalid map dimensions %dx%d\n", map->width, map->height);
        tinytiled_free_map(map);
        return 1;
    }
    if (!map->layers) {
        fprintf(stderr, "FAIL: map has no layers\n");
        tinytiled_free_map(map);
        return 1;
    }
    printf("PASS: cute_tiled loaded %dx%d map, layers=%s\n",
           map->width, map->height, map->layers->name.ptr ? map->layers->name.ptr : "");
    tinytiled_free_map(map);
    return 0;
}
