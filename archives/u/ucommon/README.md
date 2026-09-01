# GNU uCommon C++

GNU uCommon C++ is a portable C++ library providing threading, socket,
common utility, and secure/TLS abstraction APIs. The 7.0.1 source is the
Debian-maintained release of the GNU Common C++ project.

## HarmonyOS PC

The Conan recipe builds the CMake project for HarmonyOS PC arm64 with the
default GnuTLS backend. `PkgConfigDeps` supplies the generated dependency
metadata required by the upstream CMake detection logic. The package keeps
the upstream `ucommon`, `usecure`, and `commoncpp` static libraries available
to consumers.

## Dependencies

- `gnutls/3.8.10` is the default TLS dependency.
- `openssl/3.5.6` is available when `with_ssl=openssl` is selected.
- `pkgconf/3.0.5` is used only at build time.

## References

- [GNU Common C++](https://www.gnu.org/software/commoncpp/)
- [Debian source package](https://packages.debian.org/source/sid/ucommon)
