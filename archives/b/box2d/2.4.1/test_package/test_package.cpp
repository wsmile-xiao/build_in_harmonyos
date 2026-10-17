#include <box2d/box2d.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {

bool check(bool condition, const char* message)
{
    if (!condition) {
        std::printf("FAILED: %s\n", message);
        return false;
    }
    return true;
}

} // namespace

int main()
{
    b2World world(b2Vec2(0.0f, -10.0f));

    b2BodyDef ground_def;
    ground_def.position.Set(0.0f, -10.0f);
    b2Body* ground = world.CreateBody(&ground_def);
    b2PolygonShape ground_shape;
    ground_shape.SetAsBox(50.0f, 10.0f);
    ground->CreateFixture(&ground_shape, 0.0f);

    b2BodyDef body_def;
    body_def.type = b2_dynamicBody;
    body_def.position.Set(0.0f, 4.0f);
    b2Body* body = world.CreateBody(&body_def);
    b2PolygonShape body_shape;
    body_shape.SetAsBox(1.0f, 1.0f);
    b2FixtureDef fixture_def;
    fixture_def.shape = &body_shape;
    fixture_def.density = 1.0f;
    fixture_def.friction = 0.3f;
    body->CreateFixture(&fixture_def);

    bool passed = true;
    passed = check(world.GetBodyCount() == 2, "world contains two bodies") && passed;
    passed = check(ground->GetType() == b2_staticBody, "ground body is static") && passed;
    passed = check(body->GetType() == b2_dynamicBody, "dynamic body type") && passed;
    passed = check(body->IsAwake(), "dynamic body starts awake") && passed;

    for (int i = 0; i < 60; ++i) {
        world.Step(1.0f / 60.0f, 6, 2);
    }

    const b2Vec2 position = body->GetPosition();
    passed = check(std::fabs(position.x) < 0.01f && std::fabs(position.y - 1.01f) < 0.01f,
                   "falling body rests on the ground") && passed;

    if (!passed) {
        return EXIT_FAILURE;
    }

    std::printf("box2d consumer test passed\n");
    return EXIT_SUCCESS;
}
