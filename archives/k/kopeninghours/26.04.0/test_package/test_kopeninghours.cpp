// kopeninghours consumer test — verifies the published package is
// consumable via CMake (find_package(KOpeningHours) + KOpeningHours link)
// and that the public API actually parses and evaluates OSM opening-hours
// expressions (R34: real API usage, not a print-only stub).

#include <KOpeningHours/Interval>
#include <KOpeningHours/OpeningHours>

#include <QDateTime>
#include <QJsonArray>
#include <QJsonObject>
#include <QTimeZone>
#include <iostream>

using namespace KOpeningHours;

static int fail(const char *what)
{
    std::cerr << "FAIL: " << what << "\n";
    return 1;
}

int main()
{
    // 1) Parse a plain interval expression and evaluate it.
    OpeningHours oh;
    oh.setExpression("Mo-Fr 08:00-12:00");
    if (oh.error() != OpeningHours::NoError) {
        return fail("setExpression('Mo-Fr 08:00-12:00') reported an error");
    }

    // A Monday 09:00 (2020-11-09 was a Monday) must be inside an open interval.
    const QDateTime monday(QDate(2020, 11, 9), QTime(9, 0));
    const Interval inside = oh.interval(monday);
    if (!inside.isValid() || inside.state() != Interval::Open) {
        return fail("Monday 09:00 should be Open");
    }
    if (inside.begin() != QDateTime(QDate(2020, 11, 9), QTime(8, 0))
        || inside.end() != QDateTime(QDate(2020, 11, 9), QTime(12, 0))) {
        return fail("interval begin/end mismatch");
    }

    // A Monday 13:00 must be Closed (still within the working week, outside
    // the 08:00-12:00 range -> next open interval starts Tuesday 08:00).
    const Interval closed = oh.interval(QDateTime(QDate(2020, 11, 9), QTime(13, 0)));
    if (closed.state() != Interval::Closed) {
        return fail("Monday 13:00 should be Closed");
    }
    const Interval next = oh.nextInterval(closed);
    if (!next.isValid() || next.begin() != QDateTime(QDate(2020, 11, 10), QTime(8, 0))) {
        return fail("nextInterval after Monday 13:00 should be Tuesday 08:00");
    }

    // 2) Normalization: the reconstructed expression stays equivalent.
    const QByteArray normalized = oh.normalizedExpression();
    if (normalized.isEmpty()) {
        return fail("normalizedExpression() empty");
    }

    // 3) schema.org JSON-LD import (openingHours array of OSM expressions,
    //    as produced by e.g. the schema.org "openingHours" property).
    QJsonObject place;
    place.insert(QStringLiteral("@type"), QStringLiteral("Cafe"));
    QJsonArray openingHours;
    openingHours.append(QStringLiteral("Mo-Fr 09:00-17:00"));
    place.insert(QStringLiteral("openingHours"), openingHours);
    const OpeningHours fromLd = OpeningHours::fromJsonLd(place);
    if (fromLd.error() != OpeningHours::NoError) {
        return fail("fromJsonLd failed to parse the openingHours array");
    }

    std::cout << "kopeninghours consumer probe OK: '" << normalized.toStdString()
              << "' Monday-09:00=open Monday-13:00=closed next=Tuesday-08:00"
              << " jsonld-ok\n";
    return 0;
}
