// test_package consumer test — libsgp4 1.0 (HarmonyOS PC, aarch64).
//
// Reference constants below come from an independent SGP4 implementation
// (python-sgp4 2.27 — the Vallado reference code, WGS72) evaluated at the
// same tsince for the same TLE; the device build of this package agrees with
// it to < 1e-8 km at tsince 0/360/4320 (evidence: reports/upstream-runtest.md).
//
// 10 assertions in 4 groups: TLE parsing (4), propagation vs reference (4),
// error signalling (1), look-angle API (1).
#include <Tle.h>
#include <SGP4.h>
#include <Eci.h>
#include <Vector.h>
#include <Observer.h>
#include <CoordTopocentric.h>
#include <DateTime.h>
#include <SatelliteException.h>
#include <DecayedException.h>

#include <cmath>
#include <cstdio>
#include <string>

static int failures = 0;

#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);  \
            ++failures;                                                  \
        }                                                                \
    } while (0)

static bool near(double a, double b, double tol)
{
    return std::fabs(a - b) <= tol;
}

int main()
{
    // First SGP4-VER.TLE verification case (norad 5).
    const std::string l1 =
        "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753";
    const std::string l2 =
        "2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667     0.00      4320.0        360.00";
    // Like upstream runtest.cc: TLE line 2 carries run parameters after the
    // standard 69 columns, the Tle parser only accepts the 69-column form.
    Tle tle("SGP4-VER case 0", l1, l2.substr(0, Tle::LineLength()));

    // ── 1-4: TLE parsing ────────────────────────────────────────────────
    CHECK(tle.NoradNumber() == 5);
    CHECK(near(tle.Inclination(true), 34.2682, 1e-6));
    CHECK(near(tle.Eccentricity(), 0.1859667, 1e-9));
    CHECK(tle.Epoch().Year() == 2000 && tle.Epoch().Month() == 6 && tle.Epoch().Day() == 27);

    // ── 5-8: propagation vs the independent reference values ───────────
    SGP4 sgp4(tle);
    Eci eci0 = sgp4.FindPosition(0.0);
    Vector p0 = eci0.Position();
    Vector v0 = eci0.Velocity();
    CHECK(near(p0.x, 7022.465292664, 1e-4)
          && near(p0.y, -1400.082967554, 1e-4)
          && near(p0.z, 0.039951554, 1e-4));
    CHECK(near(v0.x, 1.893841015, 1e-7)
          && near(v0.y, 6.405893759, 1e-7)
          && near(v0.z, 4.534807250, 1e-7));

    Eci eci4320 = sgp4.FindPosition(4320.0);
    Vector p4 = eci4320.Position();
    Vector v4 = eci4320.Velocity();
    CHECK(near(p4.x, -9060.473735694, 1e-4)
          && near(p4.y, 4658.709525023, 1e-4)
          && near(p4.z, 813.686731534, 1e-4));
    CHECK(near(v4.x, -2.232832783, 1e-7)
          && near(v4.y, -4.110453490, 1e-7)
          && near(v4.z, -3.157345433, 1e-7));

    // ── 9: error signalling on upstream's "error code 2" fixture ───────
    // (SGP4-VER.TLE comment: "try and check error code 2", norad 33334 —
    //  the same case that yields 0 output rows in upstream's runtest.)
    const std::string e1 =
        "1 33334U 78066F   06174.85818871  .00000620  00000-0  10000-3 0  6809";
    const std::string e2 =
        "2 33334  68.4714 236.1303 5602877 123.7484 302.5767  0.00001000 67521      0.0      1440.0         1.00";
    bool signalled = false;
    try {
        SGP4 bad(Tle("error fixture", e1, e2.substr(0, Tle::LineLength())));
        bad.FindPosition(0.0);
    } catch (const SatelliteException &) {
        signalled = true;
    } catch (const DecayedException &) {
        signalled = true;
    }
    CHECK(signalled);

    // ── 10: look-angle API (Observer -> CoordTopocentric) ───────────────
    Observer obs(0.0, 0.0, 0.0);
    CoordTopocentric topo = obs.GetLookAngle(eci0);
    CHECK(topo.range > 0.0 && topo.elevation >= -90.0 && topo.elevation <= 90.0
          && topo.azimuth >= 0.0 && topo.azimuth <= 360.0);

    if (failures) {
        std::printf("libsgp4 consumer test: %d/10 assertion(s) FAILED\n", failures);
        return 1;
    }
    std::printf("libsgp4 consumer test OK: 10/10 assertions "
                "(tle-parse 4, propagation-vs-reference 4, error-signalling 1, look-angle 1)\n");
    return 0;
}
