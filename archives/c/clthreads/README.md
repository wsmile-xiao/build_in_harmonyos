# clthreads

`clthreads` is a small C++ threading and inter-thread communication library.

## OpenHarmony adaptation

- 2.4.0 source: https://github.com/dmeliza/clthreads (GitHub mirror, LGPL-2.1-or-later)
- 2.4.2 source: https://kokkinizita.linuxaudio.org/linuxaudio/downloads/ (official; the
  mirror has no 2.4.2 tag, and 2.4.2 relicensed to GPL-2.0-or-later in the source
  headers while the bundled COPYING still carries stale LGPL-2.1 text)
- Build system: Makefile (2.4.2 builds from the `source/` subdirectory)
- Runtime dependency: pthreads provided by the platform C library
- The adaptation adds `make check` to exercise mutex, event-queue, message, and
  text-formatting APIs in the source tree; the Conan consumer test repeats the
  same checks against the packaged shared library.
