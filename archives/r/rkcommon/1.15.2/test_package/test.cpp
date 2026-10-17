// rkcommon 1.15.2 consumer test: exercise real public API with assertions.
#include <rkcommon/math/vec.h>
#include <rkcommon/utility/Optional.h>
#include <rkcommon/containers/AlignedVector.h>
#include <rkcommon/utility/OnScopeExit.h>

#include <cstdio>

using namespace rkcommon;
namespace math = rkcommon::math;

static int failures = 0;
#define CHECK(cond)                                                        \
    do {                                                                   \
        if (!(cond)) {                                                     \
            std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);    \
            ++failures;                                                    \
        }                                                                  \
    } while (0)

int main()
{
    // math::vec3f — construction, arithmetic, dot/cross/length.
    math::vec3f a(1.f, 2.f, 2.f);
    math::vec3f b(4.f, 0.f, 0.f);
    CHECK(math::dot(a, b) == 4.f);
    CHECK(math::length(a) == 3.f);
    math::vec3f c = math::cross(a, b);
    CHECK(c == math::vec3f(0.f, 8.f, -8.f));

    // utility::Optional — engaged / disengaged states.
    utility::Optional<int> o1(42);
    utility::Optional<int> o2;
    CHECK(o1.has_value());
    CHECK(!o2.has_value());
    CHECK(o1.value() == 42);

    // containers::AlignedVector — sized growth and element access.
    containers::AlignedVector<float> v;
    v.push_back(1.f);
    v.push_back(2.f);
    v.push_back(3.f);
    CHECK(v.size() == 3);
    CHECK(v[0] == 1.f && v[2] == 3.f);

    // utility::OnScopeExit — RAII scope guard fires exactly once.
    int guard_hits = 0;
    {
        utility::OnScopeExit guard([&] { ++guard_hits; });
        CHECK(guard_hits == 0);
    }
    CHECK(guard_hits == 1);

    if (failures) {
        std::printf("rkcommon consumer test: %d failure(s)\n", failures);
        return 1;
    }
    std::printf("rkcommon consumer test OK: vec/Optional/AlignedVector/OnScopeExit\n");
    return 0;
}
