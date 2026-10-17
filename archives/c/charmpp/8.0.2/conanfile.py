#!/usr/bin/env python3
"""Conan recipe for Charm++ 8.0.2 (netlrts) on OpenHarmony / HarmonyOS PC (aarch64).

Charm++ ships its own build driver (`buildcmake`, a thin CMake wrapper) and builds
in-source.  The recipe therefore drives that wrapper from the source folder; the
platform adaptation lives in patches/ (CMake platform branch, thread backend,
preprocessor, autotools config.guess/sub, bash shebangs), see notes.md.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CharmppConan(ConanFile):
    name = "charmpp"
    version = "8.0.2"
    description = ("Charm++ parallel programming runtime and charmc/charmrun "
                   "tool chain (netlrts build) for OpenHarmony / HarmonyOS PC aarch64")
    license = "Apache-2.0"
    homepage = "https://github.com/charmplusplus/charm"
    url = "https://github.com/charmplusplus/charm"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Charm++ enables its zlib support (CMK_USE_ZLIB) by default
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("charmpp/8.0.2 is packaged for OpenHarmony/HarmonyOS only")
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("charmpp/8.0.2 supports aarch64 (conan arch=armv8) only")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan profile, never from bare shell variables
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # HarmonyOS PC has no /bin/bash; hnp provides bash 5.x. Resolution
        # order: CONFIG_SHELL (injected by the platform profile) -> hnp
        # versioned layout (bash.org/bash_*/bin/bash) -> legacy flat path.
        # The last two are baked into the packaged charmc/charmrun shebangs
        # (patches 0008/0010/0011), so this list must stay in sync with them.
        bash = os.environ.get("CONFIG_SHELL") or ""
        if not bash or not os.path.isfile(bash):
            import glob as _glob
            candidates = (
                sorted(_glob.glob("/data/service/hnp/bash.org/bash_*/bin/bash"))
                + ["/data/service/hnp/bin/bash"]
            )
            bash = next((c for c in candidates if os.path.isfile(c)), bash)
        if not bash or not os.path.isfile(bash):
            raise ConanInvalidConfiguration(
                "no usable bash found: set CONFIG_SHELL to an existing bash "
                "executable (candidates: CONFIG_SHELL, "
                "/data/service/hnp/bash.org/bash_*/bin/bash, "
                "/data/service/hnp/bin/bash)")

        # OHOS/HMDFS environment workarounds needed by the in-tree build:
        #  * bash must have $PWD exported, getcwd() fails under /storage/... (bash only)
        #  * autoconf's config.status (bundled hwloc) creates its temp directory with
        #    `mktemp -d`, which is not writable on HMDFS here; a failing mktemp makes
        #    it fall back to the writable mkdir path (same trick as
        #    archives/o/open-mpi/5.0.10)
        shim_dir = os.path.join(self.build_folder, ".ohos-bin")
        os.makedirs(shim_dir, exist_ok=True)
        mktemp_shim = os.path.join(shim_dir, "mktemp")
        # Same interpreter as the build shell: /bin/sh may not be executable
        # under the OHOS app sandbox MAC, so prefer the resolved bash.
        with open(mktemp_shim, "w") as handle:
            handle.write(f"#!{bash}\nexit 1\n")
        os.chmod(mktemp_shim, 0o755)

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("PWD", self.source_folder)
        env.prepend_path("PATH", os.path.dirname(bash))
        env.prepend_path("PATH", shim_dir)
        # `buildcmake` invokes cmake directly, so dependencies are located through
        # CMake's own search path (private prefix, R49)
        env.define("CMAKE_PREFIX_PATH", self.dependencies["zlib"].package_folder)

        jobs = min(build_jobs(self), 8)
        install_prefix = os.path.join(self.build_folder, "install")
        production = " --with-production" if str(self.settings.build_type) == "Release" else ""
        command = (f'"{bash}" ./buildcmake charm++ netlrts-linux-arm8 clang'
                   f'{production} -j{jobs} --force'
                   f' --install-prefix="{install_prefix}"')
        # Charm++ builds in-source (buildcmake creates <source>/<triplet> and symlinks)
        with env.vars(self, scope="build").apply():
            self.run(command, cwd=self.source_folder)

    def package(self):
        copy(self, "*", src=os.path.join(self.build_folder, "install"), dst=self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # Charm++ applications are compiled and linked through the packaged
        # bin/charmc wrapper (it selects the right Charm++/Converse library set),
        # so no individual library names are exported here.
        self.cpp_info.libs = []
