#include <Simbody.h>
#include <iostream>
#include <cassert>

using namespace SimTK;

// Test 1: Vec3 basic algebra (SimTKcommon)
bool test_vec3() {
    Vec3 a(1, 2, 3);
    Vec3 b(4, 5, 6);
    Vec3 c = a + b;
    // Expected (5,7,9)
    if (c[0] != 5 || c[1] != 7 || c[2] != 9) {
        std::cerr << "Vec3 add failed: " << c << std::endl;
        return false;
    }
    double dotVal = dot(a, b); // 1*4+2*5+3*6=32
    if (dotVal != 32) {
        std::cerr << "Vec3 dot failed: " << dotVal << std::endl;
        return false;
    }
    Vec3 cross = a % b; // cross product
    // 1,2,3 x 4,5,6 = (-3,6,-3)
    if (cross[0] != -3 || cross[1] != 6 || cross[2] != -3) {
        std::cerr << "Vec3 cross failed: " << cross << std::endl;
        return false;
    }
    std::cout << "test_vec3 passed: c=" << c << " dot=" << dotVal << " cross=" << cross << std::endl;
    return true;
}

// Test 2: Minimal MultibodySystem (Simbody) — pendulum-like system without visualization
bool test_multibody() {
    try {
        MultibodySystem system;
        SimbodyMatterSubsystem matter(system);
        GeneralForceSubsystem forces(system);
        // Simple pendulum: one body, pin joint, gravity
        Body::Rigid body(MassProperties(1.0, Vec3(0), Inertia(1)));
        MobilizedBody::Pin pendulum(matter.Ground(), Transform(Vec3(0)),
                                    body, Transform(Vec3(0, 1, 0)));
        Force::Gravity gravity(forces, matter, Vec3(0, -9.81, 0));
        system.realizeTopology();
        State state = system.getDefaultState();
        system.realize(state, Stage::Position);
        // Check that system has 1 mobilizer and position vector size
        if (matter.getNumBodies() != 2) { // Ground + pendulum
            std::cerr << "Unexpected body count: " << matter.getNumBodies() << std::endl;
            return false;
        }
        // Verify gravity is present
        if (forces.getNumForces() == 0) {
            std::cerr << "No forces registered" << std::endl;
            return false;
        }
        // Simple dynamics: verify the default mass properties we set on the body
        const MassProperties& mp = body.getDefaultRigidBodyMassProperties();
        if (mp.getMass() != 1.0) {
            std::cerr << "Mass mismatch" << std::endl;
            return false;
        }
        std::cout << "test_multibody passed: bodies=" << matter.getNumBodies()
                  << " forces=" << forces.getNumForces() << std::endl;
        return true;
    } catch (const std::exception& e) {
        std::cerr << "test_multibody exception: " << e.what() << std::endl;
        return false;
    }
}

int main() {
    bool ok1 = test_vec3();
    bool ok2 = test_multibody();
    if (ok1 && ok2) {
        std::cout << "All Simbody tests passed (2/2)" << std::endl;
        return 0;
    } else {
        std::cerr << "Some Simbody tests failed" << std::endl;
        return 1;
    }
}
