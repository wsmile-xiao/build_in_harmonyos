#include <flecs.h>
#include <stdio.h>
#include <assert.h>

typedef struct {
    double x, y;
} Position;

int main(void) {
    ecs_world_t *world = ecs_init();
    assert(world != NULL);

    /* Register the component so ecs_id(Position) symbols exist */
    ECS_COMPONENT(world, Position);

    ecs_entity_t e = ecs_new_w(world, Position);
    assert(e != 0);

    ecs_set(world, e, Position, {10, 20});
    const Position *p = ecs_get(world, e, Position);
    assert(p != NULL);
    assert(p->x == 10 && p->y == 20);

    printf("test flecs 4.1.6: OK (API exercised)\n");
    ecs_fini(world);
    return 0;
}