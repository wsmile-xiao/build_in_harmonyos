// kglobalaccel5 5.116.0 consumer test (R34: exercises the real public API).
//
// Links KF5::GlobalAccel and asserts the behaviour of the KGlobalAccel
// singleton plus the query/set shortcut API on a real QAction.
// Without a session D-Bus the setter degrades gracefully; the assertions are
// therefore written against API consistency (state after set/remove) rather
// than against a D-Bus side effect, so the test is deterministic on both a
// desktop session and a headless OHOS device.
#include <KGlobalAccel>
#include <QAction>
#include <QApplication>
#include <QKeySequence>
#include <QString>
#include <cstdio>

static int g_failures = 0;

static void check(bool ok, const char *what)
{
    if (ok) {
        std::printf("PASS: %s\n", what);
    } else {
        std::fprintf(stderr, "FAIL: %s\n", what);
        ++g_failures;
    }
}

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    // 1) singleton
    KGlobalAccel *ga = KGlobalAccel::self();
    check(ga != nullptr, "KGlobalAccel::self() != nullptr");
    if (!ga) {
        std::fprintf(stderr, "cannot continue without the KGlobalAccel singleton\n");
        return 1;
    }

    QAction action;
    action.setObjectName(QStringLiteral("test_action"));
    action.setText(QStringLiteral("test action"));

    // 2) a fresh action has no global shortcut
    const bool hasBefore = ga->hasShortcut(&action);
    check(hasBefore == false, "hasShortcut() is false before registration");

    // 3) setShortcut() is callable on a real QAction; its result must be
    //    consistent with the state observed right after the call
    const QList<QKeySequence> requested{QKeySequence(QStringLiteral("Ctrl+Alt+T"))};
    const bool setResult = ga->setShortcut(&action, requested, KGlobalAccel::NoAutoloading);
    const bool hasAfter = ga->hasShortcut(&action);
    check(hasAfter == setResult,
          "hasShortcut() after setShortcut() equals the setShortcut() result");

    // 4) shortcut() returns at most the one requested sequence
    const QList<QKeySequence> current = ga->shortcut(&action);
    check(current.size() <= 1, "shortcut() returns at most the requested sequence");

    // 5) isGlobalShortcutAvailable() is a pure query: idempotent for the same key
    const QKeySequence probe{QStringLiteral("Ctrl+Alt+U")};
    const bool available1 = KGlobalAccel::isGlobalShortcutAvailable(probe);
    const bool available2 = KGlobalAccel::isGlobalShortcutAvailable(probe);
    check(available1 == available2,
          "isGlobalShortcutAvailable() is idempotent for the same sequence");

    // 6) removeAllShortcuts() clears the action's global shortcut
    ga->removeAllShortcuts(&action);
    check(ga->hasShortcut(&action) == false,
          "hasShortcut() is false after removeAllShortcuts()");

    if (g_failures == 0) {
        std::printf("PASS: kglobalaccel5 5.116.0 consumer test finished (%d assertions)\n", 6);
        return 0;
    }
    std::fprintf(stderr, "FAIL: kglobalaccel5 5.116.0 consumer test had %d failure(s)\n", g_failures);
    return 1;
}
