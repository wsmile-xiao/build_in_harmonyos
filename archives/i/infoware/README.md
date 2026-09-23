# infoware

infoware is a C++14 system information library reporting CPU quantities,
caches, instruction sets, memory amounts, kernel/OS facts and PCI devices.
The `0.6.0` recipe builds the upstream CMake project natively on OHOS with
clang (presented as generic Linux/aarch64) and installs the static library
with its public headers; it declares no Conan package dependencies.

Upstream's x86-only cpuid inline assembly is guarded by architecture macros
with a zero-filled fallback for aarch64, and the pci.ids hardware database
required at build time is pinned from the official pciutils/pciids snapshot.
The upstream 4-example CTest suite runs inside the recipe build.
