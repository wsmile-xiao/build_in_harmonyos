#include <KCalendarCore/Event>
#include <KCalendarCore/ICalFormat>
#include <KCalendarCore/MemoryCalendar>

#include <QCoreApplication>
#include <QDate>
#include <QDateTime>
#include <QString>
#include <QTime>
#include <QTimeZone>

#include <iostream>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    auto calendar = KCalendarCore::MemoryCalendar::Ptr::create(QTimeZone::utc());
    KCalendarCore::Event::Ptr event(new KCalendarCore::Event);
    event->setUid(QStringLiteral("akonadi-calendarcore-smoke"));
    event->setSummary(QStringLiteral("Akonadi calendar event"));
    event->setDtStart(
        QDateTime(QDate(2026, 8, 27), QTime(10, 0), QTimeZone::utc()));
    event->setDtEnd(
        QDateTime(QDate(2026, 8, 27), QTime(11, 0), QTimeZone::utc()));

    if (!calendar->addEvent(event)) {
        std::cerr << "FAIL: could not add event" << std::endl;
        return 1;
    }

    KCalendarCore::ICalFormat format;
    const QString payload = format.toString(calendar);
    if (!payload.contains(QStringLiteral("SUMMARY:Akonadi calendar event"))) {
        std::cerr << "FAIL: serialized calendar is missing summary" << std::endl;
        return 1;
    }

    auto parsed = KCalendarCore::MemoryCalendar::Ptr::create(QTimeZone::utc());
    if (!format.fromString(parsed, payload) || parsed->events().isEmpty()) {
        std::cerr << "FAIL: could not parse serialized calendar" << std::endl;
        return 1;
    }

    const auto parsedEvent = parsed->events().constFirst();
    if (parsedEvent->uid() != QStringLiteral("akonadi-calendarcore-smoke")) {
        std::cerr << "FAIL: parsed event UID mismatch" << std::endl;
        return 1;
    }

    std::cout << "PASS: KCalendarCore serialized Akonadi calendar event"
              << std::endl;
    std::cout << "PASS: KCalendarCore parsed event "
              << parsedEvent->summary().toStdString() << std::endl;
    return 0;
}
