from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
import os


class CcToolConan(ConanFile):
    name = "cc-tool"
    version = "0.26"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/cctool/"
    description = "Texas Instruments CC Debugger programming utility"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml", "patches/*"

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-static")
        tc.configure_args.append("--prefix=/")
        # The legacy config.guess cannot identify HarmonyOS; the device is
        # native aarch64, so provide a stable build tuple explicitly.
        tc.configure_args.append("--build=x86_64-pc-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.configure_args.append("BOOST_CPPFLAGS=-I{}/".format(self.dependencies["boost"].cpp_info.includedirs[0]))
        tc.configure_args.append("BOOST_PROGRAM_OPTIONS_LIBS=-lboost_program_options")
        tc.configure_args.append("BOOST_FILESYSTEM_LIBS=-lboost_filesystem")
        tc.configure_args.append("BOOST_REGEX_LIBS=-lboost_regex")
        boost_libdir = self.dependencies["boost"].cpp_info.libdirs[0]
        for component in ("program_options", "filesystem", "system", "regex"):
            tc.configure_args.append("boost_cv_lib_{}=yes".format(component))
            tc.configure_args.append("boost_cv_lib_{}_LDFLAGS=-L{}".format(component, boost_libdir))
            if component == "system":
                tc.configure_args.append("boost_cv_lib_system_LIBS=")
            else:
                tc.configure_args.append("boost_cv_lib_{}_LIBS=-lboost_{}".format(component, component))
        tc.generate()
        AutotoolsDeps(self).generate()
        env = VirtualBuildEnv(self)
        env.generate(scope="build")

    def requirements(self):
        # cc-tool requires Boost >= 1.34; use the published OHOS recipe.
        self.requires("boost/1.84.0")
        self.requires("libusb/1.0.27")

    def build(self):
        apply_conandata_patches(self)
        # The runner-provided TMPDIR may be mounted non-executable on device.
        os.environ["TMPDIR"] = self.build_folder
        os.environ["TMPPREFIX"] = os.path.join(self.build_folder, "zsh-tmp")
        boost = self.dependencies["boost"]
        os.environ["CPPFLAGS"] = "-I{}".format(boost.cpp_info.includedirs[0])
        os.environ["LDFLAGS"] = "-L{}".format(boost.cpp_info.libdirs[0])
        os.environ["BOOST_PROGRAM_OPTIONS_LIBS"] = "-lboost_program_options"
        os.environ["BOOST_FILESYSTEM_LIBS"] = "-lboost_filesystem"
        os.environ["BOOST_REGEX_LIBS"] = "-lboost_regex"
        libusb = self.dependencies["libusb"]
        libusb_include_root = os.path.dirname(libusb.cpp_info.includedirs[0])
        os.environ["CPPFLAGS"] += " -I{}".format(libusb_include_root)
        pkg_config = os.path.join(self.build_folder, "pkg-config")
        with open(pkg_config, "w", encoding="utf-8") as script:
            script.write("#!/bin/sh\n")
            script.write("case \"$*\" in\n")
            script.write("  *--cflags*) echo -I{} ;;\n".format(libusb.cpp_info.includedirs[0]))
            script.write("  *--libs*) echo -L{} -lusb-1.0 ;;\n".format(libusb.cpp_info.libdirs[0]))
            script.write("  *--modversion*) echo 1.0.27 ;;\n")
            script.write("  *) exit 1 ;;\n")
            script.write("esac\n")
        os.chmod(pkg_config, 0o755)
        os.environ["PKG_CONFIG"] = pkg_config
        os.environ["LIBUSB_CFLAGS"] = "-I{}".format(libusb_include_root)
        os.environ["LIBUSB_LIBS"] = "-L{} -lusb-1.0".format(libusb.cpp_info.libdirs[0])
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "cc-tool", dst=os.path.join(self.package_folder, "bin"),
             src=os.path.join(self.build_folder, "src"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
