# clthreads 2.4.0 adaptation notes

The upstream release is a Makefile-only project with no bundled test suite.
The adaptation adds a `make check` target that builds and runs an API-level
test in the source tree. Its installation target hardcodes `g++`, host tool
paths, and `ldconfig`; the portability patch makes compiler selection,
shared-library symlinks, and staging installation work with Conan and
OpenHarmony.

OpenHarmony does not provide `pthread_cancel`. The recipe defines
`CLTHREADS_NO_PTHREAD_CANCEL` only for OHOS, so `sepuku()` retains its original
`pthread_cancel(_ident)` behavior on supported POSIX targets. On OHOS it is an
explicit no-op fallback because the upstream class does not offer a safe
cross-thread cooperative-cancellation mechanism.

The package test is the executable validation layer. It links the packaged
shared library and checks mutex, event queue, message ownership, and text
formatting behavior.
