// kcrash 6.14.0 consumer test (R34: exercises real API).
// Calls KCrash::setDrKonqiEnabled to verify the library links and the
// API is callable.
#include <KCrash>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KCrash::setDrKonqiEnabled(false);
    std::printf("PASS: KCrash::setDrKonqiEnabled OK\n");
    return 0;
}
