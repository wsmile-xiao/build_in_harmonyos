# clthreads 2.4.2 adaptation notes

Upstream 2.4.2 restructures the tarball: all sources now live under
`source/`, so the recipe builds with `make -C source`. The upstream
Makefile already honours `$(CXX)` for the shared-library link and
gained `DESTDIR` plus overridable `PREFIX`/`INCDIR`/`LIBDIR`. The
portability patch drops `-march=native` (invalid for the OHOS cross
compiler and non-reproducible), wires the
`CLTHREADS_NO_PTHREAD_CANCEL` make variable into `CPPFLAGS`, and adds
the `make check` target that builds and runs the source-tree API test.

Packaging is done by the recipe instead of `make install`, for two
device-verified reasons. First, the OHOS device build environment
resolves `install` to a non-executable file under
`~/usr/local/bin` (mode 0770, foreign owner) that shadows `/bin/install`,
which makes every upstream `install` recipe line fail with
"Permission denied". Second, the device home filesystem rejects
`ln -sf`, so the upstream symlink chain cannot be created there. The
recipe therefore copies `clthreads.h` and the built shared object with
Conan's `copy()` and stages the soname chain
(`libclthreads.so.2.4.2`, `libclthreads.so.2`, `libclthreads.so`) as
real file copies, which is functionally equivalent for linking and
runtime loading on every supported platform.

License note: 2.4.2 relicensed from LGPL-2.1 to GPL-2.0-or-later in the
source file headers. The shipped COPYING file still contains the old
LGPL-2.1 text (upstream packaging oversight); the per-file headers are
authoritative for the recipe license field. The dmeliza GitHub mirror
used for 2.4.0 has no 2.4.2 tag, so the recipe pulls the official
kokkinizita tarball instead.

OpenHarmony does not provide `pthread_cancel`. The recipe defines
`CLTHREADS_NO_PTHREAD_CANCEL` only for OHOS — both when building and,
through `package_info().cpp_info.defines`, for every Conan consumer —
so `sepuku()` retains its original `pthread_cancel(_ident)` behavior
on supported POSIX targets. On OHOS it is an explicit no-op fallback
because the upstream class does not offer a safe cross-thread
cooperative-cancellation mechanism; the patch deliberately uses only
the recipe-provided macro (no platform detection macros in patches).

API change versus 2.4.0: `~ITC_ip1q()` and `~ITC_ctrl()` are now
virtual; no other behavioural changes affect consumers. The package
test is the executable validation layer. It links the packaged shared
library and checks mutex, event queue, message ownership, and text
formatting behavior. A second consumer use case
(`test_clthreads_threads.cpp`) exercises the pattern the library
exists for: an `H_thread` worker (real detached pthread via
`thr_start`) receives `Textmsg` commands on its `ITC_ip1q` queue,
replies over the main thread's queue, and terminates by protocol
(`TERM` -> `BYE`) since `P_thread` provides no join.
