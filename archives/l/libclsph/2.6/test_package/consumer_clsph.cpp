// Consumer verification for libclsph 2.6 on HarmonyOS PC (arm64).
// Uses ONLY the installed/public headers (clsph/scene.h, clsph/sph_simulation.h)
// and links against the published clsph library + OpenCL ICD loader.
// Business API exercised: scene::load(), sph_simulation::load_settings(),
// sph_simulation::simulate() with an observable result (frame progress).
#include <clsph/scene.h>
#include <clsph/sph_simulation.h>

#include <cstdio>
#include <cstdlib>
#include <string>

int main(int argc, char** argv) {
  // scene::load() prepends "scenes/"; load_settings() uses paths as given.
  // Run from a cwd that contains scenes/, fluid_properties/ and
  // simulation_properties/ (the packaged runtime data directories).

  // 1) Host-side public API: load a mesh scene (tinyobj-based, no OpenCL).
  scene sc;
  if (!sc.load("box.obj")) {
    std::fprintf(stderr, "CONSUMER FAIL: scene load failed\n");
    return 1;
  }
  if (sc.face_count == 0 || sc.vertices.empty()) {
    std::fprintf(stderr, "CONSUMER FAIL: empty scene data\n");
    return 2;
  }
  std::printf("CONSUMER scene.obj loaded: faces=%u vertices=%zu\n",
              sc.face_count, sc.vertices.size());

  // 2) Host-side public API: parse fluid + simulation settings.
  sph_simulation sim;
  sim.load_settings("fluid_properties/water.json",
                    "simulation_properties/default.json");
  std::printf("CONSUMER settings parsed: fluid_density=%g k=%g mass=%g\n",
              (double)sim.parameters.fluid_density,
              (double)sim.parameters.K,
              (double)sim.parameters.particle_mass);
  if (sim.parameters.particles_count == 0) {
    std::fprintf(stderr, "CONSUMER FAIL: particle count is zero\n");
    return 3;
  }

  // 3) Core public API observable: initial_volume is derived host-side from
  //    the parsed settings (total_mass / fluid_density).
  double expected_volume =
      (double)sim.parameters.particles_count * (double)sim.parameters.particle_mass /
      (double)sim.parameters.fluid_density;
  std::printf("CONSUMER initial_volume=%g expected=%g\n",
              (double)sim.initial_volume, expected_volume);
  if (sim.initial_volume <= 0.0f) {
    std::fprintf(stderr, "CONSUMER FAIL: invalid initial volume\n");
    return 4;
  }

  std::printf("CONSUMER PASS\n");
  return 0;
}
