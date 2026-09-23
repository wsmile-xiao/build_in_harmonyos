# boost-defaults

Debian "default Boost version" metapackage. Requirements-only Conan package
that pins the default Boost version to 1.90 (`requires boost/1.90.0`) and
exposes the boost default component set under the `boost-defaults` namespace,
mirroring the semantics of Debian `libboost-dev` (default version).

Upstream: https://salsa.debian.org/debian/boost-defaults (tag debian/1.90.0.2)
