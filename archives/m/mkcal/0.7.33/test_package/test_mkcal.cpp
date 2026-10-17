/*
  Consumer-side smoke test for the installed mkcal package.

  Exercises the real public API surface: mKCal::ExtendedCalendar +
  mKCal::ExtendedStorage (SQLite backend), notebook creation, event insertion,
  save/close/reopen and a load round-trip.
*/
#include <QCoreApplication>
#include <QDate>
#include <QDateTime>
#include <QDebug>
#include <QString>
#include <QTemporaryDir>
#include <QTime>
#include <QTimeZone>

#include <KCalendarCore/Event>

#include <extendedcalendar.h>
#include <extendedstorage.h>
#include <notebook.h>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    QTemporaryDir tempDir;
    if (!tempDir.isValid()) {
        qCritical() << "temporary directory could not be created";
        return 1;
    }
    // /tmp is read-only on OHOS; the storage backend reads MKCAL_STORAGEDB.
    qputenv("MKCAL_STORAGEDB",
            tempDir.filePath(QStringLiteral("mkcal-test.db")).toUtf8());

    mKCal::ExtendedCalendar::Ptr calendar(
        new mKCal::ExtendedCalendar(QTimeZone::systemTimeZone()));
    mKCal::ExtendedStorage::Ptr storage = calendar->defaultStorage(calendar);
    if (!storage->open()) {
        qCritical() << "storage open failed";
        return 1;
    }

    const QString notebookId = QStringLiteral("ohpc-smoke-notebook");
    mKCal::Notebook::Ptr notebook(new mKCal::Notebook(
        notebookId,
        QStringLiteral("ohpc smoke notebook"),
        QString(),
        QStringLiteral("#001122"),
        false,  // not shared
        true,   // master
        false,  // not synced
        true,   // writable
        true,   // visible
        QString(),
        QString(),
        0));
    if (!storage->addNotebook(notebook) || !storage->setDefaultNotebook(notebook)) {
        qCritical() << "notebook setup failed";
        return 1;
    }

    KCalendarCore::Event::Ptr event(new KCalendarCore::Event);
    event->setSummary(QStringLiteral("ohpc-smoke"));
    event->setDtStart(QDateTime(QDate(2026, 9, 29), QTime(10, 0), QTimeZone::utc()));
    calendar->addEvent(event, notebookId);
    if (!storage->save()) {
        qCritical() << "storage save failed";
        return 1;
    }
    storage->close();

    // Reopen the database and verify the event survived the round-trip.
    mKCal::ExtendedCalendar::Ptr reopenedCalendar(
        new mKCal::ExtendedCalendar(QTimeZone::systemTimeZone()));
    mKCal::ExtendedStorage::Ptr reopenedStorage =
        reopenedCalendar->defaultStorage(reopenedCalendar);
    if (!reopenedStorage->open() || !reopenedStorage->load()) {
        qCritical() << "storage reopen/load failed";
        return 1;
    }
    KCalendarCore::Event::Ptr fetched = reopenedCalendar->event(event->uid());
    if (!fetched) {
        qCritical() << "event was not persisted";
        return 1;
    }
    if (fetched->summary() != QStringLiteral("ohpc-smoke")) {
        qCritical() << "event summary mismatch:" << fetched->summary();
        return 1;
    }
    if (fetched->dtStart() != event->dtStart()) {
        qCritical() << "event dtStart mismatch";
        return 1;
    }

    qDebug().noquote() << "PASS: mkcal SQLite storage round-trip" << fetched->uid();
    return 0;
}
