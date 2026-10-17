#!/usr/bin/env python3
"""Conan recipe for libfirm 1.22.0.

libfirm is a C compiler backend library built with its own Makefile (no
configure script). OHOS adaptations:
- The Makefile's build-time generators are Python 2-era (vendored jinja2
  2.8-dev / markupsafe) and use ``#!/usr/bin/env python``; on Python 3.10+
  they need the patches in patches/ (collections.abc, imp removal, regex
  inline flag) and a ``python`` -> python3 link plus ``install`` on PATH.
- Perl generators need ``.' in @INC (PERL_USE_UNSAFE_INC=1) on Perl >= 5.26.
- The OHOS profile has no ``cc``, so CC/LINK are taken from the conan conf
  ``tools.build:compiler_executables`` (R33).
- LDBL_MANT_DIG == 113 (IEEE quad) on aarch64 is upstream-unsupported; the
  fltcalc patch adds the quad descriptor.
"""
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibfirmConan(ConanFile):
    name = "libfirm"
    version = "1.22.0"
    description = (
        "libFirm is a graph-based intermediate representation (IR) library "
        "used by compilers, with SSA form, side-effect modelling and "
        "optimization passes."
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libfirm/libfirm"
    url = "https://github.com/libfirm/libfirm"
    topics = ("compiler", "ir", "ssa", "optimization")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libfirm is supported only on Linux/OHOS"
            )
        if self.settings.arch not in ("x86_64", "armv8"):
            raise ConanInvalidConfiguration(
                "libfirm supports x86_64 and armv8 (aarch64)"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Build-time generators are invoked as `python` and the install
        # recipe calls `install`; neither exists under the OHOS profile PATH.
        # Provide both from a private bin dir prepended to the build env.
        bin_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        python3 = shutil.which("python3") or "python3"
        python_link = os.path.join(bin_dir, "python")
        if not os.path.lexists(python_link):
            os.symlink(python3, python_link)
        install_sh = os.path.join(bin_dir, "install")
        if not os.path.exists(install_sh):
            with open(install_sh, "w") as f:
                f.write("#!/bin/sh\nexec /data/service/hnp/bin/busybox install \"$@\"\n")
            os.chmod(install_sh, 0o755)
        self.buildenv.prepend_path("PATH", bin_dir)
        # Perl >= 5.26 removed '.' from @INC; the emitter/regalloc generators
        # `do` the arch spec via a relative path.
        self.buildenv.define("PERL_USE_UNSAFE_INC", "1")
        VirtualBuildEnv(self).generate()

    def _compiler(self):
        ce = self.conf.get("tools.build:compiler_executables", default=None)
        cc = cpp = None
        if ce:
            try:
                d = json.loads(ce) if isinstance(ce, str) else ce
                cc = d.get("c")
                cpp = d.get("cpp")
            except Exception:
                pass

        def _resolve(candidate, fallback):
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            return fallback

        cc = _resolve(cc, "clang")
        cpp = _resolve(cpp, cc)
        return cc, cpp

    def build(self):
        apply_conandata_patches(self)
        cc, cpp = self._compiler()
        variant = "optimize" if self.settings.build_type in (
            "Release", "RelWithDebInfo", "MinSizeRel") else "debug"
        # -j1: make's jobserver fifo is not permitted on the OHOS filesystem
        # (Operation not permitted). CC/LINK must be explicit: no `cc` exists.
        vars_ = [
            "CC=" + shlex.quote(cc),
            "LINK=" + shlex.quote(cpp),
            "variant=" + variant,
        ]
        self.run("make -j1 " + " ".join(vars_), cwd=self.source_folder)

    def package(self):
        variant = "optimize" if self.settings.build_type in (
            "Release", "RelWithDebInfo", "MinSizeRel") else "debug"
        build_dir = os.path.join(self.source_folder, "build", variant)
        gen_inc = os.path.join(self.source_folder, "build", "gen", "include", "libfirm")
        # Install API headers (static + generated) and the library.
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include", "libfirm"),
             dst=os.path.join(self.package_folder, "include", "libfirm"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include", "libfirm", "adt"),
             dst=os.path.join(self.package_folder, "include", "libfirm", "adt"))
        if os.path.isdir(gen_inc):
            copy(self, "*.h", src=gen_inc,
                 dst=os.path.join(self.package_folder, "include", "libfirm"))
        copy(self, "libfirm.a", src=build_dir,
             dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libfirm.so", src=build_dir,
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["firm"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libfirm")
        self.cpp_info.set_property("cmake_target_name", "libfirm::libfirm")