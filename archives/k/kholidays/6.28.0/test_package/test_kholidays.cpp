// kholidays consumer test — verifies the published package is consumable
// via CMake (find_package(KF6Holidays)) and the public astronomy API is
// callable: SunEvents (all solar event times around the closest solar
// noon) plus the polar day/night predicates.

#include <KHolidays/SunEvents>
#include <KHolidays/SunRiseSet>

#include <QDate>
#include <QDateTime>
#include <QTimeZone>
#include <iostream>

int main()
{
    // 1) SunEvents for Beijing (39.9N, 116.4E) around the 2025 June
    // solstice: sunrise/sunset/solar noon must all be valid, correctly
    // ordered, and astronomically plausible.
    const QDate date(2025, 6, 21);
    const double latitude = 39.9042;
    const double longitude = 116.4074;
    const QTimeZone utc = QTimeZone::utc();
    const QDateTime reference(QDateTime(date, QTime(4, 0), utc));

    const KHolidays::SunEvents sunEvents(reference, latitude, longitude);

    if (!sunEvents.solarNoon().isValid()) {
        std::cerr << "FAIL: solarNoon invalid\n";
        return 1;
    }
    if (!sunEvents.sunrise().isValid() || !sunEvents.sunset().isValid()) {
        std::cerr << "FAIL: SunEvents sunrise/sunset invalid\n";
        return 1;
    }
    if (!(sunEvents.sunrise() < sunEvents.solarNoon()
          && sunEvents.solarNoon() < sunEvents.sunset())) {
        std::cerr << "FAIL: SunEvents ordering sunrise < noon < sunset broken\n";
        return 1;
    }
    // civil dawn is earlier than sunrise; civil dusk later than sunset
    if (!(sunEvents.civilDawn() < sunEvents.sunrise())) {
        std::cerr << "FAIL: civilDawn not before sunrise\n";
        return 1;
    }
    if (!(sunEvents.sunset() < sunEvents.civilDusk())) {
        std::cerr << "FAIL: civilDusk not after sunset\n";
        return 1;
    }
    // Day length at the June solstice in Beijing is ~14h50m: assert a
    // plausible astronomical range [13h, 16h].
    const qint64 daySeconds = sunEvents.sunrise().secsTo(sunEvents.sunset());
    if (daySeconds < 13 * 3600 || daySeconds > 16 * 3600) {
        std::cerr << "FAIL: implausible day length: " << daySeconds << "s\n";
        return 1;
    }
    // solar noon near 116.4E is around 04:15 UTC on that date
    const qint64 noonOffset
        = sunEvents.solarNoon().toUTC().time().msecsSinceStartOfDay() / 1000;
    if (noonOffset < 3 * 3600 || noonOffset > 5 * 3600) {
        std::cerr << "FAIL: implausible solar noon UTC time: " << noonOffset << "s\n";
        return 1;
    }

    // 2) Polar predicates (SunRiseSet, public API since 5.97):
    // deep winter near the north pole is polar night, mid summer is polar
    // day, and Beijing never sees either.
    if (!KHolidays::SunRiseSet::isPolarNight(QDate(2025, 12, 21), 89.0)) {
        std::cerr << "FAIL: isPolarNight false for 89N in December\n";
        return 1;
    }
    if (!KHolidays::SunRiseSet::isPolarDay(QDate(2025, 6, 21), 89.0)) {
        std::cerr << "FAIL: isPolarDay false for 89N in June\n";
        return 1;
    }
    if (KHolidays::SunRiseSet::isPolarDay(date, latitude)
        || KHolidays::SunRiseSet::isPolarNight(date, latitude)) {
        std::cerr << "FAIL: Beijing flagged polar day/night\n";
        return 1;
    }

    // 3) Polar sanity: deep winter near the north pole — the polar night
    // must not produce a normal short day.
    const QDate polarDate(2025, 12, 21);
    const QDateTime polarRef(QDateTime(polarDate, QTime(12, 0), utc));
    const KHolidays::SunEvents polarNight(polarRef, 89.0, 0.0);
    if (polarNight.sunrise().isValid() && polarNight.sunset().isValid()) {
        const qint64 polarDaySeconds
            = polarNight.sunrise().secsTo(polarNight.sunset());
        if (polarDaySeconds > 0 && polarDaySeconds < 12 * 3600) {
            std::cerr << "FAIL: implausible polar-day result near north pole\n";
            return 1;
        }
    }

    std::cout << "kholidays consumer probe OK: Beijing solstice sunrise "
              << sunEvents.sunrise().toString(Qt::ISODate).toStdString()
              << " sunset " << sunEvents.sunset().toString(Qt::ISODate).toStdString()
              << " (day " << (daySeconds / 3600.0) << "h)\n";
    return 0;
}
