#include <KCalendarCore/MemoryCalendar>
#include <KCalendarCore/Event>
#include <KCalendarCore/ICalFormat>
#include <KCalendarCore/Todo>

#include <QDebug>
#include <QTimeZone>
#include <iostream>

int main(int argc, char **argv)
{
    Q_UNUSED(argc);
    Q_UNUSED(argv);

    // 1) Construct a memory calendar in a named timezone and create an event.
    KCalendarCore::MemoryCalendar::Ptr calendar(
        new KCalendarCore::MemoryCalendar(QTimeZone::UTC));
    if (calendar->timeZone() != QTimeZone::UTC) {
        std::cerr << "FAIL: calendar timeZone is not UTC" << std::endl;
        return 1;
    }

    KCalendarCore::Event::Ptr event(new KCalendarCore::Event);
    event->setSummary(QStringLiteral("HarmonyOS PC kcalendarcore smoke test"));
    event->setDtStart(QDateTime(QDate(2026, 9, 6), QTime(9, 0, 0), QTimeZone::UTC));
    event->setDtEnd(QDateTime(QDate(2026, 9, 6), QTime(10, 0, 0), QTimeZone::UTC));
    if (!calendar->addEvent(event)) {
        std::cerr << "FAIL: addEvent returned false" << std::endl;
        return 1;
    }

    const KCalendarCore::Event::List events = calendar->rawEvents();
    if (events.count() != 1 || events.first() != event) {
        std::cerr << "FAIL: unexpected rawEvents count" << std::endl;
        return 1;
    }

    // 2) Round-trip the calendar through the ICal serializer (exercises the
    // libical-backed ICalFormat parser in the packaged library).
    KCalendarCore::ICalFormat format;
    const QString ics = format.toString(calendar);
    if (!ics.contains(QStringLiteral("BEGIN:VCALENDAR"))
        || !ics.contains(QStringLiteral("HarmonyOS PC kcalendarcore smoke test"))) {
        std::cerr << "FAIL: serialized calendar misses expected content" << std::endl;
        return 1;
    }

    KCalendarCore::MemoryCalendar::Ptr parsed(
        new KCalendarCore::MemoryCalendar(QTimeZone::UTC));
    if (!format.fromString(parsed, ics)) {
        std::cerr << "FAIL: fromString could not parse the serialized calendar" << std::endl;
        return 1;
    }
    if (parsed->rawEvents().count() != 1) {
        std::cerr << "FAIL: parsed calendar event count != 1" << std::endl;
        return 1;
    }

    // 3) Todo API sanity (duration handling).
    KCalendarCore::Todo::Ptr todo(new KCalendarCore::Todo);
    todo->setSummary(QStringLiteral("verify KCalendarCore::Todo"));
    todo->setDtStart(QDateTime(QDate(2026, 9, 6), QTime(9, 0, 0), QTimeZone::UTC));
    todo->setDuration(KCalendarCore::Duration(3600, KCalendarCore::Duration::Seconds));
    if (todo->duration().asSeconds() != 3600) {
        std::cerr << "FAIL: todo duration round-trip mismatch" << std::endl;
        return 1;
    }

    std::cout << "PASS: KCalendarCore MemoryCalendar/ICalFormat round-trip OK ("
              << qPrintable(parsed->rawEvents().first()->summary()) << ")" << std::endl;
    return 0;
}
