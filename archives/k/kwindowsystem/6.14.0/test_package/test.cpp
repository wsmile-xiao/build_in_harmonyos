// kwindowsystem 6.14.0 consumer test (R34: exercises real API).
// Calls KWindowSystem::showingDesktop() to verify the library links and
// the API is callable (returns a bool in any session).
#include <KWindowSystem>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    const bool showing = KWindowSystem::showingDesktop();
    std::printf("PASS: KWindowSystem::showingDesktop OK (%d)\n",
                showing ? 1 : 0);
    return 0;
}
