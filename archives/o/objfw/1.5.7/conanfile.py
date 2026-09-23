import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain

required_conan_version = ">=2.0"


class ObjFWConan(ConanFile):
    name = "objfw"
    version = "1.5.7"
    description = "ObjFW is a portable framework for the Objective-C language"
    license = "LGPL-3.0-only"
    homepage = "https://objfw.nil.im/"
    url = "https://github.com/ObjFW/ObjFW"
    topics = ("objective-c", "runtime", "framework", "objc")
    package_type = "library"
    bindirs = ["bin"]          # objfw-config/ofarc/ofdns/... developer tools
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tls": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_tls": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        if self.options.with_tls:
            self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("ObjFW recipe is currently validated for OHOS only")
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("ObjFW recipe is currently validated for OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # ObjFW's buildsys is in-source: configure generates Makefile in the
        # source root, so build folder must equal the source folder.
        self.folders.source = "."
        self.folders.generators = "generators"
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        # HMDFS does not support jobserver FIFOs: force single-job make
        self.conf.define("tools.build:jobs", 1)
        tc = AutotoolsToolchain(self)
        # config.guess cannot recognize HarmonyOS (E007): pass explicit
        # host/build triplets so configure does not need to guess.
        tc.configure_args.extend([
            "--host=aarch64-linux-ohos",
            "--build=aarch64-unknown-linux-ohos",
        ])
        tc.configure_args.extend([
            "--disable-shared" if not self.options.shared else "--enable-shared",
        ])
        if self.options.with_tls:
            tc.configure_args.append("--with-tls")
        else:
            tc.configure_args.append("--without-tls")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["objfw", "objfwrt", "objfwtls"]
        # Consumers MUST compile Objective-C sources with the ObjFW runtime
        # and constant string class; without -fconstant-string-class the
        # @"..." literals are emitted as CFConstantString and crash at
        # runtime when treated as OFConstantString.
        self.cpp_info.objcflags = [
            "-fobjc-runtime=objfw",
            "-fconstant-string-class=OFConstantString",
        ]
        self.cpp_info.set_property("cmake_file_name", "ObjFW")
        self.cpp_info.set_property("cmake_target_name", "ObjFW::ObjFW")
        self.cpp_info.set_property("pkg_config_name", "objfw")
