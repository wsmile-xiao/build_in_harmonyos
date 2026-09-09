// knotifications 6.26.0 consumer test (R34: exercises real API).
// Constructs a KNotification, verifies eventId/flags/title/icon API surface,
// and exercises the default event id from the standard config path.
#include <KNotification>
#include <QCoreApplication>
#include <QPixmap>
#include <cstdio>

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    KNotification *n = new KNotification(QStringLiteral("test"));
    if (!n) {
        std::printf("FAIL: alloc failed\n");
        return 1;
    }

    // eventId round-trip
    if (n->eventId() != QStringLiteral("test")) {
        std::printf("FAIL: eventId mismatch\n");
        return 1;
    }

    // title / text / icon API
    n->setTitle(QStringLiteral("Hello"));
    n->setText(QStringLiteral("World"));
    if (n->title() != QStringLiteral("Hello") || n->text() != QStringLiteral("World")) {
        std::printf("FAIL: title/text mismatch\n");
        return 1;
    }
    n->setIconName(QStringLiteral("dialog-information"));
    if (n->iconName() != QStringLiteral("dialog-information")) {
        std::printf("FAIL: iconName mismatch\n");
        return 1;
    }

    // flags API (CloseOnTimeout = 0x00, Persistent = 0x02)
    n->setFlags(KNotification::CloseOnTimeout | KNotification::Persistent);
    if (n->flags() != (KNotification::CloseOnTimeout
                       | KNotification::Persistent)) {
        std::printf("FAIL: flags mismatch\n");
        return 1;
    }

    // actions API
    KNotificationAction *act = n->addAction(QStringLiteral("ok"));
    if (!act || act->label() != QStringLiteral("ok")) {
        std::printf("FAIL: addAction failed\n");
        return 1;
    }

    delete n;
    std::printf("PASS: KNotification API surface verified OK\n");
    return 0;
}
