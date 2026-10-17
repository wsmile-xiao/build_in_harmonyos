// test_package — joltphysics 5.6.0 smoke test on OpenHarmony PC.
// Derived from upstream HelloWorld/HelloWorld.cpp (CC0-1.0, Jorrit Rouwe):
// simulates a dynamic sphere falling onto a static floor box and steps the
// physics world until the body goes to sleep. Validates library end-to-end
// (allocator hooks, type registration, broadphase/narrowphase, constraints
// solver, job system threads).
#include <Jolt/Jolt.h>

#include <Jolt/RegisterTypes.h>
#include <Jolt/Core/Factory.h>
#include <Jolt/Core/TempAllocator.h>
#include <Jolt/Core/JobSystemThreadPool.h>
#include <Jolt/Physics/PhysicsSettings.h>
#include <Jolt/Physics/PhysicsSystem.h>
#include <Jolt/Physics/Collision/Shape/BoxShape.h>
#include <Jolt/Physics/Collision/Shape/SphereShape.h>
#include <Jolt/Physics/Body/BodyCreationSettings.h>

#include <cstdarg>
#include <cstdio>
#include <iostream>

JPH_SUPPRESS_WARNINGS

using namespace JPH;
using namespace std;

static void TraceImpl(const char *inFMT, ...)
{
    va_list list;
    va_start(list, inFMT);
    char buffer[1024];
    vsnprintf(buffer, sizeof(buffer), inFMT, list);
    va_end(list);
    cout << buffer << endl;
}

namespace Layers
{
    static constexpr ObjectLayer NON_MOVING = 0;
    static constexpr ObjectLayer MOVING = 1;
    static constexpr ObjectLayer NUM_LAYERS = 2;
};

class ObjectLayerPairFilterImpl : public ObjectLayerPairFilter
{
public:
    virtual bool ShouldCollide(ObjectLayer inObject1, ObjectLayer inObject2) const override
    {
        switch (inObject1)
        {
        case Layers::NON_MOVING:
            return inObject2 == Layers::MOVING;
        case Layers::MOVING:
            return true;
        default:
            return false;
        }
    }
};

namespace BroadPhaseLayers
{
    static constexpr BroadPhaseLayer NON_MOVING(0);
    static constexpr BroadPhaseLayer MOVING(1);
    static constexpr uint NUM_LAYERS(2);
};

class BPLayerInterfaceImpl final : public BroadPhaseLayerInterface
{
public:
    BPLayerInterfaceImpl()
    {
        mObjectToBroadPhase[Layers::NON_MOVING] = BroadPhaseLayers::NON_MOVING;
        mObjectToBroadPhase[Layers::MOVING] = BroadPhaseLayers::MOVING;
    }

    virtual uint GetNumBroadPhaseLayers() const override
    {
        return BroadPhaseLayers::NUM_LAYERS;
    }

    virtual BroadPhaseLayer GetBroadPhaseLayer(ObjectLayer inLayer) const override
    {
        return mObjectToBroadPhase[inLayer];
    }

#if defined(JPH_EXTERNAL_PROFILE) || defined(JPH_PROFILE_ENABLED)
    virtual const char *GetBroadPhaseLayerName(BroadPhaseLayer inLayer) const override
    {
        switch ((BroadPhaseLayer::Type)inLayer)
        {
        case (BroadPhaseLayer::Type)BroadPhaseLayers::NON_MOVING: return "NON_MOVING";
        case (BroadPhaseLayer::Type)BroadPhaseLayers::MOVING: return "MOVING";
        default: return "INVALID";
        }
    }
#endif // JPH_EXTERNAL_PROFILE || JPH_PROFILE_ENABLED

private:
    BroadPhaseLayer mObjectToBroadPhase[Layers::NUM_LAYERS];
};

class ObjectVsBroadPhaseLayerFilterImpl : public ObjectVsBroadPhaseLayerFilter
{
public:
    virtual bool ShouldCollide(ObjectLayer inLayer1, BroadPhaseLayer inLayer2) const override
    {
        switch (inLayer1)
        {
        case Layers::NON_MOVING:
            return inLayer2 == BroadPhaseLayers::MOVING;
        case Layers::MOVING:
            return true;
        default:
            return false;
        }
    }
};

