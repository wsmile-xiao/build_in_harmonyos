from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibnftnlConan(ConanFile):
    name = "libnftnl"
    version = "1.3.1"
    description = "Userspace library providing a low-level netlink programming interface to nf_tables"
    license = "GPL-2.0-or-later"
    homepage = "https://www.netfilter.org/projects/libnftnl/"
    url = "https://github.com/conan-io/conan-center-index"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmnl/1.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-static" if self.options.shared else "--enable-static")
        tc.configure_args.append("--enable-shared" if self.options.shared else "--disable-shared")
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-ohos",
            "--host=aarch64-unknown-linux-ohos",
        ])
        tc.extra_cflags += ["-D_UAPI_LINUX_SOCKET_H", "-D__kernel_sa_family_t=sa_family_t"]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = ["nftnl"]
        self.cpp_info.set_property("cmake_file_name", "libnftnl")
        self.cpp_info.set_property("cmake_target_name", "libnftnl::libnftnl")
