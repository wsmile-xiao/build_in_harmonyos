#include <kdl/frames.hpp>
#include <kdl/chain.hpp>
#include <kdl/chainfksolverpos_recursive.hpp>
#include <kdl/chainjnttojacsolver.hpp>
#include <iostream>
#include <cstdlib>

// 自定义断言宏：不依赖 NDEBUG，确保 Release 构建下仍执行检查（R34）
// 失败时打印文件:行号 + 表达式，并以非零退出码终止
#define KDL_CHECK(cond)                                                        \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__                \
                      << ": " #cond << std::endl;                            \
            std::exit(1);                                                      \
        }                                                                      \
    } while (0)

static int g_checks = 0;

int main() {
    // Test 1: Basic frame arithmetic
    KDL::Frame frame1 = KDL::Frame::Identity();
    KDL::Frame frame2(KDL::Rotation::RPY(0.5, 0.2, 0.1),
                      KDL::Vector(1.0, 2.0, 3.0));
    KDL::Frame result = frame1 * frame2;
    KDL_CHECK(result.p.x() == 1.0); ++g_checks;
    KDL_CHECK(result.p.y() == 2.0); ++g_checks;
    KDL_CHECK(result.p.z() == 3.0); ++g_checks;
    std::cout << "Frame arithmetic: PASS" << std::endl;

    // Test 2: Chain creation and forward kinematics
    KDL::Chain chain;
    chain.addSegment(KDL::Segment(KDL::Joint(KDL::Joint::RotZ),
                                  KDL::Frame(KDL::Rotation::Identity(),
                                             KDL::Vector(0.0, 0.0, 1.0))));
    chain.addSegment(KDL::Segment(KDL::Joint(KDL::Joint::RotZ),
                                  KDL::Frame(KDL::Rotation::Identity(),
                                             KDL::Vector(0.0, 0.0, 1.0))));

    KDL::ChainFkSolverPos_recursive fksolver(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    q(0) = 0.5;
    q(1) = 0.3;
    KDL::Frame cartpos;
    int ret = fksolver.JntToCart(q, cartpos);
    KDL_CHECK(ret == 0); ++g_checks;
    std::cout << "Forward kinematics: PASS (ret=" << ret << ")" << std::endl;

    // Test 3: Jacobian
    KDL::ChainJntToJacSolver jacsolver(chain);
    KDL::Jacobian jac(chain.getNrOfJoints());
    ret = jacsolver.JntToJac(q, jac);
    KDL_CHECK(ret == 0); ++g_checks;
    std::cout << "Jacobian: PASS (ret=" << ret << ", cols=" << jac.columns()
              << ")" << std::endl;

    std::cout << "orocos-kdl 1.5.3: ALL " << g_checks << " CHECKS PASSED"
              << std::endl;
    return 0;
}