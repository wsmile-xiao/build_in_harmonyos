#include <stdio.h>
#include <stdlib.h>
#include <chipmunk/chipmunk.h>

/* test_package 消费者验证：真实调用 Chipmunk2D API，
 * 创建一个空间与一个盒子刚体并步进模拟，验证库可达性与基础物理行为。 */
int main(void) {
    cpSpace *space = cpSpaceNew();
    if (!space) {
        printf("FAIL: cpSpaceNew returned NULL\n");
        return 1;
    }

    cpBody *body = cpSpaceAddBody(space, cpBodyNew(10.0f, cpMomentForBox(10.0f, 100.0f, 100.0f)));
    cpShape *shape = cpSpaceAddShape(space, cpBoxShapeNew(body, 100.0f, 100.0f, 0.0f));
    cpSpaceSetGravity(space, cpv(0.0f, -100.0f));

    cpFloat cx0 = cpBodyGetPosition(body).x;
    cpFloat cy0 = cpBodyGetPosition(body).y;
    for (int i = 0; i < 60; i++) {
        cpSpaceStep(space, 1.0f / 60.0f);
    }
    cpFloat cy1 = cpBodyGetPosition(body).y;
    cpFloat vy1 = cpBodyGetVelocity(body).y;

    printf("space=%p body=%p shape=%p gravity=%.1f pos0=(%.3f,%.3f) pos1=(%.3f,%.3f) vel1=(%.3f,%.3f)\n",
           (void *)space, (void *)body, (void *)shape,
           cpSpaceGetGravity(space).y, cx0, cy0,
           cpBodyGetPosition(body).x, cy1, cpBodyGetVelocity(body).x, vy1);

    /* 60 步 1/60s 模拟后，刚体应明显沿 -y 重力方向下落 */
    int ok = (cy1 < cy0 - 10.0f);
    cpShapeFree(shape);
    cpBodyFree(body);
    cpSpaceFree(space);

    printf("chipmunk2d 7.0.3 consumer test: %s\n", ok ? "OK" : "FAIL");
    return ok ? 0 : 1;
}