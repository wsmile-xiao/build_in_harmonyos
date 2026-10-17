#include <Akonadi/Collection>
#include <Akonadi/Item>
#include <Akonadi/Tag>

#include <QCoreApplication>
#include <QByteArray>
#include <QDBusConnection>
#include <QSqlDatabase>
#include <QString>

#include <cstdio>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    Akonadi::Collection collection(42);
    collection.setName(QStringLiteral("akonadi-test-collection"));
    collection.setRemoteId(QStringLiteral("remote-collection"));
    collection.setContentMimeTypes({QStringLiteral("text/plain")});
    if (!collection.isValid() || collection.name() != QStringLiteral("akonadi-test-collection")) {
        std::printf("FAIL: Akonadi::Collection API check failed\n");
        return 1;
    }

    Akonadi::Item item(QStringLiteral("text/plain"));
    item.setId(100);
    item.setRemoteId(QStringLiteral("remote-item"));
    item.setParentCollection(collection);
    if (!item.isValid() || item.mimeType() != QStringLiteral("text/plain")
        || item.parentCollection().id() != collection.id()) {
        std::printf("FAIL: Akonadi::Item API check failed\n");
        return 2;
    }

    Akonadi::Tag tag(7);
    tag.setName(QStringLiteral("akonadi-test-tag"));
    tag.setRemoteId(QByteArray("remote-tag"));
    if (!tag.isValid() || tag.name() != QStringLiteral("akonadi-test-tag")
        || tag.remoteId() != QByteArray("remote-tag")) {
        std::printf("FAIL: Akonadi::Tag API check failed\n");
        return 3;
    }

    if (!QSqlDatabase::isDriverAvailable(QStringLiteral("QSQLITE"))) {
        std::printf("FAIL: QSQLITE driver is unavailable\n");
        return 4;
    }

    const QDBusConnection connection = QDBusConnection::sessionBus();
    if (!connection.isConnected()) {
        std::printf("INFO: session bus is not connected in this test environment\n");
    }

    std::printf("PASS: Akonadi Core API, QSQLITE and QtDBus are available\n");
    return 0;
}
