# OpenMesh

OpenMesh is a generic and efficient polygon mesh data structure and processing
library. This archive entry packages the official `11.0.0` release for Conan
consumers on Linux and OpenHarmony.

The public consumer test constructs and validates a triangle mesh, performs an
OFF round trip, and confirms that an intentionally missing mesh file is
rejected. The upstream GoogleTest inventory is validated separately because
the production package build intentionally excludes test-only dependencies.
