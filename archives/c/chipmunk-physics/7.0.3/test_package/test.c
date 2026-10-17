/* Consumer test for chipmunk-physics/7.0.3: runs a real physics simulation
 * (ball falling onto a segment under gravity) and asserts the behavioural
 * outcome, exercising cpSpace/cpBody/cpShape APIs. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include <chipmunk/chipmunk.h>

int
main(void)
{
	cpSpace *space = cpSpaceNew();
	cpSpaceSetGravity(space, cpv(0.0, -100.0));

	cpBody *static_body = cpSpaceGetStaticBody(space);
	cpShape *floor_shape = cpSegmentShapeNew(static_body, cpv(-100.0, 0.0), cpv(100.0, 0.0), 0.0);
	cpShapeSetFriction(floor_shape, 0.7);
	cpShapeSetElasticity(floor_shape, 0.4);
	cpSpaceAddShape(space, floor_shape);

	/* Ball starts 50 units above the floor. */
	cpFloat radius = 5.0;
	cpFloat mass = 1.0;
	cpBody *ball = cpBodyNew(mass, cpMomentForCircle(mass, radius, 0.0, cpvzero));
	cpBodySetPosition(ball, cpv(0.0, 50.0));
	cpShape *ball_shape = cpCircleShapeNew(ball, radius, cpvzero);
	cpShapeSetFriction(ball_shape, 0.7);
	cpShapeSetElasticity(ball_shape, 0.4);
	cpSpaceAddBody(space, ball);
	cpSpaceAddShape(space, ball_shape);

	/* Simulate 3 seconds; the ball must fall, bounce and settle on the floor. */
	for(int i = 0; i < 180; i++)
		cpSpaceStep(space, 1.0 / 60.0);

	cpVect pos = cpBodyGetPosition(ball);
	cpVect vel = cpBodyGetVelocity(ball);
	double speed = sqrt(vel.x * vel.x + vel.y * vel.y);

	printf("ball position=(%.3f, %.3f) speed=%.3f\n", (double)pos.x, (double)pos.y, speed);

	int failed = 0;
	if(fabs((double)pos.y - radius) > 2.0) {
		fprintf(stderr, "FAIL: ball did not settle on the floor (y=%.3f, expected ~%.3f)\n",
		    (double)pos.y, (double)radius);
		failed = 1;
	}
	if(speed > 1.0) {
		fprintf(stderr, "FAIL: ball is still moving (speed=%.3f)\n", speed);
		failed = 1;
	}
	if(fabs((double)pos.x) > 0.001) {
		fprintf(stderr, "FAIL: ball drifted horizontally (x=%.3f)\n", (double)pos.x);
		failed = 1;
	}

	cpSpaceFree(space);

	if(!failed)
		printf("chipmunk consumer test: OK (fall/bounce/settle simulation)\n");
	return failed;
}