int main(int argc, char** argv)
{
    RegisterDefaultAllocator();
    Trace = TraceImpl;

    Factory::sInstance = new Factory();
    RegisterTypes();

    TempAllocatorImpl temp_allocator(10 * 1024 * 1024);
    JobSystemThreadPool job_system(cMaxPhysicsJobs, cMaxPhysicsBarriers, 1);

    const uint cMaxBodies = 1024;
    const uint cNumBodyMutexes = 0;
    const uint cMaxBodyPairs = 1024;
    const uint cMaxContactConstraints = 1024;

    BPLayerInterfaceImpl broad_phase_layer_interface;
    ObjectVsBroadPhaseLayerFilterImpl object_vs_broadphase_layer_filter;
    ObjectLayerPairFilterImpl object_vs_object_layer_filter;

    PhysicsSystem physics_system;
    physics_system.Init(cMaxBodies, cNumBodyMutexes, cMaxBodyPairs, cMaxContactConstraints,
                        broad_phase_layer_interface, object_vs_broadphase_layer_filter, object_vs_object_layer_filter);

    BodyInterface &body_interface = physics_system.GetBodyInterface();

    // Static floor box
    BoxShapeSettings floor_shape_settings(Vec3(100.0f, 1.0f, 100.0f));
    floor_shape_settings.SetEmbedded();
    ShapeSettings::ShapeResult floor_shape_result = floor_shape_settings.Create();
    ShapeRefC floor_shape = floor_shape_result.Get();
    BodyCreationSettings floor_settings(floor_shape, RVec3(Vec3(0.0f, -1.0f, 0.0f)),
                                        Quat::sIdentity(), EMotionType::Static, Layers::NON_MOVING);
    Body *floor = body_interface.CreateBody(floor_settings);
    body_interface.AddBody(floor->GetID(), EActivation::DontActivate);

    // Dynamic sphere
    BodyCreationSettings sphere_settings(new SphereShape(0.5f), RVec3(Vec3(0.0f, 2.0f, 0.0f)),
                                         Quat::sIdentity(), EMotionType::Dynamic, Layers::MOVING);
    BodyID sphere_id = body_interface.CreateAndAddBody(sphere_settings, EActivation::Activate);
    body_interface.SetLinearVelocity(sphere_id, Vec3(0.0f, -5.0f, 0.0f));

    const float cDeltaTime = 1.0f / 60.0f;

    physics_system.OptimizeBroadPhase();

    uint step = 0;
    RVec3 position(0.0f, 2.0f, 0.0f);
    while (body_interface.IsActive(sphere_id))
    {
        ++step;
        position = body_interface.GetCenterOfMassPosition(sphere_id);
        physics_system.Update(cDeltaTime, 1, &temp_allocator, &job_system);
        if (step > 10000)
        {
            cout << "ERROR: sphere never went to sleep" << endl;
            return 1;
        }
    }

    cout << "Simulation finished after " << step << " steps, final position Y = "
         << ((RVec3)position).GetY() << endl;

    // The sphere (radius 0.5) must rest on the floor top (y = 0), so its
    // center must settle at ~0.5 (resting contact), not fall through (y<0).
    float final_y = ((RVec3)position).GetY();
    if (final_y < 0.0f || final_y > 1.5f)
    {
        cout << "ERROR: sphere fell through the floor or flew away, final Y = " << final_y << endl;
        return 1;
    }

    body_interface.RemoveBody(sphere_id);
    body_interface.DestroyBody(sphere_id);
    body_interface.RemoveBody(floor->GetID());
    body_interface.DestroyBody(floor->GetID());

    UnregisterTypes();
    delete Factory::sInstance;
    Factory::sInstance = nullptr;

    cout << "PASS: joltphysics smoke test (sphere resting on floor, Y=" << final_y << ")" << endl;
    return 0;
}
