#!/usr/bin/env python3
"""Conan recipe for jemalloc 5.3.0 on HarmonyOS PC (aarch64).

Key OHOS adaptations:
- --disable-cxx: JEMALLOC_CXX_THROW incompatible with OHOS stdlib.h
- -Wno-array-bounds: rtree.h RTREE_CACHE_CHECK_L2 macro array index fix
- config.guess/config.sub patches for HarmonyOS platform detection
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JemallocConan(ConanFile):
    name = "jemalloc"
    version = "5.3.0"
    description = "jemalloc is a general purpose malloc(3) implementation that emphasizes fragmentation avoidance and scalable concurrency support."
    license = "BSD-2-Clause"
    homepage = "https://jemalloc.net/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_cxx": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_cxx": False,  # Disabled: JEMALLOC_CXX_THROW incompatible with OHOS stdlib.h
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.enable_cxx:
            self.settings.rm_safe("compiler.cppstd")
            self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--enable-static")
        # Disable C++ support (JEMALLOC_CXX_THROW incompatible with OHOS stdlib.h)
        if not self.options.enable_cxx:
            tc.configure_args.append("--disable-cxx")
        # Disable features that cause runtime issues on HarmonyOS
        tc.configure_args.append("--disable-initial-exec-tls")
        tc.configure_args.append("--disable-libdl")
        tc.configure_args.append("--disable-syscall")
        # Fix array-bounds warning in rtree.h RTREE_CACHE_CHECK_L2 macro
        # Set portable TMPDIR (HarmonyOS /tmp is read-only, E002)
        env = tc.environment()
        env.append("CFLAGS", "-Wno-array-bounds")
        tmpdir = os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        # Fix umask 077 issue on HarmonyOS HMFS before configure runs
        # umask 077 creates dirs with perms 2700 (drwx--S---) that can't be written to,
        # and chmod is ineffective (E046). umask 022 creates dirs with perms 2751 (works).
        # This affects both configure's own temp files and the config.status template.
        self._patch_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def _patch_configure_umask(self):
        """Replace umask 077 with umask 022 in configure script."""
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            return
        with open(configure, "r") as f:
            content = f.read()
        content = content.replace("(umask 077 && mktemp", "(umask 022 && mktemp")
        content = content.replace("(umask 077 && mkdir", "(umask 022 && mkdir")
        with open(configure, "w") as f:
            f.write(content)

    def package(self):
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install(target="install_lib_static" if not self.options.shared else "install_lib_shared")
        autotools.install(target="install_include")

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "jemalloc")
        self.cpp_info.libs = ["jemalloc"]
        self.cpp_info.includedirs = ["include", "include/jemalloc"]
        if not self.options.shared:
            self.cpp_info.defines = ["JEMALLOC_EXPORT="]
        # R32: Use in ("Linux", "OHOS") for platform checks
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs.extend(["pthread", "rt"])
