// kstatusnotifieritem 6.26.0 consumer test (R34: exercises real API).
// Constructs KStatusNotifierItem, sets the title/icon/category/status/
// tooltip properties through the public API and reads them back. The
// constructor registers the item on the session bus when DBus is available;
// without a session bus it degrades gracefully (kdbusaddons precedent).
#include <KStatusNotifierItem>
#include <QApplication>
#include <QString>
#include <cstdio>

int main(int argc, char **argv) {
    QApplication app(argc, argv);

    KStatusNotifierItem tray(QStringLiteral("kstatusnotifieritem-smoke"));

    tray.setTitle(QStringLiteral("OHOS SNI smoke"));
    tray.setIconByName(QStringLiteral("konqueror"));
    tray.setCategory(KStatusNotifierItem::Communications);
    tray.setStatus(KStatusNotifierItem::Active);
    tray.setToolTip(QStringLiteral("konqueror"),
                    QStringLiteral("tool title"),
                    QStringLiteral("tool subtitle"));

    if (tray.title() != QStringLiteral("OHOS SNI smoke")) {
        std::printf("FAIL: title round-trip mismatch\n");
        return 1;
    }
    if (tray.category() != KStatusNotifierItem::Communications) {
        std::printf("FAIL: category round-trip mismatch\n");
        return 1;
    }
    if (tray.status() != KStatusNotifierItem::Active) {
        std::printf("FAIL: status round-trip mismatch\n");
        return 1;
    }
    if (tray.toolTipTitle() != QStringLiteral("tool title")) {
        std::printf("FAIL: toolTipTitle round-trip mismatch\n");
        return 1;
    }

    std::printf("PASS: KStatusNotifierItem API round-trip OK "
                "(title/category/status/toolTip)\n");
    return 0;
}
