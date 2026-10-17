// knighttime consumer test — verifies the published package is consumable
// via CMake (find_package(KNightTime) + KNightTime target link) and the
// core public API computes real dark-light schedules:
//  - KDarkLightSchedule::forecast(dateTime, morning, evening, ...) — the
//    fixed-times mode (pure computation, no external data)
//  - KDarkLightSchedule::forecast(dateTime, latitude, longitude) — the
//    sun-driven mode (exercises KHolidays::SunEvents transitively)
//  - previousTransition/nextTransition navigation
//  - toState/fromState serialization round-trip

#include <KDarkLightSchedule>

#include <QDate>
#include <QDateTime>
#include <QTimeZone>
#include <chrono>
#include <iostream>
#include <optional>

int main()
{
    const QTimeZone utc = QTimeZone::utc();

    // 1) Fixed-times forecast: cycleCount=7 covers the next 7 full days
    // plus the in-progress cycle anchored on the reference date (upstream
    // schedule_test.cpp: forecast(..., 3) yields 4 cycles).
    const QDateTime reference(QDate(2025, 6, 18), QTime(12, 0), utc);
    const KDarkLightSchedule fixed = KDarkLightSchedule::forecast(
        reference, QTime(6, 0), QTime(18, 0), std::chrono::minutes(30), 7);

    const auto cycles = fixed.cycles();
    if (cycles.size() != 8) {
        std::cerr << "FAIL: expected 8 cycles (7 + in-progress anchor), got "
                  << cycles.size() << "\n";
        return 1;
    }

    // Each cycle: morning transition starting at 06:00, evening at 18:00,
    // each lasting 30 minutes.
    const auto &first = cycles.first();
    if (!first.morning().startDateTime().isValid()
        || !first.evening().startDateTime().isValid()) {
        std::cerr << "FAIL: invalid transition start times\n";
        return 1;
    }
    if (first.morning().type() != KDarkLightTransition::Morning
        || first.evening().type() != KDarkLightTransition::Evening) {
        std::cerr << "FAIL: wrong transition types\n";
        return 1;
    }
    const qint64 morningDurationMs =
        first.morning().startDateTime().msecsTo(first.morning().endDateTime());
    if (morningDurationMs != 30 * 60 * 1000) {
        std::cerr << "FAIL: morning duration " << morningDurationMs << "ms != 30min\n";
        return 1;
    }

    // Transition relation classification on the morning transition.
    // Note: test() has a 60-second tolerance (upstream implementation), so
    // the probe uses offsets well clear of the boundary.
    const auto &morning = first.morning();
    if (morning.test(morning.startDateTime().addSecs(-120))
        != KDarkLightTransition::Upcoming) {
        std::cerr << "FAIL: before-start not classified Upcoming\n";
        return 1;
    }
    if (morning.test(morning.startDateTime().addSecs(15 * 60))
        != KDarkLightTransition::InProgress) {
        std::cerr << "FAIL: mid-transition not classified InProgress\n";
        return 1;
    }
    if (morning.test(morning.endDateTime().addSecs(120))
        != KDarkLightTransition::Passed) {
        std::cerr << "FAIL: after-end not classified Passed\n";
        return 1;
    }
    // Progress midpoint is 0.5.
    const qreal midProgress = morning.progress(morning.startDateTime().addSecs(15 * 60));
    if (midProgress < 0.49 || midProgress > 0.51) {
        std::cerr << "FAIL: midpoint progress " << midProgress << " != 0.5\n";
        return 1;
    }

    // 2) nextTransition/previousTransition navigation: both must resolve
    // around mid-day and be correctly ordered (previous starts at or
    // before the reference, next starts after it). With morning=6:00 /
    // evening=18:00 the exact type depends on which side of noon the
    // reference lands relative to the cycle's noon anchor (see upstream
    // cycle_test.cpp), so the probe asserts ordering rather than type.
    const QDateTime midDay(QDate(2025, 6, 18), QTime(12, 0), utc);
    const auto next = fixed.nextTransition(midDay);
    if (!next || !next->startDateTime().isValid()) {
        std::cerr << "FAIL: nextTransition did not resolve at noon\n";
        return 1;
    }
    if (!(next->startDateTime() > midDay
          || next->endDateTime() > midDay)) {
        std::cerr << "FAIL: nextTransition is not in the future of the reference\n";
        return 1;
    }
    const auto prev = fixed.previousTransition(midDay);
    if (!prev || !prev->startDateTime().isValid()) {
        std::cerr << "FAIL: previousTransition did not resolve at noon\n";
        return 1;
    }
    if (!(prev->startDateTime() <= midDay)) {
        std::cerr << "FAIL: previousTransition starts after the reference\n";
        return 1;
    }
    // Previous and next must be distinct and ordered.
    if (prev->startDateTime() >= next->startDateTime()) {
        std::cerr << "FAIL: previousTransition not before nextTransition\n";
        return 1;
    }

    // 3) Serialization round-trip: toState -> fromState -> equal schedule.
    const QString state = fixed.toState();
    const auto restored = KDarkLightSchedule::fromState(state);
    if (!restored) {
        std::cerr << "FAIL: fromState returned nullopt for a valid state\n";
        return 1;
    }
    if (restored->cycles().size() != 8) {
        std::cerr << "FAIL: restored schedule has "
                  << restored->cycles().size() << " cycles, expected 8\n";
        return 1;
    }
    const auto &restoredFirst = restored->cycles().first();
    if (restoredFirst.morning().startDateTime() != first.morning().startDateTime()
        || restoredFirst.evening().startDateTime() != first.evening().startDateTime()) {
        std::cerr << "FAIL: restored first cycle differs from the original\n";
        return 1;
    }
    // Garbage state must be rejected.
    if (KDarkLightSchedule::fromState(QString())) {
        std::cerr << "FAIL: empty state accepted\n";
        return 1;
    }

    // 4) Sun-driven forecast for Beijing (39.9N, 116.4E): exercises the
    // KHolidays::SunEvents dependency end to end. At that latitude the sun
    // rises and sets every day, so a schedule must be produced with valid
    // transitions.
    const auto sunDriven = KDarkLightSchedule::forecast(
        QDateTime(QDate(2025, 6, 18), QTime(12, 0), utc), 39.9042, 116.4074, 7);
    if (!sunDriven) {
        std::cerr << "FAIL: sun-driven forecast returned nullopt for Beijing\n";
        return 1;
    }
    const auto sunCycles = sunDriven->cycles();
    if (sunCycles.isEmpty()) {
        std::cerr << "FAIL: sun-driven forecast produced no cycles\n";
        return 1;
    }
    const auto &sunFirst = sunCycles.first();
    if (!sunFirst.morning().startDateTime().isValid()
        || !sunFirst.evening().startDateTime().isValid()) {
        std::cerr << "FAIL: sun-driven transitions invalid\n";
        return 1;
    }
    // Morning must precede evening within a cycle.
    if (!(sunFirst.morning().startDateTime() < sunFirst.evening().startDateTime())) {
        std::cerr << "FAIL: sun-driven morning not before evening\n";
        return 1;
    }

    std::cout << "knighttime consumer probe OK: fixed schedule 8 cycles "
              << "(7 days + anchor), sun-driven Beijing schedule "
              << sunCycles.size()
              << " cycles, round-trip state preserved\n";
    return 0;
}
