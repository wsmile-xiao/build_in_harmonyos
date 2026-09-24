import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AutofdoConan(ConanFile):
    name = "autofdo"
    version = "0.19"
    package_type = "application"
    description = "AutoFDO - convert perf profiles to AutoFDO profiles for GCC/LLVM"
    license = "Apache-2.0"
    homepage = "https://github.com/google/autofdo"
    url = "https://github.com/google/autofdo"
    settings = "os", "compiler", "build_type", "arch"
    requires = "openssl/3.5.6", "elfutils/0.195"
    tool_requires = "automake/1.18", "libtool/2.5.4"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os != "OHOS":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("autofdo recipe targets OHOS")
        if self.settings.arch != "armv8":
            from conan.errors import ConanInvalidConfiguration
            raise ConanInvalidConfiguration("autofdo recipe targets OHOS armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The release archive may omit vendored submodules; fetch only missing
        # directories so existing archive contents are never overwritten.
        for name, sub in self.conan_data["submodules"].items():
            destination = os.path.join("third_party", name)
            if not os.path.isdir(destination) or not os.listdir(destination):
                get(self, **sub, strip_root=True, destination=destination)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Generate configure from configure.ac (m4 macros ship in the tree).
        self.run("autoreconf -fi -I m4", cwd=src)

        # hmdfs temp dirs created with umask 077 are unwritable on OHOS.
        configure = os.path.join(src, "configure")
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("(umask 077 && mktemp -d", "(umask 000 && mktemp -d")
        content = content.replace("(umask 077 && mkdir", "(umask 000 && mkdir")
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(content)

        autotools = Autotools(self)
        autotools.configure(args=["--host=aarch64-linux-ohos", "--without-llvm"])
        autotools.make()

    def package(self):
        for binary in ("create_gcov", "dump_gcov", "sample_merger",
                       "profile_merger", "profile_diff", "profile_update",
                       "create_llvm_prof"):
            copy(self, binary, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.output.info("autofdo binaries installed to bin/")
