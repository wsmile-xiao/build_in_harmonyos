#include <sord/sord.h>

#include <stdbool.h>
#include <stdio.h>

int
main(void)
{
  SordWorld* world = sord_world_new();
  if (!world) {
    fprintf(stderr, "sord_world_new failed\n");
    return 1;
  }

  SordModel* model = sord_new(world, SORD_SPO | SORD_OPS, false);
  if (!model) {
    fprintf(stderr, "sord_new failed\n");
    sord_world_free(world);
    return 1;
  }

  sord_free(model);
  sord_world_free(world);
  printf("sord C API smoke test OK\n");
  return 0;
}
