#!/usr/bin/env python3
"""Conan recipe — pd-ekext 0.3.1 (Pure Data externals, built by pd-lib-builder).

ekext is Ed Kelly's collection of Pure Data externals for music information
retrieval and polyphony control (2005-2023): 43 C classes such as ``bmt~``
(beat mark tracker), ``ihisto`` (envelope histogram), ``phasorbars~``,
``markovChains``, ``maskxor``, ``similar~``/``simile``-style similarity and
onset helpers.  Pd dlopen()s one shared object per class
(``<class>.pd_linux``) the first time a patch instantiates that object.

Build system: upstream ``Makefile`` + the ``pd-lib-builder`` helper
(``Makefile.pdlibbuilder``, version 0.7.0), which upstream references as a git
submodule.  Debian's orig tarball substitutes the released pd-lib-builder tree,
which is why this recipe takes its source from the Debian pool (see
conandata.yml for the full provenance argument and the upstream-tag
cross-check).

OHOS notes (see notes.md)
--------------------------
* pd-lib-builder picks its platform from ``$(CC) -dumpmachine``.  With the OHOS
  clang that is ``aarch64-unknown-linux-ohos``, whose ``linux`` token selects
  the Linux branch: ``extension = pd_linux`` (the name Pd looks for on
  non-Apple platforms) and ``-fPIC -shared -rdynamic``.  ``system=Linux`` is
  still passed explicitly so the choice never depends on the build host.
* ``arch.c.flags`` is derived from ``target.arch``/``uname -m``.  The recipe
  clears it so the compile is driven purely by the OHOS clang's own aarch64
  default instead of pd-lib-builder's untested ``-mcpu=cortex-a53`` guess.
* Pd has no linkable library: it is ``-rdynamic``, and a plugin's Pd symbols
  are resolved out of the running Pd process image at dlopen() time.  The
  externals therefore link against nothing but ``-lc -lm``.
* ``puredata/0.54.1`` is an *application* package: it installs the ``pd``
  executable and the data dir and **does** ship the API headers
  (``include/pd/m_pd.h``), but publishes no ``cpp_info.includedirs`` because it
  is not a library.  The recipe resolves ``m_pd.h`` from the dependency's
  package folder and re-exports that directory in ``package_info()`` so
  consumers can compile Pd code against this package.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PdEkextConan(ConanFile):
    name = "pd-ekext"
    version = "0.3.1"
    description = "ekext: Pure Data externals for music information retrieval and polyphony control"
    license = "BSD-3-Clause"
    homepage = "https://puredata.info/downloads/ekext"
    url = ""

    # The package installs Pd external shared objects
    # (lib/pd-externals/ekext/*.pd_linux) that Pd dlopen()s when a patch
    # instantiates the class.  Not command line programs, hence no commands.json.
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    # Pd always loads these objects with dlopen(), and pd-lib-builder has no
    # static mode (its link line is hard-coded to `-shared`).  The option exists
    # only to satisfy conan's 'library' package_type contract.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Pd itself supplies m_pd.h.  The headers are the only thing the 43
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
                "dlopen()s <class>.pd_linux, and pd-lib-builder has no static "
                "mode"
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

        pd-lib-builder honours all of these on the command line:
          system             force the Linux branch (pd_linux extension)
          CC                 the OHOS cross compiler; pd-lib-builder derives
                             `system` from `$(CC) -dumpmachine`
          arch.c.flags=      cleared: pd-lib-builder's aarch64 guess
                             (-mcpu=cortex-a53, marked "not tested yet" upstream)
                             is replaced by the OHOS clang's own default target
          PDINCLUDEDIR       where m_pd.h lives (its default probes
                             /usr/include/pd, which does not exist here)
          PDLIBDIR           install root, relative to DESTDIR.  It is string
                             concatenation, not a path join:
                             installpath = $(DESTDIR)$(PDLIBDIR)/$(lib.name),
                             so it must be written with a leading slash.
        """
        args = [
            "system=Linux",
            'CC="%s"' % self._compiler(),
            "arch.c.flags=",
            'PDINCLUDEDIR="%s"' % self._pd_include_dir(),
            "PDLIBDIR=/lib/pd-externals",
        ]
        if destination is not None:
            args.append('DESTDIR="%s"' % destination)
        return " ".join(args)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R9: one shared object per class; keep -j1 so the build log stays
        # deterministic and the resource usage flat on the CI worker.
        self.run(f"make {self._make_args()} -j1",
                 env="conanbuild", cwd=self.source_folder)
        built = sorted(f for f in os.listdir(self.source_folder)
                       if f.endswith(".pd_linux"))
        # Every class in the Makefile must have produced its object, otherwise
        # the package would silently ship a partial library.
        expected = sorted(self._class_names())
        missing = [name for name in expected if name + ".pd_linux" not in built]
        if missing:
            raise ConanInvalidConfiguration(
                "externals not built: %s (built %d of %d)"
                % (", ".join(missing), len(built), len(expected)))
        self.output.info("built %d ekext externals" % len(built))

    def _class_names(self):
        """Class names from the Makefile's `class.sources` list.

        pd-lib-builder derives one shared object per entry
        (`classes.executables := $(addsuffix .$(extension), $(classes))`), so
        this is the authoritative list of what a complete build produces.  It is
        read from the Makefile rather than hardcoded so the completeness check
        in build() cannot drift away from upstream.
        """
        makefile = os.path.join(self.source_folder, "Makefile")
        names, collecting = [], False
        with open(makefile, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("class.sources"):
                    collecting = True
                    continue
                if collecting:
                    if stripped.startswith("$(empty)"):
                        break
                    token = stripped.rstrip("\\").strip()
                    if token:
                        names.append(os.path.splitext(os.path.basename(token))[0])
        if not names:
            raise ConanInvalidConfiguration(
                "could not read class.sources from " + makefile)
        return names

    def package(self):
        # installpath is $(DESTDIR)$(PDLIBDIR)/$(lib.name), i.e.
        # <package>/lib/pd-externals/ekext -- the directory Pd searches for
        # extra libraries.
        self.run(f"make install {self._make_args(self.package_folder)}",
                 env="conanbuild", cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # The externals are dlopen()ed by path, never linked against, so there
        # is nothing in cpp_info.libs to export.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.defines = ["PD"]
        # Re-export the Pd API headers resolved above: puredata/0.54.1 is an
        # application and publishes no include dirs of its own, so without this
        # a consumer of pd-ekext could not compile against it.
        self.cpp_info.includedirs = [self._pd_include_dir()]