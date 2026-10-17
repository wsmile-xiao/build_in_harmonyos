// knotifications 6.14.0 consumer test (R34: exercises real API).
#include <KNotification>
#include <QCoreApplication>
#include <cstdio>
int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KNotification *n = new KNotification(QStringLiteral("test"));
    if (!n) { std::printf("FAIL: alloc failed\n"); return 1; }
    delete n;
    std::printf("PASS: KNotification constructed OK\n");
    return 0;
}
