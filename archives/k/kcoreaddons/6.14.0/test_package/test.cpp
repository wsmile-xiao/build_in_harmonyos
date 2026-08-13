// kcoreaddons 6.14.0 consumer test (R34: exercises real KF6CoreAddons API).
// Constructs a KAboutData object and verifies basic fields round-trip.
#include <KAboutData>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KAboutData about(QStringLiteral("testapp"),
                     QStringLiteral("Test App"),
                     QStringLiteral("1.2.3"));
    if (about.componentName() != QStringLiteral("testapp")) {
        std::printf("FAIL: componentName mismatch: %s\n",
                    about.componentName().toUtf8().constData());
        return 1;
    }
    if (about.displayName() != QStringLiteral("Test App")) {
        std::printf("FAIL: displayName mismatch: %s\n",
                    about.displayName().toUtf8().constData());
        return 1;
    }
    if (about.version() != QStringLiteral("1.2.3")) {
        std::printf("FAIL: version mismatch: %s\n",
                    about.version().toUtf8().constData());
        return 1;
    }
    std::printf("PASS: KAboutData created (component=%s version=%s)\n",
                about.componentName().toUtf8().constData(),
                about.version().toUtf8().constData());
    return 0;
}
