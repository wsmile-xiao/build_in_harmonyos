#!/usr/bin/env python3
"""Conan recipe -- pd-cxc 0.5.2 (Pure Data externals, classic Makefile template).

cxc is jdl@xdv.org's small library of Pure Data helpers for random number
generation, statistics and system inspection (2001-2013): 26 classes such as
``hex2dec``, ``cxc_split``, ``cxc_prepend``, ``cxc_counter``, ``ENV``,
``mean~``/``cxmean``/``cxstddev``/``cxavgdev``, the ``random1``/``random_fl``/
``random_icg``/``random_tw`` families and the ``ascseq``/``ascwave``/
``dist_normal``/``reson~``/``delta~``/``utime``/``proc`` utilities.  Pd
dlopen()s one shared object per class (``<class>.pd_linux``) the first time a
patch instantiates that object.

Build system: upstream's hand-written ``Makefile`` ("Pd library template
version 1.0.11") -- *not* pd-lib-builder, so there is no
``Makefile.pdlibbuilder`` to provide and the recipe drives the template's own
variables instead.  The upstream tarball is self-contained (it ships that
Makefile), which is why this recipe can use the official release archive; see
conandata.yml for the provenance argument.

OHOS notes (see notes.md)
--------------------------
* The template picks its platform from ``$(UNAME)``, i.e. the *build host*.
  On a Linux build host it takes the Linux branch, which is what a
  cross-compile to OHOS/aarch64 needs: ``EXTENSION = pd_linux`` (the name Pd
  looks for on non-Apple platforms) and ``ALL_LDFLAGS += -rdynamic -shared
  -fPIC``.  ``-rdynamic`` is the whole Pd "link": every Pd symbol the externals
  import is resolved out of the loading image at dlopen() time, so the objects
  link against nothing but libc and libm.
* ``CC`` is taken from the Conan profile conf (``tools.build:compiler_executables``),
  never from an undefined shell environment variable.
* ``PD_INCLUDE`` (the Makefile derives ``PD_INCLUDE = $(PD_PATH)/include/pd``
  and hard-codes ``PD_PATH = /usr`` on Linux) is redirected at the
  ``m_pd.h`` that puredata/0.54.1 ships.
* ``LIBS=-lm``: the template's link line is ``... $(ALL_LIBS)`` with
  ``ALL_LIBS = -lc`` only, but ``dist_normal.c``/``mean~.c``/``ascwave.c`` call
  ``sqrt``/``pow``/``log``/``fabs``/``sqrtf``.  On a glibc host those resolve
  from libc, on OHOS (musl) libm is a separate library, so ``-lm`` is required
  for the link to succeed there.  Passed as a make variable, no source change.
* ``STRIP=true``: the template's ``libdir_install`` rule calls
  ``$(STRIP) --strip-unneeded`` on every installed object, where ``STRIP`` is
  the host ``strip``.  A host strip cannot read the aarch64 ELF the cross
  compiler just produced ("Unable to recognise the format of the input file")
  and make then fails, so the step is turned into a no-op.  The objects keep
  their DWARF, which costs ~1.5 MB total and changes no behaviour.
* ``objectsdir=/lib/pd-externals``: the template installs to
  ``$(DESTDIR)$(objectsdir)/$(LIBRARY_NAME)`` with ``objectsdir`` defaulting to
  ``$(prefix)/lib/pd-externals`` and ``prefix=/usr/local``.  Overriding
  ``objectsdir`` puts the externals at ``<package>/lib/pd-externals/cxc``,
  which is where Pd looks for extra libraries.
* Pd has no linkable library.  ``puredata/0.54.1`` is an *application* package:
  it installs the ``pd`` executable and the data dir and **does** ship the API
  headers (``include/pd/m_pd.h``), but publishes no ``cpp_info.includedirs``
  because it is not a library.  The recipe resolves ``m_pd.h`` from the
  dependency's package folder and re-exports that directory in
  ``package_info()`` so consumers can compile Pd code against this package.
* One source patch, ``patches/0001-array-access-64bit-safe.patch``: upstream
  reads every array with ``garray_getfloatarray()``, which casts the array's
  ``t_word`` storage to ``t_float *``.  That cast is only valid where
  ``sizeof(t_word) == sizeof(t_float)``; on LP64 ``t_word`` is an 8-byte union
  while ``t_float`` is 4 bytes, so Pd logs
  "... it uses garray_getfloatarray while running 64-bit" and every external
  that strides through the buffer with ``t_float *`` reads interleaved garbage
  (measured: ``[cxmean buf]`` reported 1.25 for a buffer holding 1..8).  On top
  of that the ``no such table`` error path had no ``return`` and took the whole
  pd process down (rc=139).  The fix is Debian's own
  ``debian/patches/array64.patch`` (LP64-safe ``garray_getfloatwords()``), plus
  the missing returns; see notes.md for the evidence.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class PdCxcConan(ConanFile):
    name = "pd-cxc"
    version = "0.5.2"
    description = "cxc: Pure Data externals for randoms, averages and system tools"
    license = "GPL-2.0-or-later"
    homepage = "https://puredata.info/downloads/cxc"
    url = ""

    # The package installs Pd external shared objects
    # (lib/pd-externals/cxc/*.pd_linux) that Pd dlopen()s when a patch
    # instantiates the class.  Not command line programs, hence no commands.json.
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    # Pd always loads these objects with dlopen(), and the upstream Makefile
    # has no static mode (its link line is hard-coded to -shared).  The option
    # exists only to satisfy conan's 'library' package_type contract.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        # Carries patches/* into the exported recipe so `conan create` from a
        # clean checkout can apply them (R: the patch is part of the delivery).
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Pd itself supplies m_pd.h.  The headers are the only thing the 26
        # externals need -- they link against nothing, every Pd symbol is
        # resolved from Pd's own -rdynamic image at load time.
        self.requires("puredata/0.54.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is validated on Linux/OHOS, not {self.settings.os}"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                f"{self.ref} is a set of Pd externals and must be shared: Pd "
                "dlopen()s <class>.pd_linux, and the upstream Makefile has no "
                "static mode"
            )

    def _pd_include_dir(self):
        """Directory holding m_pd.h inside the puredata package.

        puredata/0.54.1 is an application package, so it publishes no
        cpp_info.includedirs; the headers are there all the same
        (<pkg>/include/pd/m_pd.h and <pkg>/include/m_pd.h).
        """
        dep = self.dependencies["puredata"]
        for candidate in (os.path.join(dep.package_folder, "include", "pd"),
                          os.path.join(dep.package_folder, "include")):
            if os.path.isfile(os.path.join(candidate, "m_pd.h")):
                return candidate
        raise ConanInvalidConfiguration(
            "puredata/0.54.1 package does not provide m_pd.h "
            f"(looked in {dep.package_folder}/include[/pd])"
        )

    def _compiler(self):
        # R33: never rely on undefined shell env -- read the compiler from the
        # Conan profile conf that CI and the local WSL profile both set.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        return executables.get("c") or "clang"

    def _make_args(self, destination=None):
        """make(1) overrides, shared by the build and install invocations.

        The Pd library template honours all of these on the command line:
          CC            the OHOS cross compiler (the template's Linux branch
                        leaves CC to the make builtin, i.e. `cc`)
          PD_INCLUDE    where m_pd.h lives (its default is
                        $(PD_PATH)/include/pd = /usr/include/pd)
          LIBS          extra link libraries; -lm for sqrt/pow/log/fabs
          STRIP         the template strips every installed object with the
                        *host* strip, which cannot read aarch64 ELFs
          objectsdir    install root, i.e.
                        $(DESTDIR)$(objectsdir)/$(LIBRARY_NAME)
          UNAME         forced to Linux: the OHOS worker's `uname -s`
                        reports `HarmonyOS`, which matches no upstream
                        branch, so EXTENSION/SHARED_EXTENSION and the
                        link flags would otherwise stay empty and every
                        class would be linked as a bare executable
                        (lld: undefined symbol: main / pd_new ...).
        """
        args = [
            'CC="%s"' % self._compiler(),
            'PD_INCLUDE="%s"' % self._pd_include_dir(),
            "LIBS=-lm",
            "STRIP=true",
            "objectsdir=/lib/pd-externals",
            # See docstring: OHOS uname -s = HarmonyOS, no upstream branch
            # matches; pin Linux so EXTENSION=pd_linux, -fPIC/-shared link
            # flags and SOURCES_linux (proc.c) are all taken.
            "UNAME=Linux",
        ]
        if destination is not None:
            args.append('DESTDIR="%s"' % destination)
        return " ".join(args)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Patches must be applied in source(), not in build(): the build runs on
        # a copy of the export tree, so patching there is a silent no-op (make
        # then compiles the unpatched sources while still logging "Apply
        # patch").  build() re-checks that the patch is really in effect.
        apply_conandata_patches(self)

    def _assert_patched(self):
        """Proof in the build log that the portability patch is in effect."""
        mean_c = os.path.join(self.source_folder, "mean~.c")
        with open(mean_c, encoding="utf-8", errors="replace") as handle:
            body = handle.read()
        if "CXC_ARRAY_GET" not in body or "garray_getfloatwords" not in body:
            raise ConanException(
                "patches/0001-array-access-64bit-safe.patch did not apply: "
                "%s still has the LP64-unsafe array accessors" % mean_c)
        self.output.info("patched| mean~.c reads arrays through "
                         "garray_getfloatwords (LP64-safe)")

    def _showsetup(self):
        """Parse the Makefile's own `showsetup` target.

        `make showsetup` echoes the fully expanded build configuration.  The
        `SOURCES:` line it prints is the authoritative object list *after* the
        Linux branch has appended `SOURCES_linux`, which is exactly the set of
        `.pd_linux` files a complete build must produce -- so the completeness
        check in build() cannot drift away from upstream.

        Note that the template also echoes `CPU := $(shell uname -m)`, i.e. the
        *build host* architecture (x86_64 on a cross build).  It is only
        recorded, never used: unlike pd-lib-builder this template puts no
        -march/-mcpu in the flags, so the OHOS clang's own aarch64 default
        target is what ends up in ALL_CFLAGS (see the echoed CFLAGS line).
        """
        log = os.path.join(self.build_folder, "make-showsetup.log")
        self.run(f'make {self._make_args()} showsetup > "{log}" 2>&1',
                 env="conanbuild", cwd=self.source_folder)
        with open(log, encoding="utf-8", errors="replace") as handle:
            out = handle.read()
        # The echoed configuration is the evidence for what the Makefile
        # actually resolved, so keep it in the build log too.
        for line in out.splitlines():
            self.output.info("showsetup| %s" % line)
        values = {}
        for line in out.splitlines():
            if ": " in line:
                key, _, value = line.partition(": ")
                if key.isupper() and key not in values:
                    values[key] = value.strip()
        if "SOURCES" not in values:
            raise ConanInvalidConfiguration(
                "could not read SOURCES from `make showsetup` in "
                + self.source_folder)
        return values

    def _class_names(self, values):
        names = []
        for token in values["SOURCES"].split():
            name, ext = os.path.splitext(os.path.basename(token))
            if ext == ".c":
                names.append(name)
        if not names:
            raise ConanInvalidConfiguration(
                "`make showsetup` reported no C sources: " + values["SOURCES"])
        return names

    def build(self):
        self._assert_patched()
        setup = self._showsetup()
        self.output.info("upstream Makefile configuration: LIBRARY_NAME=%s "
                         "LIBRARY_VERSION=%s UNAME=%s objectsdir=%s"
                         % (setup.get("LIBRARY_NAME"),
                            setup.get("LIBRARY_VERSION"),
                            setup.get("UNAME"),
                            setup.get("objectsdir")))
        # The package version and the version the Makefile reads out of
        # cxc-meta.pd must agree, otherwise `archives/p/pd-cxc/0.5.2` would ship
        # a 0.5.2 archive claiming to be something else.
        if setup.get("LIBRARY_VERSION") != self.version:
            raise ConanInvalidConfiguration(
                "upstream cxc-meta.pd declares version %r, recipe packages %r"
                % (setup.get("LIBRARY_VERSION"), self.version))

        # R9: one shared object per class; keep -j1 so the build log stays
        # deterministic and the resource usage flat on the CI worker.
        self.run(f"make {self._make_args()} -j1",
                 env="conanbuild", cwd=self.source_folder)
        built = sorted(f for f in os.listdir(self.source_folder)
                       if f.endswith(".pd_linux"))
        # Every class in the Makefile must have produced its object, otherwise
        # the package would silently ship a partial library.
        expected = sorted(self._class_names(setup))
        missing = [name for name in expected if name + ".pd_linux" not in built]
        if missing:
            raise ConanInvalidConfiguration(
                "externals not built: %s (built %d of %d)"
                % (", ".join(missing), len(built), len(expected)))
        self.output.info("built %d cxc externals" % len(built))

    def package(self):
        # installpath is $(DESTDIR)$(objectsdir)/$(LIBRARY_NAME), i.e.
        # <package>/lib/pd-externals/cxc -- the directory Pd searches for
        # extra libraries.  The same rule also drops cxc-meta.pd, the 26 help
        # patches, fader.pd, README.txt and LICENSE.txt beside the objects.
        self.run(f"make {self._make_args(self.package_folder)} install",
                 env="conanbuild", cwd=self.source_folder)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # puredata/0.54.1 is an application package: it ships include/pd/m_pd.h
        # but publishes no cpp_info.includedirs of its own, so a consumer of
        # pd-cxc could not compile Pd code without this package re-exporting
        # the headers.  They are copied *into this package* rather than pointing
        # cpp_info at the dependency's package folder: cpp_info directories are
        # package-relative by convention, and an absolute path into the cache
        # would break as soon as the package is moved, downloaded elsewhere or
        # relocated (local AI review 2026-10-12, P2).
        copy(self, "*.h", src=self._pd_include_dir(),
             dst=os.path.join(self.package_folder, "include", "pd"))

    def package_info(self):
        # The externals are dlopen()ed by path, never linked against, so there
        # is nothing in cpp_info.libs to export.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Package-relative: the Pd API headers copied in package() above.
        self.cpp_info.includedirs = ["include/pd"]
        # Upstream's sources are compiled with -DPD; consumers need the same
        # switch to see the Pd API declarations rather than the standalone ones.
        self.cpp_info.defines = ["PD"]
