#include <KNotification>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KNotification notification(QStringLiteral("test"));
    notification.setTitle(QStringLiteral("smoke"));
    std::printf("PASS: KNotification constructed OK\n");
    return 0;
}
