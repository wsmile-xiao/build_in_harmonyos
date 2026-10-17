#include <Box2D/Box2D.h>

#include <cmath>
#include <cstdio>

// Consumer smoke test for liquidfun (Box2D 2.3.0 API + particle system):
// build a world, run gravity steps on a falling box, and verify the
// particle system creates a valid group and particles.
int main(void) {
    b2Vec2 gravity(0.0f, -10.0f);
    b2World world(gravity);

    // 1) Static ground body.
    b2BodyDef groundDef;
    groundDef.position.Set(0.0f, -10.0f);
    b2Body *ground = world.CreateBody(&groundDef);
    b2PolygonShape groundBox;
    groundBox.SetAsBox(50.0f, 10.0f);
    ground->CreateFixture(&groundBox, 0.0f);

    // 2) Dynamic box that should fall under gravity.
    b2BodyDef bodyDef;
    bodyDef.type = b2_dynamicBody;
    bodyDef.position.Set(0.0f, 20.0f);
    b2Body *body = world.CreateBody(&bodyDef);
    b2PolygonShape dynamicBox;
    dynamicBox.SetAsBox(1.0f, 1.0f);
    b2FixtureDef fixtureDef;
    fixtureDef.shape = &dynamicBox;
    fixtureDef.density = 1.0f;
    fixtureDef.friction = 0.3f;
    body->CreateFixture(&fixtureDef);

    // 3) LiquidFun particle system: a small water pool.
    b2ParticleSystemDef psDef;
    b2ParticleSystem *ps = world.CreateParticleSystem(&psDef);
    if (ps == NULL) {
        fprintf(stderr, "CreateParticleSystem failed\n");
        return 1;
    }
    b2ParticleGroupDef pgDef;
    b2PolygonShape shape;
    shape.SetAsBox(10.0f, 5.0f, b2Vec2(0.0f, 15.0f), 0.0f);
    pgDef.shape = &shape;
    b2ParticleGroup *group = ps->CreateParticleGroup(pgDef);
    if (group == NULL) {
        fprintf(stderr, "CreateParticleGroup failed\n");
        return 1;
    }
    const int particles = ps->GetParticleCount();
    if (particles < 50) {  // 10x5 box with default particle radius yields ~91
        fprintf(stderr, "particle count too low: %d\n", particles);
        return 1;
    }

    // 4) Step the world: the box must fall (y decreases), particles must
    //    exist throughout, and nothing may produce NaN.
    float y0 = body->GetPosition().y;
    float timeStep = 1.0f / 60.0f;
    for (int i = 0; i < 300; i++) {
        world.Step(timeStep, 8, 3);
        float y = body->GetPosition().y;
        if (!std::isfinite(y)) {
            fprintf(stderr, "body position went non-finite at step %d\n", i);
            return 1;
        }
    }
    float y1 = body->GetPosition().y;
    if (!(y1 < y0)) {
        fprintf(stderr, "box did not fall: %.3f -> %.3f\n", y0, y1);
        return 1;
    }
    if (ps->GetParticleCount() <= 0) {
        fprintf(stderr, "particles vanished\n");
        return 1;
    }

    printf("liquidfun smoke: PASS (box %.2f -> %.2f, particles %d -> %d)\n",
           y0, y1, particles, ps->GetParticleCount());
    return 0;
}
