#include <Libkdepim/ProgressManager>

#include <QCoreApplication>
#include <QDebug>
#include <QEvent>

namespace
{
int fail(const char *message)
{
    qCritical().noquote() << message;
    return 1;
}
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    KPIM::ProgressManager *manager = KPIM::ProgressManager::instance();
    if (!manager || !manager->isEmpty()) {
        return fail("progress manager did not start empty");
    }

    const QString id = KPIM::ProgressManager::getUniqueID();
    if (id.isEmpty()) {
        return fail("progress manager did not create a unique id");
    }

    KPIM::ProgressItem *item = KPIM::ProgressManager::createProgressItem(id, QStringLiteral("libkdepim smoke"));
    if (!item || item->id() != id || item->label() != QStringLiteral("libkdepim smoke")) {
        return fail("progress item was not created with the expected data");
    }

    item->setTotalItems(4);
    item->setCompletedItems(2);
    item->updateProgress();
    if (item->progress() != 50) {
        return fail("progress item did not calculate 50 percent progress");
    }

    item->setStatus(QStringLiteral("half done"));
    if (item->status() != QStringLiteral("half done")) {
        return fail("progress item status was not stored");
    }

    item->setComplete();
    QCoreApplication::sendPostedEvents(nullptr, QEvent::DeferredDelete);

    qInfo().noquote() << "PASS: libkdepim progress manager created and updated an item";
    return 0;
}
