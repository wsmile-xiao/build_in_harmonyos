// test_package/consumer.cpp
//
// rule12 end-to-end consumer scenario for GMTL.
//
// This is not a bare assertion: it drives a *complete consumer workflow*
// through the public GMTL API, the way a real application would, and checks
// the numeric results of every stage:
//
//   1. Build an affine transform (translate + rotate) and push a point
//      through it.
//   2. Compare that against doing the same rotation/translation by hand with
//      quaternions and vectors.
//   3. Run a ray/sphere and ray/plane intersection and check we hit.
//   4. Fit an axis-aligned bounding box around a point cloud and verify
//      containment.
//   5. Round-trip a quaternion through matrix form and back, and verify the
//      rotation it applies is preserved.
//   6. Solve a quadratic with the library's math helpers.
//
// Every stage asserts; a non-zero exit means the library is broken.

#include <cmath>
#include <cstdio>
#include <iostream>

#include <gmtl/AABox.h>
#include <gmtl/AABoxOps.h>
#include <gmtl/AxisAngle.h>
#include <gmtl/Containment.h>
#include <gmtl/Generate.h>
#include <gmtl/Intersection.h>
#include <gmtl/LineSeg.h>
#include <gmtl/Matrix.h>
#include <gmtl/MatrixOps.h>
#include <gmtl/Math.h>
#include <gmtl/Output.h>
#include <gmtl/Plane.h>
#include <gmtl/Point.h>
#include <gmtl/Quat.h>
#include <gmtl/QuatOps.h>
#include <gmtl/Ray.h>
#include <gmtl/Sphere.h>
#include <gmtl/Vec.h>
#include <gmtl/VecOps.h>
#include <gmtl/Version.h>
#include <gmtl/Xforms.h>

namespace
{
int g_checks = 0;
int g_failed = 0;

void check(bool cond, const char* what)
{
   ++g_checks;
   if (!cond)
   {
      ++g_failed;
      std::cout << "  FAIL: " << what << std::endl;
   }
   else
   {
      std::cout << "  ok  : " << what << std::endl;
   }
}

bool near(float a, float b, float eps = 1e-4f)
{
   return std::fabs(a - b) <= eps;
}
} // namespace

