import os
import sysconfig

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DistccConan(ConanFile):
    name = "distcc"
    version = "3.4"
    description = "Distributed C/C++ compiler system that distributes compilation tasks across multiple machines"
    license = "GPL-2.0-or-later"
    homepage = "https://distcc.github.io/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-libiberty")
        # Add Python library path for include-server extension module linking.
        # sysconfig.get_config_var("LIBDIR") may return wrong path on OHOS;
        # use installed_base which points to the actual Python installation.
        py_prefix = sysconfig.get_config_var("installed_base") or sys.prefix
        py_libdir = os.path.join(py_prefix, "lib")
        if os.path.isdir(py_libdir):
            tc.extra_ldflags.append(f"-L{py_libdir}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Create symlink to libpython3.12.so in source dir so the include-server's
        # linker command (-L. -lpython3.12) can find it
        py_prefix = sysconfig.get_config_var("installed_base") or sys.prefix
        py_lib = os.path.join(py_prefix, "lib", "libpython3.12.so")
        if os.path.exists(py_lib):
            src_link = os.path.join(self.source_folder, "libpython3.12.so")
            if not os.path.exists(src_link):
                os.symlink(py_lib, src_link)
        autotools.make(args=["-j1"])

    def package(self):
        # Install programs, examples, and config only
        # Skip install-include-server which writes to system Python site-packages
        pkg = self.package_folder
        self.run(f"make install-programs install-example install-conf DESTDIR={pkg}", env="conanbuild")

        # Manually install include-server Python files
        copy(self, "*.py", os.path.join(self.source_folder, "include_server"),
             os.path.join(pkg, "share", "distcc", "include_server"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
