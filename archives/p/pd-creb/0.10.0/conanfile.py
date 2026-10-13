#!/usr/bin/env python3
"""Conan recipe — pd-creb 0.10.0 (Pure Data extension library) for HarmonyOS PC.

creb (Tom Schouten) is a collection of Pure Data abstractions and externals.
Upstream builds through ``Makefile.pdlibbuilder`` (a vendored pd-lib-builder
snapshot) with ``make-lib-executable=no``, i.e. one loadable
``<object>.pd_linux`` per Pd class plus the abstraction/help ``.pd`` files.

OHOS adaptation notes
---------------------
* **Toolchain is passed on the make command line, never inherited (R33).**
  ``ohos-aarch64-wsl`` exposes the OHOS toolchain only through
  ``tools.build:compiler_executables``; the profile has no ``[buildenv]`` and
  ``env="conanbuild"`` is *empty* during ``conan create`` (the aggregated
  ``conanbuild.sh`` is only materialised by ``conan install``).  A bare
  ``make`` would therefore silently fall back to the host ``/usr/bin/cc`` and
  package x86-64 objects as if they were OHOS ones.  Every tool path is read
  from ``self.conf`` and passed explicitly; a missing toolchain conf is a hard
  error rather than a silent host fallback.
* **No ``PLATFORM=``** — pd-lib-builder would rewrite ``CC`` to
  ``$(PLATFORM)-gcc``, which does not exist for the OHOS triplet.
* **``target.triplet`` is supplied rather than probed.**  ``Makefile.pdlibbuilder:473``
  shells out to ``$(CC) -dumpmachine`` and aborts at line 759 if the answer comes
  back empty; that probe is the only ``$(shell)`` in the file whose failure is
  fatal, so it also reports the failure modes it cannot distinguish from "no
  triplet".  On the CI worker (build #70634/#70694/#70765) the worker logged
  ``make: sed: Resource temporarily unavailable``,
  ``make: /data/service/hnp/bin/clang: ...`` and ``make: uname: ...`` —
  EAGAIN, i.e. the worker could not spawn *any* of the three probes, and the
  makefile blamed ``clang`` for a compiler that was never run.  The triplet is
  derivable from ``settings``, so it is passed on the command line: the fatal
  ``$(error)`` at 759 then has a value to test and the build no longer dies
  there.

  This does **not** remove the probe.  GNU Make 4.3 still expands the ``:=``
  right-hand side at line 473 even when the variable comes from the command
  line, which is why build #71013 still logs a ``clang`` EAGAIN line even though
  the recipe now passes ``target.triplet``.  Measured with a ``CC`` wrapper that
  logs its argv: ``-dumpmachine`` is invoked both with and without
  ``target.triplet=`` on the command line, while ``target.triplet`` itself keeps
  the command-line value (that is what gets the build past line 759).
  Suppressing the fork would mean patching the vendored makefile to guard the
  assignment with ``ifeq ($(origin target.triplet),undefined)``.  That saves one
  fork out of the ~50 the build needs, so it is deliberately not done — see
  ``notes.md`` for the fork-exhaustion rounds it would not have helped with.
* **``cxx.ldlibs``** — pd-lib-builder's Linux branch hardcodes ``-lstdc++``.
  OHOS ships libc++ only, so every C++ external fails to link until that
  variable is overridden on the command line.  The C++ runtime itself is
  attached by the toolchain driver, so only the explicit ``-lstdc++`` goes.
* **``PDINCLUDEDIR``** — the only pd-lib-builder variable that must be
  pointed at the dependency; taken read-only from the ``puredata`` package
  folder.  ``PDDIR`` is deliberately *not* set: pd-lib-builder re-derives
  ``PDINCLUDEDIR`` as ``$(PDDIR)/src`` whenever ``PDDIR`` is defined.
* **No patching of the vendored ``pd-lib-builder``** — every fix is either a
  command-line variable or one of the six upstream-authoring (Debian)
  portability patches registered in ``conandata.yml``.

Runtime scope: the payload is a set of ``dlopen``-able Pd objects.  Pd
resolves the ``<class>_setup`` entry points and the Pd C API from the hosting
``pd`` process, so nothing links against ``puredata`` and the objects are
loadable by an OHOS ``pd`` built from the same dependency.

The payload also carries the **upstream test assets** (``unittests/`` with its
35 unit-test patch graphs and reference recordings, plus Pure Data's
``testtools`` measuring library), so that the upstream tests really execute
against the packaged objects instead of being declared "not automatable".
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PdCrebConan(ConanFile):
    name = "pd-creb"
    version = "0.10.0"
    description = "creb — abstractions and externals library for Pure Data"
    license = "GPL-2.0-or-later"
    homepage = "https://zwizwa.be/creb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("puredata", "audio", "dsp", "pd-external")

    # code-style.md suggests "library" for libraries.  This payload is 46
    # ET_DYN objects that Pd dlopen()s, with no linkable archive anywhere, so
    # "shared-library" is the closest honest description; see notes.md.
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    # Pure Data's own `testtools` library, carried in the recipe so the upstream
    # unit tests stay runnable.  The creb unittest patches instantiate the
    # measuring device by the *relative* name `testtools/unit-test-frame~`, so
    # a package that ships `unittests/` without `testtools/` cannot run a single
    # one of them.  Provenance and per-file sha256: see notes.md.
    exports_sources = "testtools/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pd-creb targets POSIX/Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Headers only.  A Pd object resolves the whole Pd C API from the
        # hosting `pd` process at dlopen() time, so no library of puredata is
        # linked into the payload.
        self.requires("puredata/0.54.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patches must be applied here, not in build(): build() compiles out
        # of a *copy* of the export tree, so patching there is a silent no-op
        # (the build then reverts to the unpatched sources while still logging
        # "Apply patch").
        apply_conandata_patches(self)

    def _compiler(self):
        """Toolchain paths straight from the profile conf (R33)."""
        executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = executables.get("c")
        cxx = executables.get("cpp")
        if not cc or not cxx:
            raise ConanException(
                "pd-creb: the profile must define tools.build:compiler_executables "
                "with both 'c' and 'cpp'. Without it make would fall back to the "
                "host /usr/bin/cc and package non-OHOS objects, so this is fatal "
                "on purpose instead of a silent cross-build of the wrong target."
            )
        missing = [p for p in (cc, cxx) if not os.path.isfile(p)]
        if missing:
            raise ConanException(
                f"pd-creb: tools.build:compiler_executables points at "
                f"non-existent tool(s) {missing}; refusing to build with a "
                "possibly wrong toolchain."
            )
        return cc, cxx

    def _pd_include_dir(self):
        """Directory holding m_pd.h inside the puredata dependency."""
        pd_prefix = self.dependencies["puredata"].package_folder
        candidates = (
            os.path.join(pd_prefix, "include", "pd"),
            os.path.join(pd_prefix, "include"),
        )
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "m_pd.h")):
                return candidate
        raise ConanException(
            f"pd-creb: m_pd.h not found under {pd_prefix}/include — the "
            "puredata dependency does not expose the Pd headers."
        )

    # ``settings.arch`` -> the CPU word pd-lib-builder expects as the first word
    # of ``target.triplet`` (Makefile.pdlibbuilder:504-510 lists the CPU names it
    # understands and takes ``$(firstword $(target.triplet))``).  An unknown value
    # is fatal rather than guessed, for the same reason ``_compiler()`` refuses to
    # fall back to a host toolchain.
    _TRIPLET_ARCH = {
        "armv8": "aarch64",
        "aarch64": "aarch64",
        "armv8-a": "aarch64",
        "armv7": "armv7",
        "armv7-a": "armv7",
        "armv7s": "armv7",
        "x86_64": "x86_64",
        "x86": "i686",
    }

    def _target_triplet(self):
        """The GNU triplet pd-lib-builder would have *probed* for.

        ``Makefile.pdlibbuilder:473`` runs ``target.triplet :=
        $(subst -, ,$(shell $(CC) -dumpmachine))`` and then aborts the whole
        build at line 759-763 when the result is empty -- the only ``$(shell)``
        in the file whose failure is fatal.  Probing is unnecessary here: the
        triplet is a property of the target, which conan already knows from
        ``settings``, and pd-lib-builder itself documents that supplying the
        triplet is how a cross build declares its platform.  Passing it on the
        make command line overrides the ``:=`` assignment above, so the probe is
        never evaluated and the platform selection becomes deterministic.

        The ``linux`` word is what
        ``ifneq ($(filter linux gnu% kfreebsd, $(target.triplet)),)`` (line 482)
        matches to pick the Linux branch, and that word is present even for OHOS:
        its clang reports ``aarch64-unknown-linux-ohos``, i.e. the triplet
        spelled out below, byte for byte, minus the ``-`` -> space substitution
        the makefile would have done.
        """
        arch = self._TRIPLET_ARCH.get(str(self.settings.arch))
        if arch is None:
            raise ConanInvalidConfiguration(
                f"pd-creb: no pd-lib-builder triplet known for arch "
                f"{self.settings.arch}; refusing to guess a target platform."
            )
        return f"{arch} unknown linux ohos"

    def _make_vars(self):
        cc, cxx = self._compiler()
        return " ".join([
            f'CC="{cc}"',
            f'CXX="{cxx}"',
            f'target.triplet="{self._target_triplet()}"',
            f'PDINCLUDEDIR="{self._pd_include_dir()}"',
            # OHOS has libc++ only; drop pd-lib-builder's hardcoded -lstdc++.
            'cxx.ldlibs="-lc -lm"',
        ])

    def _jobs(self):
        # pd-lib-builder has no job control of its own.  A serial make follows
        # the repository convention and keeps peak memory predictable on the
        # CI worker; the 46 Pd objects build in well under two minutes.
        return max(1, int(self.conf.get("tools.build:jobs", default=1)))

    def build(self):
        make_vars = self._make_vars()
        self.run(
            f"make -j{self._jobs()} {make_vars}",
            cwd=self.source_folder,
        )

    def package(self):
        # pd-lib-builder installs to $(DESTDIR)$(PDLIBDIR)/$(lib.name); the
        # leading slash on PDLIBDIR keeps the join absolute under DESTDIR.
        make_vars = self._make_vars()
        self.run(
            f"make install DESTDIR=\"{self.package_folder}\" PDLIBDIR=/lib/pd-externals "
            f"{make_vars}",
            cwd=self.source_folder,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # The upstream test assets travel with the payload, in the layout the
        # Pure Data community uses for per-library unit tests (see the pd-dev
        # thread quoted in notes.md: "a copy of the test abstractions should be
        # in every lib's unittest/ dir"):
        #   <pd-externals>/creb/unittests/     35 upstream *-unittest.pd graphs
        #                                      + their 35 reference .wav
        #   <pd-externals>/creb/testtools/     unit-test-frame{,~} + meta + license
        # `copy()`'s first argument is a glob relative to `src`; "*" is required
        # to take every file, a bare name would match by substring.
        creb_payload = os.path.join(self.package_folder, "lib", "pd-externals", "creb")
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "unittests"),
            dst=os.path.join(creb_payload, "unittests"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.export_sources_folder, "testtools"),
            dst=os.path.join(creb_payload, "testtools"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.txt",
            src=os.path.join(self.export_sources_folder, "testtools"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # The payload is a directory of dlopen()-able Pd objects plus their
        # abstractions, not a linkable library: there is no libcreb.so and no
        # `creb` archive, so declaring cpp_info.libs would hand consumers a
        # -lcreb that can never resolve.  Consumers get the payload directory
        # and add it to Pd's search path instead.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("pd_externals_dir", "lib/pd-externals/creb")
        # Where the upstream unit-test graphs and their reference .wav live,
        # relative to the package folder, for consumers that want to re-run
        # them against a real Pd.
        self.cpp_info.set_property(
            "pd_unittests_dir", "lib/pd-externals/creb/unittests")
