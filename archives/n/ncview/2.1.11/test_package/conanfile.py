#!/usr/bin/env python3
"""Conan test_package — ncview 2.1.11.

ncview is a GUI executable (R34: the test must exercise the package artifact).
The test environment is headless: ncview initializes the X toolkit during
argument handling, before reporting anything about input files, so without a
display it must exit non-zero printing its version banner plus Xt's
"Can't open display" diagnostic. That exercises the ELF dynamic dependency
chain (libnetcdf, libX11, libXt, libXext, libXpm — the vendored
Xaw/Xmu/udunits/expat are static), the runtime banner, and the X11 error path.
"""
import os
import shlex

from conan import ConanFile


class NcviewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dependency_libdirs(self):
        """Collect libdirs of the tested package and its transitive deps."""
        libdirs = []
        seen = set()
        views = []
        try:
            views.append(self.dependencies.host)
        except AttributeError:
            pass
        views.append(self.dependencies)
        for view in views:
            try:
                items = view.items()
            except AttributeError:
                continue
            for _, dep in items:
                base = getattr(dep, "package_folder", None) or ""
                for libdir in dep.cpp_info.libdirs:
                    if not os.path.isabs(libdir) and base:
                        libdir = os.path.join(base, libdir)
                    if libdir not in seen and os.path.isdir(libdir):
                        seen.add(libdir)
                        libdirs.append(libdir)
        return libdirs

    def test(self):
        ncview = self.dependencies["ncview"]
        bindir = ncview.cpp_info.bindirs[0] if ncview.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(ncview.package_folder, bindir)
        binary = os.path.join(bindir, "ncview")
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged ncview binary missing: {binary}")

        bogus = os.path.join(self.build_folder, "definitely_missing_file.nc")
        errlog = os.path.join(self.build_folder, "ncview_stderr.log")
        script = os.path.join(self.source_folder, "test_ncview.sh")

        # Explicit LD_LIBRARY_PATH: VirtualRunEnv libdirs are not always
        # populated for every dependency (known pattern in this repo), and the
        # ncview binary has no embedded rpath.
        ldpath = ":".join(self._dependency_libdirs())
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'{bash} {shlex.quote(script)} {shlex.quote(binary)} '
            f'{shlex.quote(bogus)} {shlex.quote(errlog)} '
            f'{shlex.quote(ldpath)}',
            env="conanrun",
        )
