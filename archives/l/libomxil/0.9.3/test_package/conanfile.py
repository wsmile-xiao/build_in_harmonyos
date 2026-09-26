#!/usr/bin/env python3
"""Consumer-side test for libomxil (Bellagio OpenMAX IL 0.9.3).

The probe is compiled the way a real consumer builds it (compiler taken from
the Conan profile, include/lib search paths from the aggregated cpp_info of
the tested package, every declared library linked in) and then exercises the
deployed Bellagio runtime:

  [1] run bin/omxregister-bellagio on the package's lib/bellagio component
      directory with OMX_BELLAGIO_REGISTRY pointing at a throwaway file —
      the registration step every Bellagio deployment performs (OMX_Init
      fails with ENOENT when no registry exists);
  [2] run the probe: OMX_Init() must succeed, the registered components
      must be enumerable via OMX_ComponentNameEnum(), the first component
      must instantiate via OMX_GetHandle() and release via OMX_FreeHandle(),
      and OMX_Deinit() must return OMX_ErrorNone;
  [3] the probe then audits the shipped ELF files (LIBOMXIL_PKG) with the
      HarmonyOS-specific assertions H1..H8: AArch64 ELF64 objects, the OHOS
      aarch64 dynamic loader, no glibc-only soname, and dlopen()ability of
      the loader plugin and of every component library.

On a cross build only compile+link is verified; on the OHOS CI worker
(build == host) the full runtime path is executed on the target.
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class LibomxilTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    # VirtualRunEnv/VirtualBuildEnv are listed explicitly because an explicit
    # generators list *replaces* the default one; without VirtualRunEnv there
    # is no conanrun environment for test().
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        """C compiler for the probe: the Conan profile value first (R33)."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") if isinstance(compilers, dict) else None
        if cc:
            return cc
        # Fallback only for profiles that do not pin the executables.
        for candidate in (os.environ.get("CC"), "clang", "cc", "gcc"):
            if candidate and (shutil.which(candidate)
                              or os.path.isfile(candidate)):
                return candidate
        return "cc"

    def _dep_dirs(self):
        incs = []
        libs = []
        for _ref, dep in self.dependencies.items():
            incs.extend(dep.cpp_info.includedirs)
            libs.extend(dep.cpp_info.libdirs)
        return list(dict.fromkeys(incs)), list(dict.fromkeys(libs))

    def _dep(self):
        return self.dependencies[self.tested_reference_str.split("/")[0]]

    def build(self):
        incs, libdirs = self._dep_dirs()
        dep = self._dep()
        cflags = " ".join("-I" + p for p in incs)
        link = " ".join(
            ["-L" + p for p in libdirs]
            + ["-l" + lib for lib in dep.cpp_info.libs]
            + ["-Wl,-rpath," + p for p in libdirs]
        )
        # -std=gnu99: musl only declares POSIX interfaces with the GNU dialect.
        self.run(f"{self._compiler()} -std=gnu99 -Wall test.c -o test_probe "
                 f"{cflags} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross build: compile and link verified only "
                             "(the probe runs on the OHOS target)")
            return

        dep = self._dep()
        bindir = dep.cpp_info.bindirs[0]
        libdir = dep.cpp_info.libdirs[0]
        omxregister = os.path.join(bindir, "omxregister-bellagio")
        components = os.path.join(libdir, "bellagio")
        # The registry is a runtime artifact, so it goes to a scratch directory
        # instead of the source tree.
        scratch = tempfile.mkdtemp(prefix="libomxil-probe-")
        registry = os.path.join(scratch, "omxregister-probe")

        try:
            # omxregister-bellagio returns 0 unconditionally (upstream main()
            # only DEBUG-logs errors), so the registry file is verified
            # afterwards instead of trusting the exit code.
            self.output.info(f"registering Bellagio components from "
                             f"{components}")
            self.run(f'export OMX_BELLAGIO_REGISTRY="{registry}"; '
                     f'"{omxregister}" "{components}"', env="conanrun")
            if not os.path.isfile(registry) or os.path.getsize(registry) == 0:
                raise ConanException(
                    "omxregister-bellagio did not produce a component "
                    "registry — OMX_Init() would fail with ENOENT")

            self.run(f'export OMX_BELLAGIO_REGISTRY="{registry}"; '
                     f'export LIBOMXIL_PKG="{dep.package_folder}"; '
                     f'"./test_probe"', env="conanrun")
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
