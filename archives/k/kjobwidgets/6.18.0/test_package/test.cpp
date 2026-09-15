#include <KStatusBarJobTracker>
#include <QApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    KStatusBarJobTracker tracker(nullptr);
    std::printf("PASS: KStatusBarJobTracker constructed OK\n");
    return 0;
}
