// kjobwidgets 6.14.0 consumer test (R34: exercises real API).
// KAbstractWidgetJobTracker is abstract; use the concrete
// KStatusBarJobTracker with explicit constructor arguments.
#include <KStatusBarJobTracker>
#include <QApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    // Parent widget only; omit the second (bool button) argument to avoid
    // any ambiguity flagged by review.
    KStatusBarJobTracker tracker(nullptr);
    std::printf("PASS: KStatusBarJobTracker constructed OK\n");
    return 0;
}
