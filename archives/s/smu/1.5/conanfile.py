import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain


class SmuConan(ConanFile):
    name = "smu"
    version = "1.5"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/Gottox/smu"
    description = "A simple interpreter for a simplified Markdown dialect"
    topics = ("markdown", "html", "command-line")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # The current framework requires an explicit patch pipeline even when
        # this upstream version needs no patch; Conan treats the empty list as a no-op.
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("This recipe supports Linux and OHOS")
        if str(self.settings.compiler) not in ("gcc", "clang"):
            raise ConanInvalidConfiguration("This recipe requires GCC or Clang")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_cflags = ["-Wall", "-ansi", "-fPIE"]
        tc.extra_ldflags = ["-pie", "-Wl,-z,relro,-z,now"]
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        compiler = compilers.get("c", "clang" if str(self.settings.compiler) == "clang" else "gcc")
        # config.mk overwrites environment variables and adds host /usr paths.
        # Explicit make variables retain Conan's profile flags without patching upstream.
        cflags = tc.cflags + ["-D" + shlex.quote(define) for define in tc.defines]
        cflags.append(r'-DVERSION=\"1.5\"')
        variables = {
            "CC": shlex.quote(compiler),
            "INCS": "-I.",
            "LIBS": "",
            "CFLAGS": " ".join(cflags),
            "LDFLAGS": " ".join(tc.ldflags),
        }
        if str(self.settings.os) == "OHOS":
            variables["SHELL"] = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        tc.make_args = [key + "=" + value for key, value in variables.items()]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        Autotools(self).make(args=["-j1"])

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "smu", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # The upstream install target only copies the executable and substitutes VERSION.
        man = load(self, os.path.join(self.source_folder, "smu.1"))
        save(self, os.path.join(self.package_folder, "share", "man", "man1", "smu.1"),
             man.replace("VERSION", str(self.version)))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
