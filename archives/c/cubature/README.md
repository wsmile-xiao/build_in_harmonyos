# Cubature

Cubature is Steven G. Johnson's C library for adaptive multidimensional
integration of scalar- and vector-valued functions over hypercubes. It
provides h-adaptive and p-adaptive algorithms together with scalar and
vectorized callback interfaces.

- Upstream: https://github.com/stevengj/cubature
- Version: 1.0.4 (`v1.0.4`)
- License: GPL-2.0-or-later

## HarmonyOS PC adaptation

The upstream CMake build works with the HarmonyOS Clang toolchain without a
source patch. The recipe supplies the compatibility policy required by modern
CMake, packages the public header and shared library, and declares the system
math library needed by consumers.

The validation runs both upstream algorithms over all nine bundled integrand
scenarios, builds an installed-package consumer that exercises the scalar and
vectorized APIs, and runs a HarmonyOS-only signed-library loading and target
identity test.
