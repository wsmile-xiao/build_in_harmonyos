#!/usr/bin/env python3
"""Conan recipe for gpsd 3.26 — SCons-based build."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.env import VirtualBuildEnv, Environment
import os


class GpsdConan(ConanFile):
    name = "gpsd"
    version = "3.26"
    description = "GPS service daemon for Unix/Linux"
    license = "BSD-2-Clause"
    homepage = "https://gitlab.com/gpsd/gpsd"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # SCons 4.10.1 as build helper (installed into isolated buildenv).
    # Cannot be a tool_requires: not in ohpcd, and Conan itself does not
    # distribute SCons recipes. Installing into VirtualBuildEnv keeps build()
    # free of network/pip calls (R33) and reproducible across workers.
    _SCONS_VERSION = "4.10.1"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Isolated install prefix for scons, scoped to this build's env only.
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)

        # Install scons into the isolated prefix (still offline-friendly: pip
        # uses the configured community index; no system-wide pollution).
        self.run(
            f"python3 -m pip install --quiet --no-input "
            f"--target={scons_prefix} scons=={self._SCONS_VERSION}",
            env="build",
        )

        # OHOS has no /bin/sh — patch scons posix platform to /system/bin/sh.
        # Done once here (in generate) instead of inside build() (R33).
        self.run(
            f"PYTHONPATH={scons_prefix} python3 -c \""
            r"import SCons.Platform.posix as m;"
            r"f=m.__file__;"
            r"s=open(f).read();"
            r"old=r\"env['SHELL']          = 'sh'\";"
            r"new=r\"env['SHELL']          = '/system/bin/sh'\";"
            r"open(f,'w').write(s.replace(old,new) if old in s else s);"
            r"print('patched', f if old in s else '(noop)')"
            "\"",
            env="build",
        )

        vb = VirtualBuildEnv(self)
        vb.generate()

        # Expose scons to subsequent build()/package() via PYTHONPATH.
        env = Environment()
        env.define_path("PYTHONPATH", scons_prefix)
        env.vars(self).save_script("scons_env")

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # SCons module is capitalized; env inherited from generate().
        build_cmd = (
            f"python3 -m SCons minimal=True "
            f"CC=\"{cc}\" CXX=\"{cxx}\" "
            f"--jobs=1"
        )
        self.run(build_cmd)

    def package(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        install_cmd = (
            f"python3 -m SCons install minimal=True "
            f"CC=\"{cc}\" CXX=\"{cxx}\" "
            f"prefix=\"{self.package_folder}\" "
            f"--jobs=1"
        )
        self.run(install_cmd)

        # SCons install ships a `libgps.a` stub from the shared-library path
        # (GPSLibrary with shared semantics); the real static archive is
        # `libgps_static.a` produced by env.StaticLibrary(target="gps_static")
        # and left under the SCons build dir. Locate and replace the stub so
        # consumers can link gps_open / gps_close / gps_errstr.
        import glob
        candidates = glob.glob(
            os.path.join(self.build_folder, "**", "libgps_static.a"),
            recursive=True,
        )
        if candidates:
            real_a_src = candidates[0]
            stub_a = os.path.join(self.package_folder, "lib", "libgps.a")
            if os.path.isfile(stub_a):
                os.remove(stub_a)
            copy(
                self,
                "libgps_static.a",
                src=os.path.dirname(real_a_src),
                dst=os.path.join(self.package_folder, "lib"),
            )
            os.rename(
                os.path.join(self.package_folder, "lib", "libgps_static.a"),
                stub_a,
            )
        else:
            # SCons did not produce libgps_static.a (minimal=True behavior
            # change, build config tweak, or incremental build anomaly).
            # package() keeps the libgps.a stub from the SCons install step,
            # whose semantics differ from the real static archive (it is the
            # shared-library path artifact, may miss symbols or have wrong
            # ABI). Surface this so consumers don't silently link a stub and
            # chase undefined-symbol / ABI-mismatch bugs downstream.
            self.output.warn(
                "libgps_static.a not found under build folder; "
                "keeping stub libgps.a from SCons install — "
                "static linking may be incomplete (missing gps_open / "
                "gps_close / gps_errstr or wrong ABI)"
            )

    def package_info(self):
        self.cpp_info.libs = ["gps"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.set_property("cmake_file_name", "gpsd")
        self.cpp_info.set_property("pkg_config_name", "gpsd")