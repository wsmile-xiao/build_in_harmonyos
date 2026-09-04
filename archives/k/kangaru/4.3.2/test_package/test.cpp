// test_package consumer test for kangaru 4.3.2 (header-only DI library).
// Exercises the real public API: service definition, single_service lifecycle,
// container.service<>() retrieval, and dependency autowiring.
#include <cassert>
#include <string>

#include <kangaru/kangaru.hpp>

namespace {

// A plain service type with its own single_service definition.
struct Engine {
    std::string model = "default";

    Engine() = default;
    explicit Engine(std::string m) : model(std::move(m)) {}
};

struct EngineService : kgr::single_service<Engine> {};

// A dependent service: Car autowired with EngineService.
struct Car {
    Engine& engine;
};

struct CarService : kgr::service<Car, kgr::dependency<EngineService>> {};

} // namespace

int main() {
    kgr::container container;

    // 1. single_service lifecycle: same instance is returned across calls.
    Engine& e1 = container.service<EngineService>();
    e1.model = "ohos-engine";
    Engine& e2 = container.service<EngineService>();
    assert(&e1 == &e2);
    assert(e2.model == "ohos-engine");

    // 2. Autowired dependent service resolves its dependency.
    //    Car is a transient service (kgr::service), so it is returned by value.
    Car car = container.service<CarService>();
    assert(&car.engine == &e1);

    // 3. Conditional insertion: emplace actually puts the service in.
    bool inserted = container.emplace<EngineService>();
    assert(inserted);

    // 4. The container refuses duplicate single-service emplacement.
    bool inserted_again = container.emplace<EngineService>();
    assert(!inserted_again);

    return 0;
}