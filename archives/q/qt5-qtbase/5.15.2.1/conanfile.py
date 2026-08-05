#!/usr/bin/env python
"""Conan recipe for qt5-qtbase 5.15.2.1 on OpenHarmony PC (enables Core/Gui/Network/Widgets/PrintSupport/Xml)."""
import os
import shlex
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class Qt5QtbaseConan(ConanFile):
    name = "qt5-qtbase"
    version = "5.15.2.1"
    description = "Qt5 Base Core, Gui, Network, Test, Widgets, PrintSupport and Xml modules for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # R27/R18: zlib as Conan dependency, not inline build
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qt5-qtbase only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                return
            except ConanException as error:
                self.output.warning(f"Failed to download Qt5 source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download Qt5 source from all mirrors")

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        pkg = self.package_folder

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c")
        cxx = compilers.get("cpp") or compilers.get("cxx")
        if not cc or not cxx:
            raise ConanInvalidConfiguration(
                "qt5-qtbase requires c and cpp compiler executables from the Conan profile"
            )

        # Get zlib paths from Conan dependency
        zlib = self.dependencies["zlib"]
        zlib_inc = os.path.join(zlib.package_folder, "include")
        zlib_lib = os.path.join(zlib.package_folder, "lib")

        # Detect pthread_cancel availability (musl doesn't provide it).
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
            self.output.warning(
                "pthread_cancel detection failed; disabling HAVE_PTHREAD_CANCEL"
            )
            has_pthread_cancel = False

        build_env = Environment()
        build_env.define("CC", cc)
        build_env.define("CXX", cxx)
        build_env.append("CFLAGS", f"-I{zlib_inc}")
        build_env.append("CXXFLAGS", f"-I{zlib_inc}")
        build_env.append("LDFLAGS", f"-L{zlib_lib}")
        symlink_shim_dir = self._create_symlink_shim()
        build_env.prepend_path("PATH", symlink_shim_dir)
        if has_pthread_cancel:
            build_env.append("CXXFLAGS", "-DHAVE_PTHREAD_CANCEL")
        # R8 合规：不再向源码注入任何平台条件编译宏。
        # 抽象套接字命名空间改由 0001/0002 补丁无条件启用（Linux/OHOS 内核
        # 均支持 AF_UNIX 抽象套接字），因此无需按目标平台切换编译期分支。
        # Configure Qt5 with Conan-managed compilers and zlib paths.
        with build_env.vars(self).apply():
            configure_shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh")
            if not configure_shell:
                raise ConanInvalidConfiguration("A POSIX shell is required to run Qt configure")
            self.run(
                f'cd "{src_dir}" && {shlex.quote(configure_shell)} ./configure '
                f'-prefix "{pkg}" '
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

            # Prevent stripping because the OHOS loader rejects stripped ELF files.
            jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
            self.run(f'cd "{src_dir}" && make -j{jobs} QMAKE_STRIP=""')
            # 打包阶段不运行 Qt 自带 auto-test 套件：conan create 只负责构建+打包，
            # 运行期验证交给 test_package；跑全量测试会在 CI 45 分钟硬超时内无法完成
            # （PR #3804 CI #12438 超时根因）。Qt5Test 等模块库由主 make 正常产出，不受影响。

    def _create_symlink_shim(self):
        """Copy Qt ABI aliases when the OHOS workspace rejects symlinks."""
        shim_dir = os.path.join(self.build_folder, "conan_tools")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "ln")
        real_ln = shutil.which("ln") or "/system/bin/ln"
        with open(shim, "w", encoding="utf-8") as shim_file:
            shim_file.write(
                "#!/bin/sh\n"
                f"if {shlex.quote(real_ln)} \"$@\"; then\n"
                "  exit 0\n"
                "fi\n"
                "symbolic=0\n"
                "while [ $# -gt 0 ]; do\n"
                "  case \"$1\" in\n"
                "    --symbolic) symbolic=1; shift ;;\n"
                "    --) shift; break ;;\n"
                "    -*) flags=${1#-}; case \"$flags\" in *s*) symbolic=1 ;; esac; shift ;;\n"
                "    *) break ;;\n"
                "  esac\n"
                "done\n"
                "if [ \"$symbolic\" = 1 ] && [ $# -eq 2 ]; then\n"
                "  rm -f \"$2\"\n"
                "  cp -f \"$1\" \"$2\"\n"
                "  exit $?\n"
                "fi\n"
                "exit 1\n"
            )
        os.chmod(shim, 0o755)
        return shim_dir

    def package(self):
        src_dir = self.source_folder
        lib_dir = os.path.join(src_dir, "lib")
        include_dir = os.path.join(src_dir, "include")
        mkspecs_dir = os.path.join(src_dir, "mkspecs")
        bin_dir = os.path.join(src_dir, "bin")

        # Copy libraries (unstripped)
        copy(self, "*.so*", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.prl", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.la", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.pc", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        # Copy headers
        if os.path.isdir(include_dir):
            copy(self, "*", src=include_dir,
                 dst=os.path.join(self.package_folder, "include"), keep_path=True)

        # Qt's installed module headers are forwarding headers which retain
        # relative includes into src/. Ship the referenced headers, but not
        # the C++ implementation sources.
        copy(self, "*.h", src=os.path.join(src_dir, "src"),
             dst=os.path.join(self.package_folder, "src"), keep_path=True)

        # Copy mkspecs
        if os.path.isdir(mkspecs_dir):
            copy(self, "*", src=mkspecs_dir,
                 dst=os.path.join(self.package_folder, "mkspecs"), keep_path=True)

        # Copy bin tools
        if os.path.isdir(bin_dir):
            copy(self, "*", src=bin_dir,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        plugins_dir = os.path.join(src_dir, "plugins")
        if os.path.isdir(plugins_dir):
            copy(self, "*", src=plugins_dir,
                 dst=os.path.join(self.package_folder, "plugins"), keep_path=True)

        # Copy cmake configs
        cmake_dir = os.path.join(lib_dir, "cmake")
        if os.path.isdir(cmake_dir):
            copy(self, "*", src=cmake_dir,
                 dst=os.path.join(self.package_folder, "lib", "cmake"), keep_path=True)

    def package_info(self):
        # Define components so CMakeDeps generates per-module config files
        # (Qt5CoreConfig.cmake, Qt5TestConfig.cmake, etc.) matching the
        # standard Qt5 find_package() and Qt5:: target names.
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
        qt5gui.system_libs = ["EGL", "GLESv2"]
        qt5gui.set_property("cmake_file_name", "Qt5Gui")
        qt5gui.set_property("cmake_target_name", "Qt5::Gui")

        qt5test = self.cpp_info.components["Qt5Test"]
        qt5test.libs = ["Qt5Test"]
        qt5test.includedirs = ["include", "include/QtTest"]
        qt5test.requires = ["Qt5Core"]
        qt5test.set_property("cmake_file_name", "Qt5Test")
        qt5test.set_property("cmake_target_name", "Qt5::Test")

        qt5concurrent = self.cpp_info.components["Qt5Concurrent"]
        qt5concurrent.libs = ["Qt5Concurrent"]
        qt5concurrent.includedirs = ["include", "include/QtConcurrent"]
        qt5concurrent.requires = ["Qt5Core"]
        qt5concurrent.set_property("cmake_file_name", "Qt5Concurrent")
        qt5concurrent.set_property("cmake_target_name", "Qt5::Concurrent")

        qt5widgets = self.cpp_info.components["Qt5Widgets"]
        qt5widgets.libs = ["Qt5Widgets"]
        qt5widgets.includedirs = ["include", "include/QtWidgets"]
        qt5widgets.requires = ["Qt5Core", "Qt5Gui"]
        qt5widgets.set_property("cmake_file_name", "Qt5Widgets")
        qt5widgets.set_property("cmake_target_name", "Qt5::Widgets")

        qt5printsupport = self.cpp_info.components["Qt5PrintSupport"]
        qt5printsupport.libs = ["Qt5PrintSupport"]
        qt5printsupport.includedirs = ["include", "include/QtPrintSupport"]
        qt5printsupport.requires = ["Qt5Core", "Qt5Gui", "Qt5Widgets"]
        qt5printsupport.set_property("cmake_file_name", "Qt5PrintSupport")
        qt5printsupport.set_property("cmake_target_name", "Qt5::PrintSupport")

        qt5xml = self.cpp_info.components["Qt5Xml"]
        qt5xml.libs = ["Qt5Xml"]
        qt5xml.includedirs = ["include", "include/QtXml"]
        qt5xml.requires = ["Qt5Core"]
        qt5xml.set_property("cmake_file_name", "Qt5Xml")
        qt5xml.set_property("cmake_target_name", "Qt5::Xml")

        # Aggregate package-level cmake_file_name so CMakeDeps generates
        # Qt5Config.cmake, enabling `find_package(Qt5 COMPONENTS ...)` used by
        # consumers such as poppler (PR #3805).
        self.cpp_info.set_property("cmake_file_name", "Qt5")
