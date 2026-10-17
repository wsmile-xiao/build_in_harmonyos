// Consumer test for dewalls 1.0.0 — links libdewalls and exercises the public
// WallsSurveyParser API (real parsing, not a print-only stub).
#include <QString>
#include <cstdio>

#include "wallssurveyparser.h"
#include "vector.h"

using namespace dewalls;

int main()
{
    WallsSurveyParser parser;

    // Default units: meters/degrees (Walls .srv conventions).
    if (parser.units().dUnit() != Length::Meters)
        return 1;
    if (parser.units().aUnit() != Angle::Degrees)
        return 2;

    // Parse a survey data line; a valid vector line must emit parsedVector.
    Vector parsed;
    bool sawVector = false;
    QObject::connect(&parser, &WallsSurveyParser::parsedVector,
                     [&](Vector v) { parsed = v; sawVector = true; });

    parser.parseLine("1 2 3 45 0 0");  // from-to depth dist azimuth incl flags
    if (!sawVector)
        return 3;
    if (!parsed.distance().isPositive())
        return 4;

    std::printf("dewalls 1.0.0: WallsSurveyParser parsed a survey vector OK\n");
    return 0;
}