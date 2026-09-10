# gklib 5.1.1

GKlib provides the C helper routines and data structures used by METIS and
other KarypisLab projects. This Conan package builds the library without the
optional PCRE, OpenMP, GKRAND, or bundled-regex features and exposes the CMake
target `GKlib::GKlib`.

The upstream `test/` directory contains ten standalone executables and no
CTest registrations. Two are deterministic no-argument self-checks; the other
eight require external input files. The package remains library-only, while
target validation rebuilds the two eligible unchanged sources against the
installed library. A separate package consumer exercises allocation, string,
integer math, and key/value sorting APIs.

Upstream source: https://github.com/KarypisLab/GKlib/tree/METIS-v5.1.1-DistDGL-0.5
