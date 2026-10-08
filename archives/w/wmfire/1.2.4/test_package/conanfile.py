#!/usr/bin/env python3
"""Conan test_package for wmfire 1.2.4 — HarmonyOS end-to-end consumer case.

wmfire is an X11/GTK+2 dockapp: ``main()`` calls ``gdk_init_check()`` before it
parses any option, so the shipped binary cannot complete a run inside a headless
CI container.  It can still be *started* though, and that is what this consumer
case uses.  Instead of asserting on file magic bytes it builds a real program
(``src/hc_consumer.c``) against the package's dependencies and walks the runtime
contract, end to end:

    HC-1  elf-contract          the installed ``bin/wmfire`` is a signed OHOS
                                ELF64/AArch64 PIE with a non-empty DT_NEEDED
    HC-2  loader-closure        exec the installed ``bin/wmfire`` with no
                                DISPLAY: the OHOS loader must resolve the whole
                                DT_NEEDED closure and ``main()`` must actually
                                be reached (its "GDK init failed" diagnostic +
                                exit status 255).  This is where a dependency
                                left as an ``libx.so.1 -> libx.so.1.2.3``
                                symlink blows up, because the musl loader does
                                not follow symlinks for DT_NEEDED.
    HC-3  x11-geometry-parse    real call into libX11 — the same
                                ``XParseGeometry()`` wmfire's ``-g`` option uses
    HC-4  cpu-sample            real call into libgtop — the same
                                ``glibtop_get_cpu()`` data path wmfire samples
                                on every refresh to draw the flame (wmfire
                                never calls ``glibtop_init()`` itself, so
                                neither does this case, which also reads the
                                ``glibtop_global_server->ncpu`` the program
                                uses).  The call runs in a forked child, and
                                the case is written as an implication
                                cross-checked against the platform: the
                                consumer reads ``/proc/stat`` itself, in its
                                own security domain, and requires the sampler
                                to agree with it — real advancing jiffies
                                that land inside the window that very file
                                defines, an explicit "/proc/stat ...
                                Permission denied" refusal when HarmonyOS
                                hides it (``hidepid=invisible,hmmac=genfs``),
                                and zeroed counters when the kernel serves
                                the file with no CPU accounting at all (the
                                container quirk that also makes CMake report
                                "Problem parsing /proc/meminfo").  Invented
                                counters always fail, and libgtop's own
                                diagnostics from the child are echoed into
                                the report on every outcome.

Running the consumer needs three OHOS-specific remediations:

* ``test()`` stages the conan dependency closure with ``cp -L`` before
  starting the consumer.  OHOS musl resolves DT_NEEDED by opening the plain
  name and does not follow symlinks, so a dependency shipped as
  ``libX.so.1 -> libX.so.1.2.3`` is invisible to the loader and wmfire dies
  with ``Error loading shared library libXrender.so.1`` (E505).  The same
  ``cp -L`` staging is what the merged wmgtemp consumer test does.
* ``test()`` also seeds the platform C++ runtime into the staged closure.
  The GTK+2 stack ships C++ shared objects (``libharfbuzz.so.0``,
  ``libpangocairo-1.0.so.0``, …) and the packaged ``bin/wmfire`` itself
  carries a direct ``DT_NEEDED`` on ``libc++_shared.so``, which is *not* a
  conan package but part of the SDK.  The conan-run library path contains no
  system directory on OHOS, so without this the loader reports
  ``Error loading shared library libc++_shared.so`` while wmfire is dying
  with ``exit=127``.  The merged avahi-ui consumer test records the same
  finding and remedies it with ``/system/lib64``; the merged atkmm consumer
  test uses the SDK's ``llvm/lib/aarch64-linux-ohos`` directory.  See
  ``_cxx_runtime_dir()`` for the order used here.
* The staging sweep copies with ``cp -n`` (first match wins) instead of
  plain ``cp``, because a flat stage otherwise destroys the
  ``LD_LIBRARY_PATH`` search order: VirtualRunEnv appends the *ambient*
  ``LD_LIBRARY_PATH`` after the conan libdirs, and on this host that tail
  contains ``/data/storage/el1/bundle/libs/arm64`` - an app-bundle C++
  runtime exposing the same ``libc++_shared.so`` soname (7519624 B) which the
  loader refuses to map for a plain user-directory executable.  Copied last,
  it clobbered the toolchain's loadable copy and HC-2 failed with a bogus
  "Error loading shared library libc++_shared.so".
* ``generate()`` hands libgtop's static archive to CMake by path, because
  ``find_package(libgtop CONFIG)`` cannot work: libgtop's ``cpp_info.libs``
  declares ``intl``, a file that ships in the *glib* package, and CMakeDeps
  validates every lib name against the declaring package's own libdir
  (E508).

``hc_consumer.c`` never calls ``dlopen()``: HarmonyOS CI workers refuse
dlopen/LD_PRELOAD of user-directory shared objects while exec-time DT_NEEDED
loading works (knowledge base entry E502), so every case goes through the
accepted exec-time path.

Upstream ships **no** test suite (``Makefile.am`` declares no ``TESTS``, so
``make check`` is a successful no-op — see ``test_package/MANIFEST.yml``), which
makes this consumer case the package's only executable verification.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class WmfireTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # wmfire is package_type="application", so a consumer of it does not
        # inherit its dependencies' headers/libs (Conan filters cpp_info for
        # application packages).  This consumer exercises the two libraries
        # wmfire itself calls — libgtop for the CPU counters, libX11 for the
        # -g geometry option — so declare them here directly as well.
        self.requires("libgtop/2.41.3", transitive_headers=True, transitive_libs=True)
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)

        # libgtop is consumed by path, not through find_package(libgtop CONFIG):
        # its cpp_info.libs is ["gtop-2.0", "intl"] while libintl.so ships in
        # the glib package, so CMakeDeps' conan_package_library_targets() -
        # which only searches the declaring package's own libdir - aborts the
        # configure with "Library 'intl' not found in package" (E508).
        gtop = self.dependencies["libgtop"]
        libdir = gtop.cpp_info.libdirs[0]
        archives = sorted(
            name for name in os.listdir(libdir)
            if name.startswith("lib") and name.endswith(".a")
        )
        if not archives:
            raise ConanException(f"libgtop ships no static archive in {libdir}")
        tc.variables["HC_LIBGTOP_ARCHIVE"] = os.path.join(libdir, archives[0])
        tc.variables["HC_LIBGTOP_INCLUDE_DIRS"] = ";".join(
            gtop.cpp_info.includedirs
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_consumer(self):
        candidates = [
            os.path.join(self.build_folder, "hc_consumer"),
            os.path.join(self.build_folder, str(self.settings.build_type),
                         "hc_consumer"),
            os.path.join(self.build_folder, "build",
                         str(self.settings.build_type), "hc_consumer"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        return None

    def _cxx_runtime_dir(self):
        """Directory holding the platform ``libc++_shared.so``, or ``None``.

        wmfire and several of its GTK+2 dependencies are C++ shared objects,
        so the OHOS loader needs ``libc++_shared.so`` at exec time.  That
        runtime is not a conan package and the VirtualRunEnv library path
        contains no system directory, hence it has to be added explicitly.

        Prefer the SDK copy the toolchain actually linked against (its
        ``aarch64-linux-ohos`` sub-directory ships ``libc++_shared.so`` as a
        regular file, so no E505 dereferencing is involved); fall back to the
        platform directory, which is what the merged avahi-ui consumer test
        uses.  The SDK version directory is globbed rather than hard-coded so
        a toolchain bump does not silently break the test.
        """
        candidates = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/"
            "aarch64-linux-ohos"
        ))
        candidates.append("/system/lib64")
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "libc++_shared.so")):
                return candidate
        return None

    def test(self):
        wmfire = os.path.join(
            self.dependencies["wmfire"].cpp_info.bindirs[0], "wmfire"
        )
        assert os.path.isfile(wmfire), f"wmfire binary not installed at {wmfire}"

        exe = self._find_consumer()
        assert exe, f"the hc_consumer program was not built in {self.build_folder}"

        self.output.info(f"HC consumer: {exe}")
        self.output.info(f"HC subject : {wmfire}")

        # OHOS: /system/bin/sh (mksh) cannot execve an ELF binary from the
        # user directory; wrap in bash.  env="conanrun" also puts every
        # dependency's libdir on LD_LIBRARY_PATH, which is what HC-2 needs in
        # order to load the shipped binary's whole DT_NEEDED closure.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # The C++ runtime of the GTK+2 stack.  It is *seeded* into the stage
        # rather than swept in as a directory: the directory is kept on
        # LD_LIBRARY_PATH as a fallback for any other toolchain runtime the
        # closure may need, but sweeping /system/lib64 itself would copy
        # ~2500 unrelated shared objects (including a second libc.so).
        cxx_dir = self._cxx_runtime_dir()
        if cxx_dir:
            self.output.info(f"HC cxx runtime: {cxx_dir}/libc++_shared.so")
            cxx_part = f"{cxx_dir}:"
        else:
            self.output.warning(
                "libc++_shared.so not found in the SDK or /system/lib64; the "
                "loader closure case may fail"
            )
            cxx_part = ""

        # E505: OHOS musl opens DT_NEEDED by plain name and does not follow
        # symlinks, so a dependency shipped as `libX.so.1 -> libX.so.1.2.3`
        # is invisible to it and wmfire dies with
        # "Error loading shared library libXrender.so.1".  Stage the conan
        # closure dereferenced (cp -L) - the same remediation the merged
        # wmgtemp consumer test uses.
        #
        # The sweep uses `cp -n` (first match wins) because a flat stage
        # destroys LD_LIBRARY_PATH precedence: VirtualRunEnv appends the
        # ambient LD_LIBRARY_PATH after the conan libdirs, and this host's
        # tail contains /data/storage/el1/bundle/libs/arm64, which exposes an
        # app-bundle libc++_shared.so (7519624 B) under the same soname that
        # the loader refuses to map for a user-directory executable.  Copied
        # last, it overwrote the toolchain's loadable copy and HC-2 failed
        # with a bogus "Error loading shared library libc++_shared.so".
        # Seeding the toolchain's runtime before the sweep keeps it
        # authoritative regardless of what the ambient path contains.
        seed = ""
        if cxx_dir:
            seed = f'cp -Lf "{cxx_dir}/libc++_shared.so" "$stage/" 2>/dev/null; '
        stage = (
            'stage="${TMPDIR:-$HOME/tmp}/wmfire-hc-libs-$$"; '
            'mkdir -p "$stage"; '
            + seed +
            'echo "$LD_LIBRARY_PATH" | tr ":" "\\n" | while read -r d; do '
            '[ -n "$d" ] && [ -d "$d" ] && cp -nL "$d"/*.so* "$stage/" '
            '2>/dev/null; done; '
            f'export LD_LIBRARY_PATH="$stage:{cxx_part}$LD_LIBRARY_PATH"; '
            f'exec "{exe}" "{wmfire}"'
        )
        self.run(f'"{bash}" -c \'{stage}\'', env="conanrun")
