/*
    Consumer-side test for kdeclarative 6.26.0 on HarmonyOS PC.

    Exercises the KF6CalendarEvents C++ library shipped by kdeclarative:
    CalendarEventsPlugin (the plugin interface consumers implement) and the
    CalendarEvents::EventData value type (both declared in
    CalendarEvents/CalendarEventsPlugin).
*/

#include <CalendarEvents/CalendarEventsPlugin>
#include <kdeclarative_version.h>

#include <QCoreApplication>
#include <QDate>
#include <QDateTime>
#include <QString>

#include <cstdio>

namespace
{
int fail(const char *message)
{
    std::fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}
}

class TestPlugin : public CalendarEvents::CalendarEventsPlugin
{
    Q_OBJECT
public:
    using CalendarEvents::CalendarEventsPlugin::CalendarEventsPlugin;
    void loadEventsForDateRange(const QDate &startDate, const QDate &endDate) override
    {
        m_start = startDate;
        m_end = endDate;
    }
    QDate m_start;
    QDate m_end;
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);

    // 1. The ecm_setup_version() header pins the packaged upstream release.
    if (QString(KDECLARATIVE_VERSION_STRING) != QStringLiteral("6.26.0")) {
        return fail("kdeclarative_version.h reports an unexpected version");
    }
    if (KDECLARATIVE_VERSION_MAJOR != 6
            || KDECLARATIVE_VERSION_MINOR != 26
            || KDECLARATIVE_VERSION_PATCH != 0) {
        return fail("kdeclarative_version.h reports unexpected version parts");
    }

    // 2. CalendarEventsPlugin: the abstract interface consumers implement;
    //    subclassing it (implementing the loadEventsForDateRange pure
    //    virtual) must work: vtable + Q_OBJECT moc linkage against the
    //    installed library.
    TestPlugin plugin;
    plugin.loadEventsForDateRange(QDate(2026, 9, 10), QDate(2026, 9, 11));
    if (plugin.m_start != QDate(2026, 9, 10) || plugin.m_end != QDate(2026, 9, 11)) {
        return fail("loadEventsForDateRange did not retain the window");
    }

    // 3. EventData: the value type carried by calendar event data sources.
    CalendarEvents::EventData event;
    event.setUid(QStringLiteral("test-uid-1"));
    event.setTitle(QStringLiteral("HarmonyOS PC test event"));
    event.setDescription(QStringLiteral("consumer-side kdeclarative test"));
    event.setStartDateTime(QDateTime(QDate(2026, 9, 10), QTime(9, 0)));
    event.setEndDateTime(QDateTime(QDate(2026, 9, 10), QTime(10, 0)));
    event.setIsAllDay(false);
    event.setIsMinor(true);
    event.setEventType(CalendarEvents::EventData::Event);
    event.setEventColor(QStringLiteral("#3daee9"));

    if (event.uid() != QStringLiteral("test-uid-1")
            || event.title() != QStringLiteral("HarmonyOS PC test event")
            || event.description() != QStringLiteral("consumer-side kdeclarative test")
            || event.startDateTime() != QDateTime(QDate(2026, 9, 10), QTime(9, 0))
            || event.endDateTime() != QDateTime(QDate(2026, 9, 10), QTime(10, 0))
            || event.isAllDay()
            || !event.isMinor()
            || event.type() != CalendarEvents::EventData::Event
            || event.eventColor() != QStringLiteral("#3daee9")) {
        return fail("EventData accessors did not retain the stored fields");
    }

    // 4. Copy semantics: EventData is a QSharedData value type; the copy
    //    must stay independent after mutation of the original.
    CalendarEvents::EventData copy(event);
    copy.setTitle(QStringLiteral("changed"));
    if (event.title() != QStringLiteral("HarmonyOS PC test event")
            || copy.title() != QStringLiteral("changed")) {
        return fail("EventData copy-on-write semantics broken");
    }

    std::printf("PASS kdeclarative %s CalendarEvents uid=%s title=%s\n",
                KDECLARATIVE_VERSION_STRING,
                event.uid().toUtf8().constData(),
                event.title().toUtf8().constData());
    return 0;
}

#include "test_kdeclarative.moc"
