// ki18n 6.14.0.1 consumer test (R34: exercises real API).
// Part 1: core KLocalizedString formatting.
// Part 2: QML-capable context object KLocalizedContext (main lib).
// Part 3: the NEW QML add-on of this revision, KLocalizedQmlContext
//         (KF6I18nQml / libKF6I18nQml.so) — the exact class
//         KF6NewStuff's widgets/dialog.cpp instantiates with a QQmlEngine.
//         Without this add-on knewstuff cannot build, so its real
//         behaviour is the regression test for 6.14.0 -> 6.14.0.1.
#include <KLocalizedContext>
#include <KLocalizedQmlContext>
#include <KLocalizedString>

#include <QCoreApplication>
#include <QQmlEngine>
#include <QString>

#include <cstdio>

static int failures = 0;

#define CHECK(cond)                                                \
    do {                                                           \
        if (!(cond)) {                                             \
            std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);  \
            ++failures;                                            \
        }                                                          \
    } while (0)

int main(int argc, char **argv)
{
    // QQmlEngine wraps a QJSEngine which aborts without a core app.
    QCoreApplication app(argc, argv);

    // Part 1: core formatting round-trip
    const QString s = ki18n("hello %1")
                          .subs(QStringLiteral("world"))
                          .toString();
    CHECK(s == QStringLiteral("hello world"));

    // Part 2: KLocalizedContext domain property + untranslated pass-through
    {
        KLocalizedContext context;
        context.setTranslationDomain(QStringLiteral("ki18n_consumer_test"));
        CHECK(context.translationDomain()
              == QStringLiteral("ki18n_consumer_test"));
        // no catalog installed -> i18n() must fall back to the source text
        CHECK(context.i18n(QStringLiteral("cheerio"))
              == QStringLiteral("cheerio"));
    }

    // Part 3: KF6I18nQml add-on (the reason this revision exists)
    {
        QQmlEngine engine;
        KLocalizedQmlContext qmlContext(&engine);
        qmlContext.setTranslationDomain(QStringLiteral("ki18n_consumer_test"));
        CHECK(qmlContext.i18n(QStringLiteral("hello qml"))
              == QStringLiteral("hello qml"));
        CHECK(qmlContext.i18nc(QStringLiteral("ctx"),
                               QStringLiteral("greet"))
              == QStringLiteral("greet"));
    }

    if (failures == 0) {
        std::printf("PASS: ki18n core + QML add-on API exercised\n");
        return 0;
    }
    std::printf("FAILED: %d checks\n", failures);
    return 1;
}
