// Consumer test for the packaged erkir 2.1.1 (HarmonyOS PC / OHOS, arm64).
//
// Links the INSTALLED package (find_package(erkir CONFIG)) and calls real
// public APIs only — no stubs, no printf-only smoke (R34 / PF3).
// Expected values are the upstream-documented ones: test/test.cpp in the
// v2.1.1 tarball asserts the very same numbers with the same 0.001
// tolerance, so a pass here also proves the packaged library computes what
// upstream claims on this platform.
#include "cartesianpoint.h"
#include "coordinate.h"
#include "datum.h"
#include "ellipsoidalpoint.h"
#include "sphericalpoint.h"
#include "vector3d.h"

#include <cmath>
#include <cstdio>

using namespace erkir;

namespace {

int g_total = 0;
int g_failed = 0;

void check_near(const char *what, double actual, double expected, double eps)
{
  ++g_total;
  if (!std::isfinite(actual) || std::fabs(actual - expected) > eps) {
    std::fprintf(stderr, "FAIL %s: actual=%.6f expected=%.6f (eps=%g)\n",
                 what, actual, expected, eps);
    ++g_failed;
  }
}

} // namespace

int main()
{
  // ── spherical model (haversine / rhumb) ──────────────────────────────
  const spherical::Point london{52.205, 0.119};
  const spherical::Point paris{48.857, 2.351};
  check_near("spherical.distanceTo(London,Paris)", london.distanceTo(paris),
             404279.164, 0.001);
  check_near("spherical.bearingTo(London,Paris)", london.bearingTo(paris),
             156.167, 0.001);
  check_near("spherical.finalBearingTo(London,Paris)", london.finalBearingTo(paris),
             157.890, 0.001);

  const auto dest = spherical::Point{51.4778, -0.0015}.destinationPoint(7794.0, 300.7);
  check_near("spherical.destinationPoint.lat", dest.latitude().degrees(),
             51.5135, 0.001);
  check_near("spherical.destinationPoint.lon", dest.longitude().degrees(),
             -0.0983, 0.001);

  check_near("spherical.areaOf(unit-polygon)",
             spherical::Point::areaOf({{0, 0}, {1, 0}, {0, 1}}),
             6182469722.731, 0.001);

  // ── ellipsoidal model (Vincenty) ─────────────────────────────────────
  const ellipsoidal::Point cornwall{50.06632, -5.71475};
  const ellipsoidal::Point scotland{58.64402, -3.07009};
  check_near("ellipsoidal.distanceTo(Vincenty)", cornwall.distanceTo(scotland),
             969954.169, 0.001);
  check_near("ellipsoidal.initialBearingTo", cornwall.initialBearingTo(scotland),
             9.1419, 0.001);

  ellipsoidal::Point wgs84{53.0, 1.0, 50.0};
  const auto osgb = wgs84.toDatum(ellipsoidal::Datum::Type::OSGB36);
  check_near("ellipsoidal.toDatum(OSGB36).lat", osgb.latitude().degrees(),
             52.9996, 0.001);
  check_near("ellipsoidal.toDatum(OSGB36).height", osgb.height(), 3.987, 0.001);

  // ── ECEF round trip ──────────────────────────────────────────────────
  const auto ecef = ellipsoidal::Point{45.0, 45.0}.toCartesianPoint();
  check_near("cartesian.ECEF.x", ecef->x(), 3194419.145, 0.001);

  const auto roundtrip = cartesian::Point{3194419.0, 3194419.0, 4487348.0}.toGeoPoint();
  check_near("cartesian.toGeoPoint.lat", roundtrip->latitude().degrees(), 45.0, 0.0001);
  check_near("cartesian.toGeoPoint.lon", roundtrip->longitude().degrees(), 45.0, 0.0001);

  // ── 3-d vector helpers ───────────────────────────────────────────────
  const Vector3d v123{1.0, 2.0, 3.0};
  const Vector3d v321{3.0, 2.0, 1.0};
  check_near("vector.dot", v123.dot(v321), 10.0, 1e-9);
  check_near("vector.length", v123.length(), 3.7416573867739413, 1e-9);
  check_near("vector.cross.x", v123.cross(v321).x(), -4.0, 1e-9);

  // ── coordinate helpers ───────────────────────────────────────────────
  check_near("Coordinate.wrap360(-1)", Coordinate::wrap360(-1.0), 359.0, 1e-9);
  check_near("Coordinate.toRadians(180)", Coordinate::toRadians(180.0),
             Coordinate::pi(), 1e-9);

  std::printf("ERKIR_TEST_PACKAGE_RESULT total=%d passed=%d failed=%d\n",
              g_total, g_total - g_failed, g_failed);
  return g_failed == 0 ? 0 : 1;
}
