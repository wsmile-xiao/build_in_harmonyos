// Consumer test for mathfu 1.1.0 (header-only C++ math library).
//
// Real-API verification of vectors, matrices and quaternions through the
// installed mathfu headers: arithmetic operators, dot/cross products,
// normalization, lerp, matrix multiply/transpose/inverse, affine
// translation, perspective projection and quaternion rotation.

#include <cmath>
#include <cstdio>

#include "mathfu/constants.h"
#include "mathfu/glsl_mappings.h"
#include "mathfu/matrix.h"
#include "mathfu/matrix_4x4.h"
#include "mathfu/quaternion.h"
#include "mathfu/rect.h"
#include "mathfu/vector.h"

namespace {

int g_failures = 0;

void Check(bool condition, const char* description) {
  if (condition) {
    std::printf("PASS: %s\n", description);
  } else {
    std::printf("FAIL: %s\n", description);
    ++g_failures;
  }
}

bool Near(float a, float b, float epsilon) {
  return std::fabs(a - b) <= epsilon;
}

// Vector arithmetic, dot product, cross product and length (assertion 1-6).
void TestVectorBasics() {
  mathfu::vec3 a(1.0f, 2.0f, 3.0f);
  mathfu::vec3 b(4.0f, 5.0f, 6.0f);

  mathfu::vec3 sum = a + b;
  Check(Near(sum.x, 5.0f, 1e-6f) && Near(sum.y, 7.0f, 1e-6f) &&
            Near(sum.z, 9.0f, 1e-6f),
        "vector addition a+b = (5, 7, 9)");

  mathfu::vec3 scaled = a * 2.0f;
  Check(Near(scaled.x, 2.0f, 1e-6f) && Near(scaled.y, 4.0f, 1e-6f) &&
            Near(scaled.z, 6.0f, 1e-6f),
        "vector scaling a*2 = (2, 4, 6)");

  float dot = mathfu::vec3::DotProduct(a, b);
  Check(Near(dot, 32.0f, 1e-5f), "dot product a.b = 32");

  mathfu::vec3 cross = mathfu::vec3::CrossProduct(a, b);
  Check(Near(cross.x, -3.0f, 1e-6f) && Near(cross.y, 6.0f, 1e-6f) &&
            Near(cross.z, -3.0f, 1e-6f),
        "cross product a x b = (-3, 6, -3)");

  Check(Near(a.Length(), std::sqrt(14.0f), 1e-5f), "vector length |a| = sqrt(14)");
  Check(Near(a.LengthSquared(), 14.0f, 1e-5f), "vector length squared = 14");
}

// Normalization and lerp (assertion 7-8).
void TestVectorNormalizedLerp() {
  mathfu::vec3 v(3.0f, 4.0f, 0.0f);
  mathfu::vec3 n = v.Normalized();
  Check(Near(n.Length(), 1.0f, 1e-6f) && Near(n.x, 0.6f, 1e-6f) &&
            Near(n.y, 0.8f, 1e-6f),
        "normalized (3,4,0) = (0.6, 0.8, 0)");

  mathfu::vec3 l0(0.0f, 0.0f, 0.0f);
  mathfu::vec3 l1(10.0f, 20.0f, 30.0f);
  mathfu::vec3 mid = mathfu::vec3::Lerp(l0, l1, 0.25f);
  Check(Near(mid.x, 2.5f, 1e-6f) && Near(mid.y, 5.0f, 1e-6f) &&
            Near(mid.z, 7.5f, 1e-6f),
        "lerp(l0, l1, 0.25) = (2.5, 5, 7.5)");
}

// Matrix multiply, transpose and inverse of a 3x3 matrix (assertion 9-13).
void TestMatrixOps() {
  mathfu::mat3 m(1.0f, 2.0f, 3.0f, 4.0f, 5.0f, 6.0f, 7.0f, 8.0f, 10.0f);
  mathfu::mat3 inv;
  bool invertible = m.InverseWithDeterminantCheck(&inv);
  Check(invertible, "3x3 matrix with det=3 is invertible");

  mathfu::mat3 product = m * inv;
  bool identity = true;
  for (int c = 0; c < 3; ++c) {
    for (int r = 0; r < 3; ++r) {
      const float expected = (r == c) ? 1.0f : 0.0f;
      if (!Near(product(c, r), expected, 1e-4f)) {
        identity = false;
      }
    }
  }
  Check(identity, "m * inverse(m) = identity");

  mathfu::mat3 t = m.Transpose();
  Check(Near(t(1, 0), m(0, 1), 1e-7f) && Near(t(2, 1), m(1, 2), 1e-7f),
        "transpose swaps (i,j) with (j,i)");

  mathfu::mat3 singular(1.0f, 2.0f, 3.0f, 2.0f, 4.0f, 6.0f, 1.0f, 1.0f, 1.0f);
  mathfu::mat3 singular_inv;
  Check(!singular.InverseWithDeterminantCheck(&singular_inv),
        "singular matrix fails the determinant check");

  mathfu::vec3 e0(1.0f, 0.0f, 0.0f);
  mathfu::vec3 col0 = m * e0;
  Check(Near(col0.x, 1.0f, 1e-6f) && Near(col0.y, 2.0f, 1e-6f) &&
            Near(col0.z, 3.0f, 1e-6f),
        "matrix-vector multiply m*e0 returns the first column (1, 2, 3)");
}

// Affine translation and 4x4 matrix-vector multiply (assertion 14-15).
void TestMatrixAffine() {
  mathfu::vec3 offset(5.0f, -2.0f, 1.0f);
  mathfu::mat4 translate =
      mathfu::mat4::FromTranslationVector(offset);
  mathfu::vec3 origin(0.0f, 0.0f, 0.0f);
  mathfu::vec3 moved = translate * origin;
  Check(Near(moved.x, 5.0f, 1e-6f) && Near(moved.y, -2.0f, 1e-6f) &&
            Near(moved.z, 1.0f, 1e-6f),
        "translation matrix moves the origin to (5, -2, 1)");

  mathfu::vec4 corner(1.0f, 1.0f, 1.0f, 1.0f);
  mathfu::vec4 transformed = translate * corner;
  Check(Near(transformed.x, 6.0f, 1e-6f) && Near(transformed.y, -1.0f, 1e-6f) &&
            Near(transformed.z, 2.0f, 1e-6f) && Near(transformed.w, 1.0f, 1e-6f),
        "translation matrix acts on a 4d point");
}

// Perspective projection: point on the near plane maps to w == near.
void TestMatrixPerspective() {
  const float kFovY = static_cast<float>(M_PI) / 4.0f;
  const float kAspect = 1.0f;
  const float kNear = 1.0f;
  const float kFar = 100.0f;
  mathfu::mat4 persp =
      mathfu::mat4::Perspective(kFovY, kAspect, kNear, kFar);
  mathfu::vec4 on_near(0.0f, 0.0f, -kNear, 1.0f);
  mathfu::vec4 clipped = persp * on_near;
  Check(Near(clipped.w, kNear, 1e-4f),
        "perspective: near-plane point keeps w == near");
}

// Quaternion rotation: +90 degrees around Z maps +X onto +Y (assertion 17-20).
void TestQuaternionRotation() {
  const float kHalfPi = static_cast<float>(M_PI) / 2.0f;
  mathfu::quat rotation =
      mathfu::quat::FromAngleAxis(kHalfPi, mathfu::vec3(0.0f, 0.0f, 1.0f));
  mathfu::vec3 x_axis(1.0f, 0.0f, 0.0f);
  mathfu::vec3 rotated = rotation * x_axis;
  Check(Near(rotated.x, 0.0f, 1e-4f) && Near(rotated.y, 1.0f, 1e-4f) &&
            Near(rotated.z, 0.0f, 1e-4f),
        "quaternion +90 deg around Z rotates +X to +Y");

  mathfu::quat composed =
      rotation * mathfu::quat::identity;
  mathfu::vec3 rotated_again = composed * x_axis;
  Check(Near(rotated_again.y, 1.0f, 1e-4f),
        "multiplying by the identity quaternion preserves the rotation");

  mathfu::vec3 recovered;
  float angle = 0.0f;
  rotation.ToAngleAxis(&angle, &recovered);
  Check(Near(angle, kHalfPi, 1e-4f) && Near(recovered.z, 1.0f, 1e-4f),
        "ToAngleAxis recovers 90 degrees around +Z");

  mathfu::mat3 rot_matrix = rotation.ToMatrix();
  mathfu::vec3 via_matrix = rot_matrix * x_axis;
  Check(Near(via_matrix.y, 1.0f, 1e-4f),
        "ToMatrix matches the quaternion rotation");
}

// GLSL-style typedefs and packed constants (assertion 21-23).
void TestGlslMappings() {
  mathfu::vec2 ones = mathfu::kOnes2f;
  Check(Near(ones.x, 1.0f, 1e-6f) && Near(ones.y, 1.0f, 1e-6f),
        "GLSL mapping vec2 works with kOnes2f constant");

  mathfu::vec3 zeros = mathfu::kZeros3f;
  Check(Near(zeros.x, 0.0f, 1e-6f) && Near(zeros.z, 0.0f, 1e-6f),
        "GLSL mapping vec3 works with kZeros3f constant");

  mathfu::rectf rect(0.0f, 0.0f, 4.0f, 2.0f);
  Check(Near(rect.pos.x, 0.0f, 1e-6f) && Near(rect.size.x, 4.0f, 1e-6f) &&
            Near(rect.size.y, 2.0f, 1e-6f),
        "Rect<float> stores pos and size vectors");
}

}  // namespace

int main() {
  TestVectorBasics();
  TestVectorNormalizedLerp();
  TestMatrixOps();
  TestMatrixAffine();
  TestMatrixPerspective();
  TestQuaternionRotation();
  TestGlslMappings();

  std::printf("\n%d checks failed\n", g_failures);
  return g_failures == 0 ? 0 : 1;
}
