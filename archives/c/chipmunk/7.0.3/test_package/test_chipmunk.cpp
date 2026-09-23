/* Consumer test for chipmunk/7.0.3 on OHOS PC.
 *
 * Chipmunk2D ships no test suite of its own, so this file carries the real
 * verification of the delivered artifact: a gravity fall, a pin-joint
 * distance invariant, a collision-handler invocation, a static-segment
 * resting contact, a point query, moment-of-inertia maths and the BB
 * helpers — each through the public C API, TAP output, non-zero exit on
 * any failure.
 */
#include <chipmunk/chipmunk.h>

#include <cmath>
#include <cstdio>

static int checks = 0;
static int failures = 0;

static void check(int condition, const char *description) {
    ++checks;
    if (!condition) {
        ++failures;
        printf("not ok %d - %s\n", checks, description);
    } else {
        printf("ok %d - %s\n", checks, description);
    }
}

static cpBool begin_hits(cpArbiter *arb, cpSpace *space, void *data) {
    int *flag = static_cast<int *>(data);
    *flag = 1;
    return cpTrue;
}

int main(void) {
    /* ── space + gravity: a free body must fall ─────────────────────── */
    cpSpace *space = cpSpaceNew();
    check(space != NULL, "cpSpaceNew returns a space");
    cpSpaceSetGravity(space, cpv(0, -100));

    cpBody *ball_body = cpSpaceAddBody(space, cpBodyNew(1.0, 1.0));
    cpBodySetPosition(ball_body, cpv(0, 10));
    cpShape *ball = cpSpaceAddShape(
        space, cpCircleShapeNew(ball_body, 0.5, cpvzero));
    cpShapeSetElasticity(ball, 0.3);
    cpShapeSetFriction(ball, 0.7);

    for (int i = 0; i < 10; ++i) {
        cpSpaceStep(space, 1.0 / 60.0);
    }
    check(cpBodyGetPosition(ball_body).y < 9.0,
          "body falls under gravity after 10 steps");

    /* ── static segment: the falling ball must be caught ────────────── */
    cpBody *static_body = cpSpaceGetStaticBody(space);
    check(static_body != NULL, "space exposes its static body");
    cpShape *floor = cpSpaceAddShape(
        space, cpSegmentShapeNew(static_body, cpv(-50, 0), cpv(50, 0), 0.2));
    cpShapeSetElasticity(floor, 0.9);
    cpShapeSetFriction(floor, 0.8);

    cpBodySetPosition(ball_body, cpv(0, 2));
    cpBodySetVelocity(ball_body, cpv(0, 0));
    for (int i = 0; i < 240; ++i) {
        cpSpaceStep(space, 1.0 / 60.0);
    }
    check(cpBodyGetPosition(ball_body).y > 0.0 && cpBodyGetPosition(ball_body).y < 1.5,
          "ball rests on the static segment above y=0 after bouncing");

    /* ── pin joint: two bodies keep their rest distance ──────────────── */
    cpBody *a = cpSpaceAddBody(space, cpBodyNew(1.0, 1.0));
    cpBody *b = cpSpaceAddBody(space, cpBodyNew(1.0, 1.0));
    cpBodySetPosition(a, cpv(-2, 5));
    cpBodySetPosition(b, cpv(2, 5));
    cpSpaceAddConstraint(
        space, cpPinJointNew(a, b, cpvzero, cpvzero));
    cpSpaceAddShape(space, cpCircleShapeNew(a, 0.3, cpvzero));
    cpSpaceAddShape(space, cpCircleShapeNew(b, 0.3, cpvzero));
    for (int i = 0; i < 30; ++i) {
        cpSpaceStep(space, 1.0 / 60.0);
    }
    cpVect delta = cpvsub(cpBodyGetPosition(b), cpBodyGetPosition(a));
    check(std::fabs(cpvlength(delta) - 4.0) < 0.3,
          "pin joint keeps the two bodies 4 units apart");

    /* ── collision handler: a sweep must raise begin ─────────────────── */
    int hits = 0;
    cpCollisionHandler *handler = cpSpaceAddCollisionHandler(space, 1, 2);
    handler->beginFunc = begin_hits;
    handler->userData = &hits;
    cpBody *left = cpSpaceAddBody(space, cpBodyNew(1.0, 1.0));
    cpBody *right = cpSpaceAddBody(space, cpBodyNew(1.0, 1.0));
    cpBodySetPosition(left, cpv(-10, 20));
    cpBodySetPosition(right, cpv(10, 20));
    cpShape *left_shape = cpSpaceAddShape(
        space, cpCircleShapeNew(left, 0.5, cpvzero));
    cpShape *right_shape = cpSpaceAddShape(
        space, cpCircleShapeNew(right, 0.5, cpvzero));
    cpShapeSetCollisionType(left_shape, 1);
    cpShapeSetCollisionType(right_shape, 2);
    cpBodySetVelocity(left, cpv(20, 0));
    for (int i = 0; i < 120 && !hits; ++i) {
        cpSpaceStep(space, 1.0 / 60.0);
    }
    check(hits == 1, "collision handler begin fires when circles meet");

    /* ── spatial query ───────────────────────────────────────────────── */
    cpShape *found = cpSpacePointQueryNearest(
        space, cpBodyGetPosition(right), 10.0, CP_SHAPE_FILTER_ALL, NULL);
    check(found == right_shape, "cpSpacePointQueryNearest finds the circle");

    /* ── moment maths ────────────────────────────────────────────────── */
    cpFloat moment = cpMomentForCircle(2.0, 0.0, 1.0, cpvzero);
    check(std::fabs(moment - 1.0) < 1e-6,
          "cpMomentForCircle matches m*r^2/2 for a solid disc");

    /* ── bounding boxes ──────────────────────────────────────────────── */
    cpBB bb1 = cpBBNew(0, 0, 1, 1);
    cpBB bb2 = cpBBNew(0.5, 0.5, 2, 2);
    cpBB bb3 = cpBBNew(5, 5, 6, 6);
    check(cpBBIntersects(bb1, bb2) && !cpBBIntersects(bb1, bb3),
          "cpBBIntersects separates overlapping from disjoint boxes");

    cpSpaceFree(space);
    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
