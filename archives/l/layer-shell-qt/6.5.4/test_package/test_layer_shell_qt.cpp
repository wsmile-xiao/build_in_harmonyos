#include <LayerShellQt/Shell>
#include <LayerShellQt/Window>

#include <QGuiApplication>
#include <QMargins>
#include <QSize>
#include <QWindow>

#include <cstdio>

namespace
{
int checks = 0;
int failures = 0;

void check(bool condition, const char *name)
{
    ++checks;
    if (condition) {
        std::printf("PASS %s\n", name);
    } else {
        ++failures;
        std::printf("FAIL %s\n", name);
    }
}
}

int main(int argc, char **argv)
{
    LayerShellQt::Shell::useLayerShell();
    check(qgetenv("QT_WAYLAND_SHELL_INTEGRATION") == "layer-shell",
          "Shell::useLayerShell sets the integration selector");

    QGuiApplication app(argc, argv);
    QWindow window;
    auto *layer = LayerShellQt::Window::get(&window);
    check(layer != nullptr, "Window::get returns an attached API object");
    check(layer->layer() == LayerShellQt::Window::LayerTop,
          "default layer is LayerTop");
    check(layer->anchors() == (LayerShellQt::Window::AnchorTop
                               | LayerShellQt::Window::AnchorBottom
                               | LayerShellQt::Window::AnchorLeft
                               | LayerShellQt::Window::AnchorRight),
          "default anchors cover all four edges");
    check(layer->margins() == QMargins(), "default margins are zero");
    check(layer->exclusionZone() == 0, "default exclusive zone is zero");
    check(layer->keyboardInteractivity()
              == LayerShellQt::Window::KeyboardInteractivityOnDemand,
          "default keyboard interactivity is on-demand");
    check(layer->screenConfiguration()
              == LayerShellQt::Window::ScreenFromQWindow,
          "default screen configuration follows QWindow");
    check(layer->activateOnShow(), "activate-on-show defaults to true");
    check(layer->closeOnDismissed(), "close-on-dismissed defaults to true");

    layer->setLayer(LayerShellQt::Window::LayerBottom);
    layer->setAnchors(LayerShellQt::Window::Anchors{
        LayerShellQt::Window::AnchorTop,
        LayerShellQt::Window::AnchorLeft,
    });
    layer->setMargins(QMargins(1, 2, 3, 4));
    layer->setExclusiveZone(24);
    layer->setDesiredSize(QSize(640, 480));
    layer->setKeyboardInteractivity(
        LayerShellQt::Window::KeyboardInteractivityNone);
    layer->setScreenConfiguration(
        LayerShellQt::Window::ScreenFromCompositor);
    layer->setActivateOnShow(false);
    layer->setCloseOnDismissed(false);
    layer->setScope(QStringLiteral("conan-consumer"));

    check(layer->layer() == LayerShellQt::Window::LayerBottom,
          "layer setter persists");
    check(layer->anchors()
              == LayerShellQt::Window::Anchors{
                     LayerShellQt::Window::AnchorTop,
                     LayerShellQt::Window::AnchorLeft,
                 },
          "anchors setter persists");
    check(layer->margins() == QMargins(1, 2, 3, 4),
          "margins setter persists");
    check(layer->exclusionZone() == 24, "exclusive-zone setter persists");
    check(layer->desiredSize() == QSize(640, 480),
          "desired-size setter persists");
    check(layer->keyboardInteractivity()
              == LayerShellQt::Window::KeyboardInteractivityNone,
          "keyboard-interactivity setter persists");
    check(layer->screenConfiguration()
              == LayerShellQt::Window::ScreenFromCompositor,
          "screen-configuration setter persists");
    check(!layer->activateOnShow(), "activate-on-show setter persists");
    check(!layer->closeOnDismissed(), "close-on-dismissed setter persists");
    check(layer->scope() == QStringLiteral("conan-consumer"),
          "scope setter persists");

    std::printf("RESULT checks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
