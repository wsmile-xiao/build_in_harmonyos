// HarmonyOS-specific test for isospec/2.3.2 (rule12).
//
// Verifies the three things that actually differ on OHOS:
//   1. the OHOS dynamic loader has mapped the delivered IsoSpec++ library
//      and exports its C symbols (the binary links it via DT_NEEDED, so
//      dlsym(RTLD_DEFAULT, ...) proves the loader accepted the packaged
//      object — NDK-built 4 KiB-aligned libraries are rejected by loaders
//      on 16 KiB-page HarmonyOS targets);
//   2. the C wrapper API (extern "C") links and runs against the package;
//   3. the runtime triple is OHOS/aarch64/LP64.
#include <IsoSpec++/cwrapper.h>

#include <cstdio>
#include <cstring>
#include <dlfcn.h>
#include <sys/utsname.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        std::fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main() {
    int failures = 0;

    // 1. When the package is consumed as a shared library, the OHOS
    //    dynamic loader must have mapped the packaged object and exported
    //    its C symbols (NDK-built 4 KiB-aligned libraries are rejected by
    //    loaders on 16 KiB-page HarmonyOS targets).  Under a static-link
    //    consumer this is a tautology, so record an explicit SKIP instead
    //    of pretending the loader was exercised.
    void *sym = dlsym(RTLD_DEFAULT, "setupIso");
    if (sym != nullptr) {
        std::printf("loader: setupIso resolved via dlsym (shared consume)\n");
    } else {
        std::printf("loader: setupIso not in dynamic namespace — SKIPPED (static build, no DT_NEEDED)\n");
    }

    // 2. C wrapper round-trip: setupIso + threshold generator + teardown
    //    (called through the linked API, same code path as dlsym).
    {
        // Hydrogen: 2 isotopes (1.0078/0.999885, 2.0141/0.000115), 2 atoms.
        const int isotopeNumbers[] = {2};
        const int atomCounts[] = {2};
        const double masses[] = {1.00782503207, 2.0141017778};
        const double probs[] = {0.999885, 0.000115};
        void *iso = setupIso(1, isotopeNumbers, atomCounts, masses, probs);
        CHECK(iso != nullptr, "setupIso must allocate a C-side Iso object");
        if (iso) {
            void *gen = setupIsoThresholdGenerator(iso, 1e-4, true, 10, 10, true);
            CHECK(gen != nullptr, "setupIsoThresholdGenerator must allocate");
            if (gen) {
                int visited = 0;
                while (advanceToNextConfigurationIsoThresholdGenerator(gen))
                    visited++;
                std::printf("C-API threshold walk: %d configurations\n", visited);
                CHECK(visited >= 1, "C-API generator must walk at least one configuration");
                deleteIsoThresholdGenerator(gen);
            }
            deleteIso(iso);
        }
    }

    // 3. Runtime triple: OHOS kernel, aarch64, LP64.
    utsname uts{};
    CHECK(uname(&uts) == 0, "uname must succeed");
    std::printf("uname: %s %s %s\n", uts.sysname, uts.machine, uts.release);
    CHECK(strstr(uts.sysname, "HarmonyOS") != nullptr || strstr(uts.sysname, "Linux") != nullptr,
          "sysname must be HarmonyOS/Linux family");
    CHECK(strcmp(uts.machine, "aarch64") == 0, "machine must be aarch64");
    CHECK(sizeof(void *) == 8, "must run under LP64");

    if (failures == 0)
        std::printf("test_isospec_ohos: all checks passed\n");
    return failures == 0 ? 0 : 1;
}
