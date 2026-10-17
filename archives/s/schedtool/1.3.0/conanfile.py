import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SchedtoolConan(ConanFile):
    name = "schedtool"
    version = "1.3.0"
    description = "Query or change process scheduling policy, niceness and CPU affinity"
    license = "GPL-2.0-only"
    homepage = "https://github.com/freequaos/schedtool"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def layout(self):
        basic_layout(self, src_folder="src")

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("schedtool needs Linux-compatible scheduler APIs")
        if cross_building(self):
            raise ConanInvalidConfiguration("This recipe requires a native build and runtime tests")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang" if str(self.settings.compiler) in ("clang", "apple-clang") else "gcc")
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash" if str(self.settings.os) == "OHOS" else "/bin/sh")
        flags = ["-O0", "-g"] if str(self.settings.build_type) == "Debug" else ["-O2"]
        flags += ["-fPIE"] + self.conf.get("tools.build:cflags", default=[], check_type=list)
        ldflags = ["-pie", "-Wl,-z,relro,-z,now"]
        ldflags += self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        sysroot = self.conf.get("tools.build:sysroot", default=None, check_type=str)
        if sysroot:
            flags.append("--sysroot=" + shlex.quote(sysroot))
            ldflags.append("--sysroot=" + shlex.quote(sysroot))
        args = ["make", "-j1", "CC=" + cc, "SHELL=" + shell,
                "CFLAGS=" + " ".join(flags), "LDFLAGS=" + " ".join(ldflags)]
        self.run(" ".join(shlex.quote(arg) for arg in args), cwd=self.source_folder)
        self.output.info("Upstream 1.3.0 has no check/test target or test suite; see test_package/MANIFEST.yml")

    def package(self):
        copy(self, "schedtool", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "schedtool.8", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man8"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        for name in ("README", "INSTALL", "SCHED_DESIGN"):
            copy(self, name, src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "schedtool"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
