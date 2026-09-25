#include <KAuth/Action>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KAuth::Action action(QStringLiteral("org.test.action"));
    if (action.name() != QStringLiteral("org.test.action")) {
        std::printf("FAIL: KAuth action name mismatch\n");
        return 1;
    }
    std::printf("PASS: KAuth action constructed OK\n");
    return 0;
}