int main()
{
   std::cout << "GMTL consumer end-to-end scenario" << std::endl;
   std::cout << "gmtl version: " << gmtl::getVersion() << std::endl << std::endl;

   // ------------------------------------------------------------------
   // 1. Build an affine transform: translate by (10,0,0), rotate 90deg
   //    about Z, and push the unit X point through it.
   // ------------------------------------------------------------------
   std::cout << "[1] transform pipeline" << std::endl;

   const float half_pi = static_cast<float>(gmtl::Math::PI) / 2.0f;

   gmtl::Matrix44f xform;
   gmtl::identity(xform);
   {
      gmtl::Matrix44f rot;
      gmtl::setRot(rot, gmtl::AxisAnglef(half_pi, 0.0f, 0.0f, 1.0f));
      gmtl::Matrix44f trans;
      gmtl::setTrans(trans, gmtl::Vec3f(10.0f, 0.0f, 0.0f));
      // rot then translate
      gmtl::mult(xform, trans, rot);
   }

   gmtl::Point3f p(1.0f, 0.0f, 0.0f);
   gmtl::Point3f moved = xform * p;
   check(near(moved[0], 10.0f), "rotate(90Z) then translate(10,0,0) -> x == 10");
   check(near(moved[1], 1.0f), "rotate(90Z) then translate(10,0,0) -> y == 1");
   check(near(moved[2], 0.0f), "rotate(90Z) then translate(10,0,0) -> z == 0");

   // ------------------------------------------------------------------
   // 2. Do the same by hand with a quaternion, and compare.
   // ------------------------------------------------------------------
   std::cout << "[2] quaternion cross-check" << std::endl;

   gmtl::Quatf q = gmtl::makeRot<gmtl::Quatf>(gmtl::AxisAnglef(half_pi, 0.0f, 0.0f, 1.0f));
   gmtl::Vec3f by_hand = q * gmtl::Vec3f(1.0f, 0.0f, 0.0f);
   by_hand += gmtl::Vec3f(10.0f, 0.0f, 0.0f);
   check(near(by_hand[0], moved[0]), "quat path matches matrix path (x)");
   check(near(by_hand[1], moved[1]), "quat path matches matrix path (y)");
   check(near(by_hand[2], moved[2]), "quat path matches matrix path (z)");

   // ------------------------------------------------------------------
   // 3. Ray/sphere and ray/plane intersection.
   // ------------------------------------------------------------------
   std::cout << "[3] intersection" << std::endl;

   gmtl::Spheref sphere(gmtl::Point3f(0.0f, 0.0f, 0.0f), 1.0f);
   gmtl::Rayf ray(gmtl::Point3f(-5.0f, 0.0f, 0.0f), gmtl::Vec3f(1.0f, 0.0f, 0.0f));
   unsigned int num_hits = 0;
   float t0 = 0.0f;
   float t1 = 0.0f;
   bool hit_sphere = gmtl::intersect(sphere, ray, num_hits, t0, t1);
   check(hit_sphere, "ray hits unit sphere on the X axis");
   check(hit_sphere && num_hits == 2u, "ray/sphere reports 2 shell hits");
   check(hit_sphere && near(t0, 4.0f), "ray/sphere entry t0 == 4");
   check(hit_sphere && near(t1, 6.0f), "ray/sphere exit  t1 == 6");

   // Plane through (3,0,0) with normal (1,0,0), i.e. the x = 3 plane.  gmtl's
   // Plane stores the offset as dot(point_on_plane, normal), so the ray
   // travelling +X from (-5,0,0) meets it at t = 8.
   gmtl::Planef plane(gmtl::Vec3f(1.0f, 0.0f, 0.0f),
                      gmtl::Point3f(3.0f, 7.0f, -2.0f));
   float t_plane = 0.0f;
   bool hit_plane = gmtl::intersect(plane, ray, t_plane);
   check(hit_plane, "ray hits the x=3 plane");
   check(hit_plane && near(t_plane, 8.0f), "ray/plane t == 8");

   // ------------------------------------------------------------------
   // 4. Fit an AABB around a point cloud and check containment.
   // ------------------------------------------------------------------
   std::cout << "[4] bounding box" << std::endl;

   gmtl::Point3f cloud[4] = {
      gmtl::Point3f(-1.0f, -2.0f, -3.0f),
      gmtl::Point3f(4.0f, 0.0f, 0.0f),
      gmtl::Point3f(2.0f, 5.0f, 1.0f),
      gmtl::Point3f(0.0f, 1.0f, 7.0f),
   };
   gmtl::AABoxf box;
   box.setEmpty(true); // start uninitialised, then grow over the cloud
   for (int i = 0; i < 4; ++i)
   {
      gmtl::extendVolume(box, cloud[i]);
   }
   check(near(box.getMin()[0], -1.0f) && near(box.getMin()[1], -2.0f) &&
            near(box.getMin()[2], -3.0f),
         "AABB min == (-1,-2,-3)");
   check(near(box.getMax()[0], 4.0f) && near(box.getMax()[1], 5.0f) &&
            near(box.getMax()[2], 7.0f),
         "AABB max == (4,5,7)");
   for (int i = 0; i < 4; ++i)
   {
      check(gmtl::isInVolume(box, cloud[i]), "every cloud point is inside the AABB");
   }
   check(!gmtl::isInVolume(box, gmtl::Point3f(100.0f, 0.0f, 0.0f)),
         "a far-away point is outside the AABB");

   // ------------------------------------------------------------------
   // 5. Quat -> matrix -> quat round trip preserves the rotation.
   // ------------------------------------------------------------------
   std::cout << "[5] quat/matrix round trip" << std::endl;

   // gmtl's AxisAngle requires a *normalised* axis: setRot() asserts on a
   // non-unit axis and otherwise silently produces a non-unit quaternion,
   // which is why the axis below is normalised by hand.
   const gmtl::Vec3f axis =
      gmtl::makeNormal(gmtl::Vec3f(1.0f, 2.0f, 3.0f));

   gmtl::Quatf q_orig = gmtl::makeRot<gmtl::Quatf>(
      gmtl::AxisAnglef(0.7f, axis[0], axis[1], axis[2]));
   check(near(gmtl::length(q_orig), 1.0f), "rotation quaternion is unit length");

   gmtl::Matrix44f m_rt = gmtl::makeRot<gmtl::Matrix44f>(q_orig);
   gmtl::Quatf q_back = gmtl::makeRot<gmtl::Quatf>(m_rt);

   gmtl::Vec3f probe(0.3f, -0.9f, 0.5f);
   gmtl::Vec3f v1 = q_orig * probe;
   gmtl::Vec3f v2 = q_back * probe;
   check(near(v1[0], v2[0]) && near(v1[1], v2[1]) && near(v1[2], v2[2]),
         "quat->matrix->quat preserves the applied rotation");

   gmtl::Matrix44f m_direct = gmtl::makeRot<gmtl::Matrix44f>(q_orig);
   gmtl::Vec3f v3 = m_direct * probe;
   check(near(v1[0], v3[0]) && near(v1[1], v3[1]) && near(v1[2], v3[2]),
         "quaternion and matrix forms agree on the probe vector");

   // ------------------------------------------------------------------
   // 6. Math helpers.
   // ------------------------------------------------------------------
   std::cout << "[6] math helpers" << std::endl;

   float r1 = 0.0f, r2 = 0.0f;
   bool solved = gmtl::Math::quadraticFormula(r1, r2, 1.0f, -3.0f, 2.0f);
   check(solved, "quadraticFormula(x^2-3x+2) returns real roots");
   check(solved && (near(r1, 2.0f) || near(r2, 2.0f)) &&
            (near(r1, 1.0f) || near(r2, 1.0f)),
         "roots of x^2-3x+2 are 1 and 2");
   check(near(gmtl::Math::deg2Rad(180.0f), static_cast<float>(gmtl::Math::PI)),
         "deg2Rad(180) == PI");

   // ------------------------------------------------------------------
   std::cout << std::endl
             << "checks: " << g_checks << "  failed: " << g_failed << std::endl;

   if (g_failed != 0)
   {
      std::cout << "CONSUMER E2E: FAILED" << std::endl;
      return 1;
   }
   std::cout << "CONSUMER E2E: PASSED (" << g_checks << "/" << g_checks << ")"
             << std::endl;
   return 0;
}
