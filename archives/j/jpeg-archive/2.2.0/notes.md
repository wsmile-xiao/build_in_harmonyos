# jpeg-archive 2.2.0

The upstream tag v2.2.0 uses a Makefile. The recipe builds the three ELF
utilities against the published mozjpeg/4.1.1 package and installs the
upstream jpeg-archive shell wrapper alongside them.

Source SHA-256:
3da16a5abbddd925dee0379aa51d9fe0cba33da0b5703be27c13a2dda3d7ed75

Upstream test coverage is recorded in manifest.yaml. The upstream make test
target compiles and executes a target binary, so it is not run on the
cross-build host. The Conan test_package performs functional target-side
checks by generating a PPM image, recompressing it to JPEG, comparing the
generated JPEG with itself, and verifying repeated jpeg-hash output.
