/* Homebrew-equivalent consumer test for simple-tiles.
 * Formula test: simplet_map_new() / simplet_map_free().
 */
#include <simple-tiles/simple_tiles.h>
#include <stdio.h>

int main(void) {
    simplet_map_t *map = simplet_map_new();
    if (!map) {
        fprintf(stderr, "simplet_map_new failed\n");
        return 1;
    }
    simplet_map_free(map);
    printf("simple-tiles 0.6.2: simplet_map_new/free OK\n");
    return 0;
}
