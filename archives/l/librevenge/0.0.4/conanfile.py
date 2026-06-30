#!/usr/bin/env python3
"""Conan recipe — librevenge 0.0.4 (Autotools).

R26: Static linking for DevBox compatibility (--disable-shared --enable-static).
R27: Dependencies use @ohpcd/stable (boost/zlib system-installed, pending @ohpcd/stable).
R28: test_package/ included.

Platform adaptations:
  - E007/E072: Replace config.guess/config.sub with OHOS-aware versions
  - umask 077→022: HarmonyOS FS can't create files in dirs with restricted group perms
  - Patches: configure.ac -Wno-error=shadow, RVNGStringIterTest.cpp #include <cassert>
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibrevengeConan(ConanFile):
    name = "librevenge"
    version = "0.0.4"
    description = "A base library for document import filters (librevenge)"
    license = "MPL-2.0"
    homepage = "https://sourceforge.net/projects/libwpd/files/librevenge/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: Dependencies must reference @ohpcd/stable
        # boost (header-only) and zlib are system-installed; when @ohpcd/stable
        # versions become available, add:
        #   self.requires("boost/1.84.0@ohpcd/stable", transitive_headers=True)
        #   self.requires("zlib/1.3.1@ohpcd/stable")
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Build static libraries (DevBox only copies bin/, no lib/)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        # boost spirit classic has -Wshadow warnings; suppress as non-error
        tc.extra_cxxflags.append("-Wno-error=shadow")
        # System-installed boost headers and zlib
        sys_prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        tc.extra_cflags.append(f"-I{sys_prefix}/include")
        tc.extra_cxxflags.append(f"-I{sys_prefix}/include")
        tc.extra_ldflags.append(f"-L{sys_prefix}/lib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # E007/E072: Replace config.guess/config.sub with OHOS-aware versions
        am_dir = "/storage/Users/currentUser/usr/local/share/automake-1.17"
        for script in ("config.guess", "config.sub"):
            sys_script = os.path.join(am_dir, script)
            if os.path.exists(sys_script):
                shutil.copy2(sys_script, os.path.join(src, script))

        # Regenerate configure from patched configure.ac
        self.run("autoreconf -fi", cwd=src)

        # Fix: umask 077 -> 022 in generated configure (HarmonyOS FS limitation)
        configure = os.path.join(src, "configure")
        if os.path.exists(configure):
            with open(configure, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure, "w") as f:
                f.write(content)

        # Set PKG_CONFIG_PATH for cppunit and zlib
        env = os.environ.copy()
        sys_prefix = env.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        pkg_config_path = f"{sys_prefix}/lib/pkgconfig:{env.get('PKG_CONFIG_PATH', '')}"
        env["PKG_CONFIG_PATH"] = pkg_config_path

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Headers are in include/librevenge-0.0/librevenge/
        self.cpp_info.includedirs.append("include/librevenge-0.0")
        # Library files are librevenge-0.0.a etc; strip "lib" prefix for -l flag
        self.cpp_info.libs = [
            "revenge-0.0",
            "revenge-generators-0.0",
            "revenge-stream-0.0",
        ]
        self.cpp_info.set_property("cmake_file_name", "librevenge")
        self.cpp_info.set_property("cmake_target_name", "librevenge::librevenge")
