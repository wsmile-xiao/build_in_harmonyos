#include <entt/entt.hpp>

#include <cstdint>
#include <cstdio>

struct Position { float x; float y; };
struct Velocity { float dx; float dy; };

// Free function for signal connect
static int g_signal_value = 0;
static void on_signal(int v) { g_signal_value = v; }

struct MyEvent { int value; };
static int g_dispatch_value = 0;
static void on_event(MyEvent ev) { g_dispatch_value = ev.value; }

int main() {
    entt::registry registry;

    // Test entity creation and component emplace/get
    const auto entity = registry.create();
    registry.emplace<int>(entity, 42);
    if (registry.get<int>(entity) != 42) {
        std::puts("FAIL: emplace/get<int> mismatch");
        return 1;
    }

    // Test multiple components
    const auto e2 = registry.create();
    registry.emplace<Position>(e2, 1.0f, 2.0f);
    registry.emplace<Velocity>(e2, 0.5f, -1.0f);

    // Test view iteration
    auto view = registry.view<Position, Velocity>();
    int count = 0;
    view.each([&count](auto& pos, auto& vel) {
        pos.x += vel.dx;
        pos.y += vel.dy;
        ++count;
    });
    if (count != 1) {
        std::puts("FAIL: view iteration count mismatch");
        return 1;
    }

    // Verify position was updated
    auto& updated_pos = registry.get<Position>(e2);
    if (updated_pos.x != 1.5f || updated_pos.y != 1.0f) {
        std::puts("FAIL: position update mismatch");
        return 1;
    }

    // Test entity destruction
    registry.destroy(entity);
    if (registry.valid(entity)) {
        std::puts("FAIL: entity should be destroyed");
        return 1;
    }

    // Test signal system (sigh + sink)
    entt::sigh<void(int)> signal;
    entt::sink sink{signal};
    sink.connect<&on_signal>();
    signal.publish(99);
    if (g_signal_value != 99) {
        std::puts("FAIL: signal not received");
        return 1;
    }

    // Test dispatcher
    entt::dispatcher dispatcher;
    dispatcher.sink<MyEvent>().connect<&on_event>();
    dispatcher.trigger<MyEvent>({77});
    if (g_dispatch_value != 77) {
        std::puts("FAIL: dispatcher event not received");
        return 1;
    }

    // Test hashed_string
    using namespace entt::literals;
    auto hs = "test"_hs;
    if (hs == 0u) {
        std::puts("FAIL: hashed_string should not be zero");
        return 1;
    }

    // Test meta system
    entt::meta_factory<int>().type("int"_hs);
    auto type = entt::resolve<int>();
    if (!type) {
        std::puts("FAIL: meta resolve failed");
        return 1;
    }

    std::puts("PASS: entt 4.0.0 registry/signal/dispatcher/meta/hashed_string API checks passed");
    return 0;
}
