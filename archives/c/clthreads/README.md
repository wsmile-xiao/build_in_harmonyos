# clthreads

`clthreads` is a small C++ threading and inter-thread communication library.

## OpenHarmony adaptation

- Source: https://github.com/dmeliza/clthreads
- Build system: Makefile
- Runtime dependency: pthreads provided by the platform C library
- The adaptation adds `make check` to exercise mutex, event-queue, message, and
  text-formatting APIs in the source tree; the Conan consumer test repeats the
  same checks against the packaged shared library.
