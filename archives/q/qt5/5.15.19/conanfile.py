#!/usr/bin/env python3
"""Conan recipe for qt5 (qtbase) 5.15.19 on OpenHarmony PC."""
import os
import shlex
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Qt5Conan(ConanFile):
    name = "qt5"
    version = "5.15.19"
    description = "Qt5 Base (Core/Gui/Network/Widgets/PrintSupport/Xml) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt5 only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                break
            except ConanException as error:
                self.output.warning(f"Failed to download Qt5 source from {url}: {error}")
        else:
            raise ConanInvalidConfiguration("Unable to download Qt5 source from all mirrors")

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "qt5 requires c and cpp compiler executables from the Conan profile"
            )

        zlib = self.dependencies["zlib"]
        zlib_inc = os.path.join(zlib.package_folder, "include")
        zlib_lib = os.path.join(zlib.package_folder, "lib")

        try:
            subprocess.run(
                shlex.split(cxx) + ["-x", "c++", "-", "-o", os.devnull, "-lpthread"],
                input=(
                    b"#include <pthread.h>\n"
                    b"int main() {\n"
                    b"    int (*volatile cancel)(pthread_t) = &pthread_cancel;\n"
                    b"    return cancel == nullptr;\n"
                    b"}\n"
                ),
                check=True, capture_output=True, timeout=10,
            )
            has_pthread_cancel = True
        except (subprocess.CalledProcessError, FileNotFoundError,
                subprocess.TimeoutExpired, OSError):
            has_pthread_cancel = False

        try:
            subprocess.run(
                shlex.split(cxx) + ["-x", "c++", "-", "-c", "-o", os.devnull],
                input=(
                    b"#include <sys/types.h>\n"
                    b"#include <sys/socket.h>\n"
                    b"int main() {\n"
                    b"    socklen_t len = 0;\n"
                    b"    return (int)len;\n"
                    b"}\n"
                ),
                check=True, capture_output=True, timeout=10,
            )
            has_socklen_t = True
        except (subprocess.CalledProcessError, FileNotFoundError,
                subprocess.TimeoutExpired, OSError):
            has_socklen_t = False

        build_env = Environment()
        build_env.define("CC", cc)
        build_env.define("CXX", cxx)
        build_env.append("CFLAGS", f"-I{zlib_inc}")
        build_env.append("CXXFLAGS", f"-I{zlib_inc}")
        build_env.append("LDFLAGS", f"-L{zlib_lib}")
        if has_pthread_cancel:
            build_env.append("CXXFLAGS", "-DHAVE_PTHREAD_CANCEL")
        if has_socklen_t:
            build_env.append("CFLAGS", "-DHAVE_SOCKLEN_T")
            build_env.append("CXXFLAGS", "-DHAVE_SOCKLEN_T")

        with build_env.vars(self).apply():
            configure_shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh")
            if not configure_shell:
                raise ConanInvalidConfiguration("A POSIX shell is required to run Qt configure")
            self.run(
                f'cd "{src_dir}" && {shlex.quote(configure_shell)} ./configure '
                f'-prefix "{self.package_folder}" '
                f'-opensource -confirm-license '
                f'-no-dbus -no-accessibility '
                f'-opengl es2 -no-xcb -no-eglfs -no-linuxfb '
                f'-no-feature-sql '
                f'-no-feature-systemsemaphore -no-feature-sharedmemory '
                f'-nomake tests -nomake examples '
                f'-no-iconv -no-glib -no-icu -no-vulkan '
                f'-no-openssl -no-libproxy -no-system-proxies '
                f'-system-zlib '
                f'-platform linux-clang '
                f'-recheck-all',
            )

            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{src_dir}" && make -j{jobs} QMAKE_STRIP=""')

    def package(self):
        src_dir = self.source_folder
        lib_dir = os.path.join(src_dir, "lib")
        include_dir = os.path.join(src_dir, "include")
        mkspecs_dir = os.path.join(src_dir, "mkspecs")
        bin_dir = os.path.join(src_dir, "bin")

        copy(self, "*.so*", src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.prl", src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.la", src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.pc", src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", src=lib_dir, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        if os.path.isdir(include_dir):
            copy(self, "*", src=include_dir, dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.h", src=os.path.join(src_dir, "src"), dst=os.path.join(self.package_folder, "src"), keep_path=True)
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir, dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)
        if os.path.isdir(bin_dir):
            copy(self, "*", src=bin_dir, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        plugins_dir = os.path.join(src_dir, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir, dst=os.path.join(self.package_folder, "plugins"), keep_path=True)
        cmake_dir = os.path.join(lib_dir, "cmake")
        if os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir, dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=True)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]

        qt5core = self.cpp_info.components["Qt5Core"]
        qt5core.libs = ["Qt5Core"]
        qt5core.includedirs = ["include", "include/QtCore"]
        qt5core.requires = ["zlib::zlib"]
        qt5core.set_property("cmake_file_name", "Qt5Core")
        qt5core.set_property("cmake_target_name", "Qt5::Core")

        qt5network = self.cpp_info.components["Qt5Network"]
        qt5network.libs = ["Qt5Network"]
        qt5network.includedirs = ["include", "include/QtNetwork"]
        qt5network.requires = ["Qt5Core"]
        qt5network.set_property("cmake_file_name", "Qt5Network")
        qt5network.set_property("cmake_target_name", "Qt5::Network")

        qt5gui = self.cpp_info.components["Qt5Gui"]
        qt5gui.libs = ["Qt5Gui"]
        qt5gui.includedirs = ["include", "include/QtGui"]
        qt5gui.requires = ["Qt5Core"]
        qt5gui.set_property("cmake_file_name", "Qt5Gui")
        qt5gui.set_property("cmake_target_name", "Qt5::Gui")

        qt5widgets = self.cpp_info.components["Qt5Widgets"]
        qt5widgets.libs = ["Qt5Widgets"]
        qt5widgets.includedirs = ["include", "include/QtWidgets"]
        qt5widgets.requires = ["Qt5Core", "Qt5Gui"]
        qt5widgets.set_property("cmake_file_name", "Qt5Widgets")
        qt5widgets.set_property("cmake_target_name", "Qt5::Widgets")

        qt5test = self.cpp_info.components["Qt5Test"]
        qt5test.libs = ["Qt5Test"]
        qt5test.includedirs = ["include", "include/QtTest"]
        qt5test.requires = ["Qt5Core"]
        qt5test.set_property("cmake_file_name", "Qt5Test")
        qt5test.set_property("cmake_target_name", "Qt5::Test")

        qt5xml = self.cpp_info.components["Qt5Xml"]
        qt5xml.libs = ["Qt5Xml"]
        qt5xml.includedirs = ["include", "include/QtXml"]
        qt5xml.requires = ["Qt5Core"]
        qt5xml.set_property("cmake_file_name", "Qt5Xml")
        qt5xml.set_property("cmake_target_name", "Qt5::Xml")

        qt5concurrent = self.cpp_info.components["Qt5Concurrent"]
        qt5concurrent.libs = ["Qt5Concurrent"]
        qt5concurrent.includedirs = ["include", "include/QtConcurrent"]
        qt5concurrent.requires = ["Qt5Core"]
        qt5concurrent.set_property("cmake_file_name", "Qt5Concurrent")
        qt5concurrent.set_property("cmake_target_name", "Qt5::Concurrent")
