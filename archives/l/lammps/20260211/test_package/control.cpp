// Control self-proof for the lammps test package: compiled and run with the
// exact toolchain the recipe used, so any lmp failure below is attributable to
// lammps itself rather than to the device toolchain.
#include <cstdio>
int main() {
  std::printf("CONTROL_OK\n");
  return 0;
}
