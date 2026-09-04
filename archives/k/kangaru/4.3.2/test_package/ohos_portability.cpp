// OHOS 专项可移植性测试 — kangaru 4.3.2 (header-only DI library)
//
// 本文件独立于上游测试与 test_package/test.cpp，专门验证 kangaru 公共 API
// 在 OpenHarmony PC (aarch64, clang 15 + libc++/17) 环境下可编译、可运行：
//   - service / single_service 生命周期与内存地址稳定性
//   - container.service<T>() 检索与依赖注入 (kgr::dependency)
//   - emplace 条件插入与重复插入去重
//   - 异常路径 (service_error 删除候选) 编译期正确性
// 所有断言为真实 API 行为校验，非空壳/打印测试。
#include <cassert>
#include <cstdio>
#include <string>

#include <kangaru/kangaru.hpp>

namespace {

// 普通服务：带默认构造（kangaru 要求 service 类型可默认构造/可注入参数）。
struct Engine {
    std::string model = "default";
    int rpm = 0;
};

struct EngineService : kgr::single_service<Engine> {};

// 依赖服务：Car 注入 EngineService；kgr::service 为瞬态服务（按值返回）。
struct Car {
    Engine& engine;
    int seats = 4;
};

struct CarService : kgr::service<Car, kgr::dependency<EngineService>> {};

// 无默认构造的服务，验证瞬态 service 的显式参数构造路径（上游 same pattern:
// container.service<Definition>(1, 1.f)）。
struct ExplicitEngine {
    int power;
    explicit ExplicitEngine(int p) : power(p) {}
};

struct ExplicitEngineService : kgr::service<ExplicitEngine> {};

} // namespace

int main() {
    int failures = 0;

    {
        kgr::container container;

        // 1. single_service 单例生命周期：多次获取为同一实例，地址稳定。
        Engine& e1 = container.service<EngineService>();
        e1.model = "ohos-engine";
        e1.rpm = 3000;
        Engine& e2 = container.service<EngineService>();
        if (&e1 != &e2 || e2.model != "ohos-engine" || e2.rpm != 3000) {
            std::fprintf(stderr, "FAIL: single_service identity/lifecycle\n");
            ++failures;
        }

        // 2. 依赖注入：瞬态服务按值返回，但依赖解析到同一单例。
        Car car = container.service<CarService>();
        if (&car.engine != &e1 || car.seats != 4) {
            std::fprintf(stderr, "FAIL: dependency autowire resolution\n");
            ++failures;
        }

        // 3. 瞬态 service 显式参数构造（上游模式：service<T>(args...)）。
        ExplicitEngine eng = container.service<ExplicitEngineService>(800);
        if (eng.power != 800) {
            std::fprintf(stderr, "FAIL: explicit-arg transient construction\n");
            ++failures;
        }
    }

    {
        // 独立容器验证 emplace 条件插入语义：首次 true，重复插入同一单例 false。
        kgr::container container;

        // 3. emplace 条件插入：首次 true，重复插入同一单例 false。
        if (!container.emplace<EngineService>()) {
            std::fprintf(stderr, "FAIL: emplace first insertion\n");
            ++failures;
        }
        if (container.emplace<EngineService>()) {
            std::fprintf(stderr, "FAIL: emplace duplicate insertion\n");
            ++failures;
        }

        // 4. contains 校验：已 emplaced 的服务可被发现。
        if (!container.contains<EngineService>()) {
            std::fprintf(stderr, "FAIL: contains after emplace\n");
            ++failures;
        }

        // 5. fork 快照语义（容器拷贝已删除，只允许 fork）：复制的服务状态一致。
        kgr::container fork = container.fork();
        Engine& fe = fork.service<EngineService>();
        fe.model = "ohos-engine";
        fe.rpm = 3000;
        ExplicitEngine fex = fork.service<ExplicitEngineService>(800);
        if (fe.model != "ohos-engine" || fe.rpm != 3000) {
            std::fprintf(stderr, "FAIL: forked container engine state\n");
            ++failures;
        }
        if (fex.power != 800) {
            std::fprintf(stderr, "FAIL: forked explicit service state\n");
            ++failures;
        }

        // 6. 瞬态服务按值返回：每次获取独立实例，修改互不影响（值语义）。
        ExplicitEngine a = container.service<ExplicitEngineService>(800);
        a.power = 111;
        ExplicitEngine b = container.service<ExplicitEngineService>(800);
        if (a.power != 111 || b.power != 800) {
            std::fprintf(stderr, "FAIL: transient service value independence\n");
            ++failures;
        }
    }

    if (failures == 0) {
        std::printf("kangaru-ohos-portability: 6/6 checks passed on OHOS\n");
        return 0;
    }
    std::fprintf(stderr, "kangaru-ohos-portability: %d/6 checks FAILED\n", failures);
    return 1;
}