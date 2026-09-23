#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "siscone/momentum.h"
#include "siscone/siscone.h"
#include "siscone/spherical/momentum.h"
#include "siscone/spherical/siscone.h"

// Consumer test for siscone 3.0.5: exercise both shipped libraries
// (libsiscone + libsiscone_spherical) through their real public API.
// Each passing assertion prints one CHECK-OK: line; the test_package
// conanfile counts them for the HMBS_TEST_PACKAGE_RESULT marker
// (4 lines required).
int main() {
    int checked = 0;

    std::string package = siscone::siscone_package_name();
    if (package.empty()) {
        std::fprintf(stderr, "siscone_package_name returned empty\n");
        return 1;
    }
    std::printf("CHECK-OK: package=%s\n", package.c_str());
    checked++;

    std::string version = siscone::siscone_version();
    if (version.empty()) {
        std::fprintf(stderr, "siscone_version returned empty\n");
        return 1;
    }
    std::printf("CHECK-OK: version=%s\n", version.c_str());
    checked++;
    if (version.find("3.0.5") == std::string::npos) {
        std::fprintf(stderr, "unexpected version=%s (want 3.0.5)\n", version.c_str());
        return 1;
    }

    // Cylindrical (hadronic) path: 3 well-separated particles, R=0.7.
    std::vector<siscone::Cmomentum> particles;
    particles.push_back(siscone::Cmomentum(30.0, 0.0, 10.0, 32.0));
    particles.push_back(siscone::Cmomentum(-20.0, 15.0, -5.0, 26.0));
    particles.push_back(siscone::Cmomentum(5.0, -25.0, 8.0, 27.0));
    siscone::Csiscone finder;
    int njets = finder.compute_jets(particles, 0.7, 0.5);
    if (njets < 0 || (std::size_t)njets != finder.jets.size()) {
        std::fprintf(stderr, "compute_jets inconsistent: %d vs %lu\n",
                     njets, (unsigned long)finder.jets.size());
        return 1;
    }
    std::printf("CHECK-OK: cylindrical njets=%d\n", njets);
    checked++;

    // Spherical (e+e-) path: 3 particles on the sphere, R=0.7.
    std::vector<siscone_spherical::CSphmomentum> sph_particles;
    sph_particles.push_back(siscone_spherical::CSphmomentum(1.0, 0.0, 0.0, 1.0));
    sph_particles.push_back(siscone_spherical::CSphmomentum(0.0, 1.0, 0.0, 1.0));
    sph_particles.push_back(siscone_spherical::CSphmomentum(0.0, 0.0, 1.0, 1.0));
    siscone_spherical::CSphsiscone sph_finder;
    int sph_njets = sph_finder.compute_jets(sph_particles, 0.7, 0.5);
    if (sph_njets < 0 || (std::size_t)sph_njets != sph_finder.jets.size()) {
        std::fprintf(stderr, "spherical compute_jets inconsistent: %d vs %lu\n",
                     sph_njets, (unsigned long)sph_finder.jets.size());
        return 1;
    }
    std::printf("CHECK-OK: spherical njets=%d\n", sph_njets);
    checked++;

    if (checked != 4) {
        std::fprintf(stderr, "checked=%d (want 4)\n", checked);
        return 1;
    }
    std::printf("siscone consumer test: OK (%d checks)\n", checked);
    return 0;
}
