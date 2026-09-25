// Consumer test for isospec/2.3.2 — exercises the C++ API that the
// package delivers (include/IsoSpec++/), both generator-based streaming
// and the FixedEnvelope collector.  This file is the L1 test that
// `conan create` runs automatically.
#include <IsoSpec++/isoSpec++.h>
#include <IsoSpec++/fixedEnvelopes.h>

#include <cmath>
#include <cstdio>

using namespace IsoSpec;

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        std::fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main() {
    int failures = 0;

    // 1. Threshold streaming: water at 0.01 must yield the dominant
    //    isotopologue (1H-2-16O ~ 0.998).
    {
        IsoThresholdGenerator iso("H2O1", 0.01, true, 10, 10, true);
        const size_t confs = iso.count_confs();
        std::printf("H2O1 @ threshold 0.01: %zu configurations\n", confs);
        CHECK(confs >= 1, "water must yield at least one configuration above 0.01");
    }

    // 2. Total-probability collector: 0.999 requested coverage must be
    //    delivered within tolerance.
    {
        FixedEnvelope env = FixedEnvelope::FromTotalProb("C1H1O2N2Se1Sn1P1", 0.999, true, true);
        double total = 0.0;
        for (size_t ii = 0; ii < env.confs_no(); ii++)
            total += env.prob(ii);
        std::printf("C1H1O2N2Se1Sn1P1 @ 0.999: %zu confs, prob sum %.8f\n",
                    env.confs_no(), total);
        CHECK(env.confs_no() > 0, "collector must produce configurations");
        CHECK(total >= 0.99 && total <= 1.01, "probability mass must cover ~0.999");
        CHECK(std::isfinite(env.mass(0)) && env.mass(0) > 0.0,
              "first configuration must carry a positive finite mass");
    }

    if (failures == 0)
        std::printf("test_isospec: all checks passed\n");
    return failures == 0 ? 0 : 1;
}
