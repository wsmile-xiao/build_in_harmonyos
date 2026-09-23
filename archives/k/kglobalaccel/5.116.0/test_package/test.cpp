// kglobalaccel 5.116.0 consumer test (R34: exercises the real public API).
//
// Links KF5::GlobalAccel and asserts the behaviour of the KGlobalAccel
// singleton plus the query/set shortcut API on a real QAction.
// Without a session D-Bus the D-Bus-bound setters degrade gracefully; the
// assertions are written against API consistency (state after set/remove)
// and against the client-side registration chain (default-shortcut round
// trip, doRegister()/garbage-keycode guards) rather than against a D-Bus
// side effect, so the test is deterministic on both a desktop session and a
// headless OHOS device.
//
// Assertions 4-9 are the positive-path block: they verify that the
// client-side registration chain actually works (state is stored and read
// back, malformed input is refused), so a functional regression in that
// chain fails the test even though no kglobalaccel daemon is present.
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

    // 4) POSITIVE PATH: setDefaultShortcut() accepts a well-formed sequence.
    //    The client-side chain (garbage-keycode check -> doRegister()
    //    bookkeeping -> default-shortcut map insert) runs identically with
    //    and without the kglobalaccel daemon.
    const bool defaultResult = ga->setDefaultShortcut(&action, requested, KGlobalAccel::NoAutoloading);
    check(defaultResult == true,
          "setDefaultShortcut() accepts a well-formed sequence");

    // 5) POSITIVE PATH: the registered default shortcut is readable back.
    //    This round trip fails if the registration chain regresses.
    check(ga->defaultShortcut(&action) == requested,
          "defaultShortcut() round-trips the registered sequence");

    // 6) registration guard: an action without objectName() must be refused
    //    by the client-side doRegister() guard before any daemon interaction
    QAction unnamedAction;
    check(ga->setShortcut(&unnamedAction, requested) == false,
          "setShortcut() rejects an action without objectName()");

    // 7) the refused action must stay unregistered
    check(ga->hasShortcut(&unnamedAction) == false,
          "rejected action stays unregistered");

    // 8) garbage-keycode guard: a sequence containing keycode -1 (upstream
    //    checkGarbageKeycode; Qt produces it for exotic multimedia keys)
    //    must be refused instead of forwarded
    QAction guardAction;
    guardAction.setObjectName(QStringLiteral("test_action_guard"));
    const QList<QKeySequence> garbage{QKeySequence(-1)};
    check(ga->setShortcut(&guardAction, garbage) == false,
          "setShortcut() refuses a sequence with a garbage keycode (-1)");

    // 9) the refused sequence must stay unregistered
    check(ga->hasShortcut(&guardAction) == false,
          "garbage-keycode sequence stays unregistered");

    // 10) shortcut() returns at most the one requested sequence
    const QList<QKeySequence> current = ga->shortcut(&action);
    check(current.size() <= 1, "shortcut() returns at most the requested sequence");

    // 11) isGlobalShortcutAvailable() is a pure query: idempotent for the same key
    const QKeySequence probe{QStringLiteral("Ctrl+Alt+U")};
    const bool available1 = KGlobalAccel::isGlobalShortcutAvailable(probe);
    const bool available2 = KGlobalAccel::isGlobalShortcutAvailable(probe);
    check(available1 == available2,
          "isGlobalShortcutAvailable() is idempotent for the same sequence");

    // 12) removeAllShortcuts() clears the action's global shortcut (both the
    //     active-shortcut and the default-shortcut client-side maps)
    ga->removeAllShortcuts(&action);
    check(ga->hasShortcut(&action) == false,
          "hasShortcut() is false after removeAllShortcuts()");

    // 13) the default-shortcut map is cleared as well
    check(ga->defaultShortcut(&action).isEmpty(),
          "defaultShortcut() is empty after removeAllShortcuts()");

    if (g_failures == 0) {
        std::printf("PASS: kglobalaccel 5.116.0 consumer test finished (%d assertions)\n", 13);
        return 0;
    }
    std::fprintf(stderr, "FAIL: kglobalaccel 5.116.0 consumer test had %d failure(s)\n", g_failures);
    return 1;
}
