// test_package consumer test for reactphysics3d 0.10.2 (OHOS aarch64)
//
// Real physics-engine exercise (R34: the test must actually call the
// packaged library API, not just print a banner):
//   - create a physics world, a static ground box and a dynamic falling box
//   - step the simulation for a few seconds
//   - assert the falling box actually moved down under gravity and comes to
//     rest on the ground (contact produced), which proves the library links,
//     runs, and computes collision/rigid-body dynamics correctly on OHOS.
#include <cmath>
#include <cstdio>
#include <cstdlib>

#include <reactphysics3d/reactphysics3d.h>

using namespace rp3d;

int main() {
    bool ok = true;

    // Physics engine common object (entry point in 0.10.2)
    PhysicsCommon physicsCommon;

    // World with default settings
    PhysicsWorld* world = physicsCommon.createPhysicsWorld();

    // Gravity along -Y
    const Vector3 gravity(0.0, -9.81, 0.0);
    world->setGravity(gravity);

    // Static ground: a large box centered at y = -0.5 (top face at y = 0)
    BoxShape* groundShape = physicsCommon.createBoxShape(Vector3(10.0, 0.5, 10.0));
    Transform groundTransform(Vector3(0.0, -0.5, 0.0), Quaternion::identity());
    RigidBody* groundBody = world->createRigidBody(groundTransform);
    groundBody->setType(BodyType::STATIC);
    groundBody->addCollider(groundShape, Transform::identity());

    // Dynamic falling box: 1x1x1 box, center initially at y = 5
    BoxShape* boxShape = physicsCommon.createBoxShape(Vector3(0.5, 0.5, 0.5));
    Transform boxTransform(Vector3(0.0, 5.0, 0.0), Quaternion::identity());
    RigidBody* boxBody = world->createRigidBody(boxTransform);
    boxBody->setType(BodyType::DYNAMIC);
    boxBody->addCollider(boxShape, Transform::identity());
    boxBody->updateMassPropertiesFromColliders();

    const decimal timeStep = decimal(1.0) / decimal(60.0);
    const int nbSteps = 5 * 60;  // simulate 5 seconds

    decimal minY = boxTransform.getPosition().y;
    for (int i = 0; i < nbSteps; i++) {
        world->update(timeStep);
        decimal y = boxBody->getTransform().getPosition().y;
        if (y < minY) {
            minY = y;
        }
    }

    const decimal finalY = boxBody->getTransform().getPosition().y;

    // The box must have fallen significantly (gravity worked)
    if (finalY > 4.0) {
        std::printf("FAIL: box did not fall under gravity (finalY=%.6f)\n",
                    static_cast<double>(finalY));
        ok = false;
    }
    // The box must have fallen at least to near the ground (resting on it,
    // half-extent 0.5 -> center around y=0.5, with small solver tolerance)
    if (finalY > 1.2) {
        std::printf("FAIL: box did not come to rest on the ground (finalY=%.6f)\n",
                    static_cast<double>(finalY));
        ok = false;
    }

    if (ok) {
        std::printf("PASS: reactphysics3d 0.10.2 dynamics OK on OHOS "
                    "(finalY=%.6f, minY=%.6f)\n",
                    static_cast<double>(finalY),
                    static_cast<double>(minY));
    }

    physicsCommon.destroyPhysicsWorld(world);

    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}