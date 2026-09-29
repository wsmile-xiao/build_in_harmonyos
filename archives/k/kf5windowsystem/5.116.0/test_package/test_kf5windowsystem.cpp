/*
 * test_kf5windowsystem.cpp — consumer test for kf5windowsystem 5.116.0 on
 * HarmonyOS PC.
 *
 * Links KF5::WindowSystem (libKF5WindowSystem.so) and exercises the real
 * KWindowSystem / KWindowEffects API surface, asserting the observable
 * behaviour of the always-compiled dummy backend that OHOS uses:
 *
 *  - The build switches X11 off (CMAKE_DISABLE_FIND_PACKAGE_X11), so the
 *    platform probe must report Platform::Unknown for a non-xcb,
 *    non-wayland QPA (offscreen here) instead of resolving an X11 plugin.
 *  - The platform plugin search finds no candidate (no X11/Wayland plugin
 *    is published for OHOS), so KWindowSystem falls back to
 *    KWindowSystemPrivateDummy and every query returns its documented
 *    default rather than the process aborting.
 *  - KWindowEffects routes through the same wrapper and therefore uses
 *    KWindowEffectsPrivateDummy, whose isEffectAvailable() is false.
 *
 * No display is required: the conanfile test() step exports
 * QT_QPA_PLATFORM=offscreen.
 */
#include <QGuiApplication>

#include <KWindowEffects>
#include <KWindowSystem>

#include <cstdio>

static int failures = 0;

static void check(bool ok, const char *what)
{
    std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok) {
        ++failures;
    }
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);

    std::printf("QPA platform: %s\n", QGuiApplication::platformName().toUtf8().constData());

    // 1. The library is live and the platform probe resolves to Unknown:
    //    the offscreen QPA is neither "xcb" nor "wayland*", and with X11
    //    compiled out there is no xcb plugin that could claim it.
    check(KWindowSystem::platform() == KWindowSystem::Platform::Unknown,
          "KWindowSystem::platform() == Platform::Unknown (no X11/Wayland backend)");

    // 2. The convenience predicates agree with the enum.
    check(!KWindowSystem::isPlatformX11(), "isPlatformX11() == false");
    check(!KWindowSystem::isPlatformWayland(), "isPlatformWayland() == false");

    // 3. The singleton is constructible and exports a stable meta object,
    //    i.e. the class (and its Q_PROPERTYs) is really in the .so.
    KWindowSystem *self = KWindowSystem::self();
    check(self != nullptr && self->metaObject() != nullptr
              && self->metaObject()->className() == QByteArrayLiteral("KWindowSystem"),
          "KWindowSystem::self() returns a live singleton with its meta object");

    // 4. The dummy backend answers its documented defaults.
    check(!KWindowSystem::showingDesktop(), "showingDesktop() == false (dummy backend)");
    check(!KWindowSystem::allowedActionsSupported(),
          "allowedActionsSupported() == false (dummy backend)");

    // 5. A mutating call is accepted and silently ignored by the dummy
    //    backend (no X11 round-trip, no crash, state stays default).
    KWindowSystem::setShowingDesktop(true);
    check(!KWindowSystem::showingDesktop(),
          "setShowingDesktop(true) is a no-op on the dummy backend");

    // 6. KWindowEffects uses the dummy effects implementation too.
    check(!KWindowEffects::isEffectAvailable(KWindowEffects::BlurBehind),
          "KWindowEffects::isEffectAvailable(BlurBehind) == false (dummy backend)");
    check(!KWindowEffects::isEffectAvailable(KWindowEffects::BackgroundContrast),
          "KWindowEffects::isEffectAvailable(BackgroundContrast) == false (dummy backend)");

    std::printf("test_kf5windowsystem: %d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
