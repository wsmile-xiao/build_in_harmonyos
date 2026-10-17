// libkdegames 26.04.0 consumer test (R34: exercises real API).
// Verifies KGameClock (timer API), KGameTheme (theme metadata) and
// KGamePopupItem (popup message API) are callable from the installed
// headers/libs.
#include <KGameClock>
#include <KGameTheme>
#include <KGamePopupItem>
#include <QApplication>
#include <QGraphicsScene>
#include <QString>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);

    // --- KGameClock: time string helpers ---
    KGameClock clock;
    clock.restart();
    const QString total = clock.timeString();
    if (total.isEmpty()) {
        std::fprintf(stderr, "FAIL: KGameClock timeString() empty\n");
        return 1;
    }
    clock.setTime(65u);
    if (clock.seconds() != 65u) {
        std::fprintf(stderr, "FAIL: KGameClock setTime/seconds mismatch\n");
        return 1;
    }
    clock.setTime(QStringLiteral("00:01:05"));
    if (clock.seconds() != 65u) {
        std::fprintf(stderr, "FAIL: KGameClock setTime(QString)/seconds mismatch\n");
        return 1;
    }
    clock.pause();
    clock.resume();
    clock.restart();
    clock.showTime();

    // --- KGameTheme: metadata accessors ---
    KGameTheme theme(QByteArray("test-theme"));
    if (theme.identifier() != QByteArray("test-theme")) {
        std::fprintf(stderr, "FAIL: KGameTheme identifier mismatch\n");
        return 1;
    }
    theme.setName(QStringLiteral("Test Theme"));
    if (theme.name() != QStringLiteral("Test Theme")) {
        std::fprintf(stderr, "FAIL: KGameTheme name roundtrip failed\n");
        return 1;
    }
    theme.setLicense(QStringLiteral("CC-BY-SA-4.0"));
    theme.setAuthor(QStringLiteral("Tester"));
    if (theme.license() != QStringLiteral("CC-BY-SA-4.0")
        || theme.author() != QStringLiteral("Tester")) {
        std::fprintf(stderr, "FAIL: KGameTheme metadata roundtrip failed\n");
        return 1;
    }
    // A nonexistent desktop file must be rejected, leaving fields untouched.
    if (theme.readFromDesktopFile(QStringLiteral("/nonexistent/theme.desktop"))) {
        std::fprintf(stderr, "FAIL: KGameTheme accepted a nonexistent file\n");
        return 1;
    }

    // --- KGamePopupItem: scene-integrated popup ---
    {
        // QGraphicsScene + item registration without paint/show cycles
        // (showMessage() starts animations that need a running event loop).
        QGraphicsScene scene;
        KGamePopupItem messageItem;
        scene.addItem(&messageItem);
        messageItem.setMessageTimeout(100);
        messageItem.setMessageOpacity(0.9);
        if (!messageItem.hidesOnMouseClick()) {
            std::fprintf(stderr, "FAIL: KGamePopupItem default hide-on-click wrong\n");
            return 1;
        }
        messageItem.setHideOnMouseClick(false);
        if (messageItem.hidesOnMouseClick()) {
            std::fprintf(stderr, "FAIL: KGamePopupItem setHideOnMouseClick failed\n");
            return 1;
        }
        messageItem.forceHide(KGamePopupItem::InstantHide);
    }

    std::printf(
        "PASS: KGameClock/KGameTheme/KGamePopupItem API OK (time=%s, theme=%s)\n",
        total.toUtf8().constData(),
        theme.name().toUtf8().constData()
    );
    return 0;
}
