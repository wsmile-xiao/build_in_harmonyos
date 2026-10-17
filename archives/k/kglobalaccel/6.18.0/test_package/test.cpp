// kglobalaccel 6.18.0 consumer test (R34: exercises real API).
// Calls the KGlobalAccel singleton and static query APIs; these work
// headless without a running DBus daemon (calls fail gracefully).
#include <KGlobalAccel>
#include <QAction>
#include <QApplication>
#include <QKeySequence>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);

    KGlobalAccel *accel = KGlobalAccel::self();
    if (!accel) {
        std::printf("FAIL: KGlobalAccel::self() returned null\n");
        return 1;
    }
    std::printf("PASS: KGlobalAccel::self() OK\n");

    QAction action;
    action.setObjectName(QStringLiteral("test-action"));
    action.setText(QStringLiteral("test-action"));
    const QList<QKeySequence> seqs{QKeySequence(Qt::CTRL | Qt::ALT | Qt::Key_F12)};
    // Without a DBus session daemon this returns false; the call itself must
    // not crash and the library must be linked/usable.
    KGlobalAccel::self()->setShortcut(&action, seqs, KGlobalAccel::NoAutoloading);
    KGlobalAccel::isGlobalShortcutAvailable(QKeySequence(Qt::CTRL | Qt::ALT | Qt::Key_F12));
    KGlobalAccel::globalShortcutsByKey(QKeySequence(Qt::CTRL | Qt::ALT | Qt::Key_F12));

    std::printf("PASS: kglobalaccel API exercised without crash\n");
    return 0;
}
