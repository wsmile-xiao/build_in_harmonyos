// kauth 6.14.0 consumer test (R34: exercises real API).
#include <KAuth/Action>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KAuth::Action action(QStringLiteral("org.test.action"));
    if (action.name() != QStringLiteral("org.test.action")) {
        std::printf("FAIL: action name mismatch\n");
        return 1;
    }
    std::printf("PASS: KAuth::Action constructed OK (%s)\n",
                qPrintable(action.name()));
    return 0;
}
