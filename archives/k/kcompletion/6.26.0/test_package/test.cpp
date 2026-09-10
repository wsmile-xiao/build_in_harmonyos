// kcompletion 6.26.0 consumer test (R34: exercises real API).
// Constructs a KCompletion and verifies prefix matching behavior.
#include <KCompletion>
#include <QCoreApplication>
#include <QStringList>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    KCompletion completion;
    completion.setItems(QStringList{
        QStringLiteral("alpha"),
        QStringLiteral("alpine"),
        QStringLiteral("beta"),
    });

    const QStringList matches = completion.allMatches(QStringLiteral("alp"));
    if (!matches.contains(QStringLiteral("alpha"))) {
        std::fprintf(stderr, "FAIL: alpha was not matched\n");
        return 1;
    }
    if (!matches.contains(QStringLiteral("alpine"))) {
        std::fprintf(stderr, "FAIL: alpine was not matched\n");
        return 1;
    }
    if (matches.contains(QStringLiteral("beta"))) {
        std::fprintf(stderr, "FAIL: beta was unexpectedly matched\n");
        return 1;
    }

    std::printf("PASS: KCompletion prefix matching OK (%d matches)\n",
                static_cast<int>(matches.size()));
    return 0;
}
