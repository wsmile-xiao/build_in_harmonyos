/* test_package 消费者测试：仅通过 simbody 公开头文件/公开链接目标，
 * 构造单摆多体系统并验证周期（业务有意义的公开 API 调用）。 */
#include <Simbody.h>
#include <cmath>
#include <cstdio>

using namespace SimTK;

int main() {
    MultibodySystem system;
    SimbodyMatterSubsystem matter(system);
    GeneralForceSubsystem forces(system);
    Force::UniformGravity gravity(forces, matter, Vec3(0, -9.8, 0));

    const double L = 1.0, g = 9.8, m = 0.5;
    Body::Rigid pendulumBody(MassProperties(m, Vec3(0), Inertia(1e-3)));
    MobilizedBody::Pin pendulum(matter.Ground(),
        Transform(Vec3(0)),
        pendulumBody, Transform(Vec3(0, L, 0)));

    const double T_analytic = 2*Pi*std::sqrt(L/g);
    system.realizeTopology();
    State st = system.getDefaultState();
    st.updQ()[0] = 5.0*Pi/180.0;
    st.updU()[0] = 0.0;
    system.realize(st, Stage::Velocity);

    RungeKuttaMersonIntegrator integ(system);
    integ.setAccuracy(1e-8);
    TimeStepper ts(system, integ);

    const double dt = 0.005;
    double t = 0.0, q_prev = st.getQ()[0], q_cur = q_prev;
    bool crossed = false;
    ts.initialize(st);
    while (t < 5.0*T_analytic && !crossed) {
        ts.stepTo(t + dt);
        st = ts.getState();
        t = ts.getTime();
        q_cur = st.getQ()[0];
        if (q_cur <= 0.0 && q_prev > 0.0) crossed = true;
        q_prev = q_cur;
    }
    const double T_measured = 4.0*t;
    bool ok = crossed && T_measured >= 0.98*T_analytic && T_measured <= 1.02*T_analytic;
    std::printf("simbody test_package: T_analytic=%.6f T_measured=%.6f crossed=%d -> %s\n",
                T_analytic, T_measured, crossed ? 1 : 0, ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}
