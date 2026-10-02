#!/usr/bin/env python3
"""Conan recipe — pd-libdir 1.11 (upstream pd-lib-builder Makefile).

pd-libdir is the `libdir` loader library for Pure Data (Pd): a shared object
that Pd dlopen()s as `libdir.pd_linux` so that any directory containing a
`<lib>/<lib>-meta.pd` marker becomes an importable Pd library.  It is *not* a
linkable library and has no C API of its own — the whole contract is the
exported `setup()` entry point, driven by Pd.

Build system: the upstream hand-written `Makefile` + `Makefile.pdlibbuilder`
(the pd-lib-builder helper).  Neither file is patched for the platform; the
recipe passes the six make overrides they need on the command line (see
`_make_args()` and notes.md).

OHOS notes (see notes.md):
- pd-lib-builder picks its platform from `uname`, so on the Linux CI worker it
  takes the Linux branch and names the artifact `libdir.pd_linux` -- the name
  Pd looks for on non-Apple platforms.  No patching required.
- pd-lib-builder also derives `arch.c.flags` from `uname -m`, which on the
  x86_64 worker injects `-march=core2 -msse...`.  Those are rejected by the
  aarch64 OHOS clang, so the recipe clears `arch.c.flags` on the make command
  line.
- Pd headers are not a standalone conan package: `puredata/0.54.1` ships
  `include/pd/m_pd.h` but declares itself an application and therefore exports
  no `includedirs`.  The recipe resolves that header directory from the
  dependency's package folder and re-exports it in `package_info()` so that
  consumers (and test_package) can compile Pd code against this package.
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


class PdLibdirConan(ConanFile):
    name = "pd-libdir"
    version = "1.11"
    description = "libdir loader library for Pure Data (Pd): makes any directory with a <lib>-meta.pd an importable Pd library"
    license = "BSD-3-Clause"
    homepage = "https://puredata.info/docs/developer/Libdir"
    url = "https://tracker.debian.org/pkg/pd-libdir"

    # A Pd loader plugin: an ELF shared object that Pd dlopen()s.  Not a CLI
    # tool (no main(), no bin/ install), hence "library" and no commands.json
    # — see notes.md.
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # Pd loads this library with dlopen(), so it is always a shared object;
    # pd-lib-builder has no static mode. The option exists only to satisfy
    # conan's 'library' package_type contract and is rejected when False.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    no_copy_source = False

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pd itself supplies m_pd.h / s_stuff.h / g_canvas.h.  The headers are
        # the only thing libdir.c needs — the plugin links against nothing,
        # every Pd symbol is resolved from Pd's own -rdynamic image at load
        # time.
        self.requires("puredata/0.54.1")

    # R32: only Linux/OHOS are supported build hosts for this recipe.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                f"{self.ref} is a Pd loader plugin and must be shared: Pd "
                "dlopen()s libdir.pd_linux, and pd-lib-builder has no static "
                "mode"
            )

    def _pd_include_dir(self):
        """Directory holding m_pd.h inside the puredata package.

        puredata/0.54.1 is declared as an application package, so it publishes
        no cpp_info.includedirs; the headers are there all the same
        (<pkg>/include/m_pd.h and <pkg>/include/pd/m_pd.h).
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
        # R33: never rely on undefined shell env — read the compiler from the
        # Conan profile conf that CI and W3 both set.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        return executables.get("c") or "clang"

    def _make_args(self, destination=None):
        """make(1) overrides, shared by the build and install invocations.

        pd-lib-builder honours all of these on the command line:
          system             force the Linux branch (see below)
          CC                 the cross compiler (its default is plain `gcc`)
          arch.c.flags=      cleared: an x86_64 build host would otherwise
                             inject -march=core2 -msse... into an aarch64
                             OHOS compile
          PDINCLUDEDIR       where m_pd.h lives (its default probes
                             /usr/include/pd)
          PDLIBDIR           install root, relative to DESTDIR
          lib.version        baked into the plugin via -DVERSION
          LDFLAGS            DT_SONAME, so the shared object is identifiable

        `system=Linux` is required, not cosmetic.  pd-lib-builder derives its
        platform from `uname` by exact string match (Linux / Darwin / MSYS /
        MINGW), so it has no branch for OHOS.  The OHOS CI worker reports
        `uname` = "HarmonyOS": without the override the Linux block is skipped
        entirely, `extension` stays empty and the link degenerates to
        `-o libdir.` with no `-shared`, which fails with
        "ld.lld: error: undefined symbol: main" (plus every Pd symbol).  Note
        this is invisible on a Linux dev box -- WSL2 reports uname=Linux, so the
        bug only reproduces on the real worker.  Taking the Linux branch gives
        the artifact the name Pd actually looks for on non-Apple platforms
        (`pd_linux`), plus -fPIC/-shared/-rdynamic and -lc -lm.
        """
        args = [
            "system=Linux",
            f'CC="{self._compiler()}"',
            "arch.c.flags=",
            f'PDINCLUDEDIR="{self._pd_include_dir()}"',
            "PDLIBDIR=/lib",
            "lib.version=%s" % self.version,
            'LDFLAGS="-Wl,-soname,libdir.pd_linux"',
        ]
        if destination is not None:
            args.append(f'DESTDIR="{destination}"')
        return " ".join(args)

    def source(self):
        data = self.conan_data["sources"][self.version]
        get(self, url=data["url"], sha256=data["sha256"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R9: pd-lib-builder generates a single object file; keep -j1 so the
        # build log stays deterministic.
        self.run(f"make {self._make_args()} -j1",
                 env="conanbuild", cwd=self.source_folder)

    def package(self):
        # installpath is $(DESTDIR)$(PDLIBDIR)/$(lib.name), i.e.
        # <package>/lib/libdir/ — matching where Pd looks for extra libraries.
        self.run(f"make install {self._make_args(self.package_folder)}",
                 env="conanbuild", cwd=self.source_folder)
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # The plugin lives one level below lib/ (lib/libdir/libdir.pd_linux);
        # Pd dlopen()s it by path, it is not linked against anything, so it has
        # no libs to export.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib", "lib/libdir"]
        self.cpp_info.libs = []
        self.cpp_info.defines = ["PD"]
        # Re-export the Pd API headers resolved above, so consumers can compile
        # Pd code against this package alone (puredata/0.54.1 publishes no
        # include dirs of its own).  Absolute path on purpose: the headers live
        # in the dependency's package folder, same pattern as cloog's GMP
        # headers.
        self.cpp_info.includedirs = [self._pd_include_dir()]
