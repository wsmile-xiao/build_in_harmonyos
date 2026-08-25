// kcompletion 6.14.0 consumer test (R34: exercises real API).
#include <KCompletion>
#include <QCoreApplication>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);
    KCompletion comp;
    comp.insertItems(QStringList() << QStringLiteral("alpha") << QStringLiteral("alpine"));
    comp.setCompletionMode(KCompletion::CompletionPopup);
    const QStringList items = comp.allMatches(QStringLiteral("al"));
    if (items.isEmpty()) {
        std::printf("FAIL: no matches\n");
        return 1;
    }
    std::printf("PASS: KCompletion allMatches OK (%d)\n", items.count());
    return 0;
}
