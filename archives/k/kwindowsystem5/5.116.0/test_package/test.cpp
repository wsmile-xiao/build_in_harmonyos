#include <iostream>

#include <KWindowInfo>
#include <KWindowSystem>
#include <QCoreApplication>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // Real API usage (R34/R51): exercise compiled libKF5WindowSystem entry
    // points.  On OHOS (no X11 / no WM) these query functions return a
    // fallback value without crashing, which still links and invokes the
    // real KWindowSystem implementation.
    KWindowSystem *kws = KWindowSystem::self();
    if (!kws) {
        std::cerr << "FAIL: KWindowSystem::self() returned null" << std::endl;
        return 1;
    }
    std::cout << "KWindowSystem::self() OK" << std::endl;

    const int desktops = KWindowSystem::numberOfDesktops();
    std::cout << "KWindowSystem::numberOfDesktops() = "
              << desktops << std::endl;

    // Build a KWindowInfo for the (invalid-on-OHOS) null window; valid() is
    // expected to be false, which still calls into the real window-info
    // lookup path.
    const KWindowInfo info(0, NET::WMState);
    std::cout << "KWindowInfo(0).valid() = "
              << (info.valid() ? "true" : "false") << std::endl;

    std::cout << "OK: kwindowsystem5 consumer compiled and linked"
              << std::endl;
    return 0;
}
