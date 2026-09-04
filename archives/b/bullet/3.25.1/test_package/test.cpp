#include <btBulletCollisionCommon.h>
#include <btBulletDynamicsCommon.h>
#include <cstdio>

int main() {
    btBroadphaseInterface* broadphase = new btDbvtBroadphase();
    btDefaultCollisionConfiguration* collisionConfig = new btDefaultCollisionConfiguration();
    btCollisionDispatcher* dispatcher = new btCollisionDispatcher(collisionConfig);
    btSequentialImpulseConstraintSolver* solver = new btSequentialImpulseConstraintSolver();
    btDiscreteDynamicsWorld* world = new btDiscreteDynamicsWorld(
        dispatcher, broadphase, solver, collisionConfig);

    world->setGravity(btVector3(0, -10, 0));

    // Ground plane
    btStaticPlaneShape* groundShape = new btStaticPlaneShape(btVector3(0, 1, 0), 0);
    btDefaultMotionState* groundMS = new btDefaultMotionState(
        btTransform(btQuaternion(0, 0, 0, 1), btVector3(0, 0, 0)));
    btRigidBody::btRigidBodyConstructionInfo groundCI(0, groundMS, groundShape, btVector3(0, 0, 0));
    btRigidBody* ground = new btRigidBody(groundCI);
    world->addRigidBody(ground);

    // Falling sphere
    btSphereShape* sphereShape = new btSphereShape(1.0);
    btDefaultMotionState* sphereMS = new btDefaultMotionState(
        btTransform(btQuaternion(0, 0, 0, 1), btVector3(0, 10, 0)));
    btRigidBody::btRigidBodyConstructionInfo sphereCI(1.0, sphereMS, sphereShape, btVector3(0, 0, 0));
    btRigidBody* sphere = new btRigidBody(sphereCI);
    world->addRigidBody(sphere);

    // Simulate 3 seconds
    for (int i = 0; i < 180; i++) {
        world->stepSimulation(1.0f / 60.0f, 10);
    }

    btTransform trans;
    sphere->getMotionState()->getWorldTransform(trans);
    float y = trans.getOrigin().getY();

    // Sphere should rest on ground (radius=1, ground at y=0)
    if (y > 0.5f && y < 1.5f) {
        printf("PASS: sphere at y=%.2f (expected ~1.0)\n", y);
        return 0;
    } else {
        printf("FAIL: sphere at y=%.2f (expected ~1.0)\n", y);
        return 1;
    }
}
