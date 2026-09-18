// test_openmm.cpp — Consumer test for OpenMM 8.1.2
// Verifies: library links correctly, API is callable, version matches.
#include <OpenMM.h>
#include <iostream>
#include <string>

int main() {
    // Get OpenMM version string
    std::string version = OpenMM::Platform::getOpenMMVersion();
    std::cout << "OpenMM version: " << version << std::endl;

    // Verify version matches expected release
    if (version != "8.1.2") {
        std::cerr << "FAIL: unexpected version " << version
                  << " (expected 8.1.2)" << std::endl;
        return 1;
    }

    // Create a simple molecular system
    OpenMM::System system;

    // Add a particle (hydrogen mass in AMU)
    system.addParticle(1.008);

    // Verify the particle was added
    if (system.getNumParticles() != 1) {
        std::cerr << "FAIL: expected 1 particle, got "
                  << system.getNumParticles() << std::endl;
        return 1;
    }

    // Load the packaged plugins (OPENMM_PLUGIN_DIR is exported by the recipe's
    // runenv; the recipe's SONAME fix is what makes the plugin libraries
    // resolvable by the dynamic loader).
    OpenMM::Platform::loadPluginsFromDirectory(
        OpenMM::Platform::getDefaultPluginsDirectory());

    // Get available platforms
    int numPlatforms = OpenMM::Platform::getNumPlatforms();
    std::cout << "Available platforms: " << numPlatforms << std::endl;
    for (int i = 0; i < numPlatforms; i++) {
        std::string platName = OpenMM::Platform::getPlatform(i).getName();
        std::cout << "  Platform " << i << ": " << platName << std::endl;
    }

    // Reference is compiled into libOpenMM; CPU is a dlopen'ed plugin from
    // lib/plugins — both must be present for the package to be functional.
    bool hasReference = false;
    bool hasCPU = false;
    for (int i = 0; i < numPlatforms; i++) {
        std::string platName = OpenMM::Platform::getPlatform(i).getName();
        if (platName == "Reference") hasReference = true;
        if (platName == "CPU") hasCPU = true;
    }

    if (!hasReference) {
        std::cerr << "FAIL: Reference platform not available" << std::endl;
        return 1;
    }
    if (!hasCPU) {
        std::cerr << "FAIL: CPU platform plugin not loaded "
                  << "(dlopen of lib/plugins failed?)" << std::endl;
        return 1;
    }

    std::cout << "PASS: OpenMM 8.1.2 working correctly" << std::endl;
    return 0;
}
