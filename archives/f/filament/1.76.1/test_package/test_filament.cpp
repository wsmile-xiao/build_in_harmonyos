// Filament 1.76.1 L1 consumer test (noop backend).
//
// Verifies the packaged engine actually links and runs on HarmonyOS PC
// (aarch64), without requiring a GPU or a window system:
//
//   1. Backend::NOOP is offered by this build            (compiled-in drivers)
//   2. Engine::create(Backend::NOOP)                     (core engine + job system)
//   3. engine->getBackend() reports what we asked for
//   4. Engine::createRenderer()                          (renderer API)
//   5. Engine::createScene() / createView() / createCamera(Entity)
//      + View::setScene / setCamera                      (scene graph + math)
//   6. Renderer::beginFrame(SwapChain) / render(View) / endFrame()
//      on an off-screen swap chain                       (frame loop runs end to end)
//   7. utils::EntityManager create/destroy               (Entity + component storage)
//   8. teardown: destroy every child object, then the engine
//
// The noop backend is always compiled (filament/backend/CMakeLists.txt:54-55)
// and needs no Vulkan/GL driver, which is what makes this runnable headless.

#include <filament/Engine.h>
#include <filament/Renderer.h>
#include <filament/Scene.h>
#include <filament/View.h>
#include <filament/Camera.h>
#include <filament/SwapChain.h>

#include <backend/DriverEnums.h>

#include <utils/Entity.h>
#include <utils/EntityManager.h>

#include <cstdio>

namespace {

int g_failures = 0;

void check(bool cond, const char *what) {
    if (cond) {
        std::printf("  ok   : %s\n", what);
    } else {
        std::printf("  FAIL : %s\n", what);
        ++g_failures;
    }
}

}  // namespace

int main() {
    using namespace filament;
    // `Backend` is declared in filament::backend (backend/DriverEnums.h:175);
    // `using namespace filament` above does not bring it into scope.  Alias it
    // rather than adding a second using-directive, so this stays explicit.
    using Backend = filament::backend::Backend;

    // 1. Backend::NOOP must be part of this build's driver set.
    check(Backend::NOOP == static_cast<Backend>(5),
          "Backend::NOOP enum value present");

    // 2. Core engine on the noop backend — no GPU, no display needed.
    Engine *engine = Engine::create(Backend::NOOP);
    check(engine != nullptr, "Engine::create(Backend::NOOP)");
    if (engine == nullptr) {
        std::fprintf(stderr, "[test_filament] FAILED: engine creation\n");
        return 1;
    }

    // 3. Backend round-trip.
    check(engine->getBackend() == Backend::NOOP,
          "engine->getBackend() == Backend::NOOP");

    // 4. Renderer.
    Renderer *renderer = engine->createRenderer();
    check(renderer != nullptr, "engine->createRenderer()");

    // 5. Scene / View / Camera.
    Scene *scene = engine->createScene();
    check(scene != nullptr, "engine->createScene()");
    View *view = engine->createView();
    check(view != nullptr, "engine->createView()");

    utils::Entity cameraEntity = utils::EntityManager::get().create();
    Camera *camera = engine->createCamera(cameraEntity);
    check(camera != nullptr, "engine->createCamera(entity)");

    if (view != nullptr && scene != nullptr) {
        view->setScene(scene);   // no getter upstream; the call must simply work
        check(true, "view->setScene() accepted the scene");
    }
    if (view != nullptr && camera != nullptr) {
        view->setCamera(camera); // likewise a setter-only API
        check(true, "view->setCamera() accepted the camera");
    }

    // 6. Frame loop on an off-screen swap chain (no native window handle).
    SwapChain *swapChain = engine->createSwapChain(64, 64);
    check(swapChain != nullptr, "engine->createSwapChain(64, 64)");
    if (renderer != nullptr && view != nullptr && swapChain != nullptr) {
        const bool begun = renderer->beginFrame(swapChain);
        check(begun, "Renderer::beginFrame() on the off-screen swap chain");
        // Renderer.h documents that beginFrame returns false once a backend
        // exception has been delivered; render()/endFrame() are not valid then,
        // so the frame body runs only when the frame actually began.
        if (begun) {
            renderer->render(view);
            renderer->endFrame();
            check(true, "Renderer::render(view) + endFrame() completed");
        }
    }

    // 7. Entity bookkeeping (utils library).
    utils::Entity extra = utils::EntityManager::get().create();
    check(!extra.isNull(), "EntityManager::create()");
    utils::EntityManager::get().destroy(extra);

    // 8. Teardown in dependency order.
    if (swapChain != nullptr) engine->destroy(swapChain);
    // A Camera is a component of an Entity, not a standalone destroyable object:
    // Engine.h declares no destroy(Camera*) overload.  Camera.h:53-54 documents
    // the teardown as Engine::destroyCameraComponent(Entity), which takes the
    // entity the camera was created on.
    if (camera != nullptr) engine->destroyCameraComponent(cameraEntity);
    utils::EntityManager::get().destroy(cameraEntity);
    if (view != nullptr) engine->destroy(view);
    if (scene != nullptr) engine->destroy(scene);
    if (renderer != nullptr) engine->destroy(renderer);
    Engine::destroy(&engine);
    check(engine == nullptr, "Engine::destroy() cleared the handle");

    if (g_failures != 0) {
        std::fprintf(stderr, "[test_filament] FAILED: %d assertion(s)\n", g_failures);
        return 1;
    }
    std::printf("[test_filament] PASS: filament 1.76.1 noop engine/renderer/scene OK\n");
    return 0;
}
