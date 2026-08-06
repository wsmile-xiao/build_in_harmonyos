#!/usr/bin/env python3
"""Conan recipe for abgate 1.2.0 — LV2 noise gate plugin.

abGate is an LV2 audio plugin for noise gating. This recipe builds only the
core DSP plugin (gate.so) without GUI components (gtkmm/Qt not available on
OHOS). The GUI is disabled by default.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AbgateConan(ConanFile):
    name = "abgate"
    version = "1.2.0"
    description = "abGate - LV2 noise gate plugin for Linux audio"
    license = "LGPL-3.0-only"
    homepage = "https://abgate.sourceforge.io/"
    url = "https://github.com/antanasbruzas/abGate"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lv2/1.18.11-git")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _get_cc(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _get_cxx(self):
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("cpp") or "clang++"

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cxx = self._get_cxx()

        # Get lv2 include and lib paths from conan dependency
        lv2_cflags = ""
        lv2_ldflags = ""
        lv2_libs = ""
        try:
            dep = self.dependencies["lv2"]
            if dep.cpp_info.includedirs:
                base = dep.cpp_info.includedirs[0]
                lv2_cflags = f"-I{base} -I{base}/lv2"
            if dep.cpp_info.libdirs:
                lv2_ldflags = " ".join(f"-L{d}" for d in dep.cpp_info.libdirs)
            if dep.cpp_info.libs:
                lv2_libs = " ".join(f"-l{l}" for l in dep.cpp_info.libs)
        except KeyError:
            raise ConanException("lv2 dependency not found in build requirements")
        except AttributeError as e:
            raise ConanException(f"Failed to get lv2 dependency info: {e}")

        # Build the core DSP plugin (gate.so) without GUI components
        # gate_gui.so requires gtkmm-2.4 which is not available on OHOS
        self.run(
            f"{cxx} -shared -fPIC -DPIC -Wl,--as-needed "
            f"gate.cpp {lv2_cflags} {lv2_ldflags} {lv2_libs} "
            f"-o gate.so",
            cwd=src
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Install the LV2 bundle
        bundle_dir = os.path.join(pkg, "lib", "lv2", "abGate.lv2")
        os.makedirs(bundle_dir, exist_ok=True)

        # Copy LV2 bundle files
        for f in ["manifest.ttl", "gate.ttl", "gate.so",
                   "bypass_off.png", "bypass_on.png", "knob.png", "background.png"]:
            fpath = os.path.join(src, f)
            if os.path.isfile(fpath):
                shutil.copy2(fpath, os.path.join(bundle_dir, f))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []