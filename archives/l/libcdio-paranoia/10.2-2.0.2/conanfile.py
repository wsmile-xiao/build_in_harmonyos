#!/usr/bin/env python3
"""Conan recipe for libcdio-paranoia and the cd-paranoia CLI."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibcdioParanoiaConan(ConanFile):
    name = "libcdio-paranoia"
    version = "10.2-2.0.2"
    description = "CD audio extraction library and cd-paranoia command-line tool"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/libcdio/"
    url = "https://github.com/libcdio/libcdio-paranoia"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {
        "shared": False,
        "fPIC": True,
        "libcdio/*:shared": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libcdio-paranoia supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libcdio/2.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libcdio-paranoia's configure script discovers libcdio through pkg-config.
        PkgConfigDeps(self).generate()

        if str(self.settings.os) == "OHOS":
            # The published libcdio package contains libtool .la metadata with
            # the package's historical / prefix.  A libtool consumer then follows
            # that metadata to //lib/libcdio.la instead of the Conan archive.
            # Feed this build a private, .a-only dependency prefix instead of
            # mutating the dependency cache.
            dep = self.dependencies["libcdio"]
            dep_prefix = os.path.join(self.build_folder, "libcdio-dependency")
            copy(
                self,
                "*.a",
                src=os.path.join(dep.package_folder, "lib"),
                dst=os.path.join(dep_prefix, "lib"),
            )
            copy(
                self,
                "*",
                src=os.path.join(dep.package_folder, "include"),
                dst=os.path.join(dep_prefix, "include"),
                keep_path=True,
            )
            pc_dir = os.path.join(dep_prefix, "lib", "pkgconfig")
            os.makedirs(pc_dir, exist_ok=True)
            save(
                self,
                os.path.join(pc_dir, "libcdio.pc"),
                "\n".join([
                    f"prefix={dep_prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include",
                    "Name: libcdio",
                    "Description: Conan package: libcdio",
                    "Version: 2.3.0",
                    'Libs: -L"${libdir}" -liso9660 -ludf -lcdio',
                    'Cflags: -I"${includedir}"',
                    "",
                ]),
            )

        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.configure_args.extend([
            "--disable-example-progs",
            "--without-versioned-libs",
        ])
        # Static OHOS test/consumer binaries must not depend on a host runtime.
        if str(self.settings.os) == "OHOS":
            tc.extra_ldflags.append("-all-static")
        tc.generate()

    def _ohos_build_env(self):
        """Return a stable shell environment for Autotools on HMDFS."""
        env = dict(os.environ)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c", "clang")
        cxx = compiler_executables.get("cpp", "clang++")
        optimization = "-O0 -g" if str(self.settings.build_type) == "Debug" else "-O3"
        compiler_bin = os.path.dirname(cc) if os.path.isabs(cc) else ""
        path_prefix = [p for p in (compiler_bin, "/system/bin", "/usr/bin", "/bin") if p]
        if env.get("PATH"):
            path_prefix.append(env["PATH"])
        dep_lib = os.path.join(self.build_folder, "libcdio-dependency", "lib")
        dep_include = os.path.join(self.build_folder, "libcdio-dependency", "include")
        env.update({
            "CC": cc,
            "CXX": cxx,
            "CFLAGS": f"-fPIC {optimization}",
            "CXXFLAGS": f"-stdlib=libc++ -std=c++17 -fPIC {optimization}",
            "LDFLAGS": f"-L{dep_lib} -all-static",
            "CPPFLAGS": f"-DNDEBUG -I{dep_include}",
            "PKG_CONFIG_PATH": os.path.join(dep_lib, "pkgconfig") + os.pathsep + self.generators_folder,
            # The profile's bash wrapper can emit getcwd failures from Conan's
            # HMDFS cache.  The platform /bin/sh works for this release archive.
            "CONFIG_SHELL": "/bin/sh",
            "SHELL": "/bin/sh",
            "PATH": os.pathsep.join(path_prefix),
            "TMPDIR": os.path.join(self.build_folder, "tmp"),
        })
        os.makedirs(env["TMPDIR"], exist_ok=True)
        return env

    def _ohos_make(self, *args, env=None):
        subprocess.run(["make", "-j1", *args], cwd=self.build_folder, env=env, check=True)

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            env = self._ohos_build_env()
            # Reconstruct the generated arguments through the public
            # AutotoolsToolchain.configure_args property.  The configure
            # process itself needs an explicit cwd because HMDFS can reject
            # Conan's transient process cwd.
            tc = AutotoolsToolchain(self)
            if not self.options.shared:
                tc.configure_args.extend(["--enable-static", "--disable-shared"])
            tc.configure_args.extend([
                "--disable-example-progs",
                "--without-versioned-libs",
            ])
            subprocess.run(
                [os.path.join(self.source_folder, "configure"), *tc.configure_args],
                cwd=self.build_folder,
                env=env,
                check=True,
            )
            self._ohos_make(env=env)
            # Keep the complete upstream regression suite in the Conan build contract.
            self._ohos_make("check", env=env)
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            # Keep the complete upstream regression suite in the Conan build contract.
            autotools.make(target="check", args=["-j1"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            env = self._ohos_build_env()
            env["DESTDIR"] = self.package_folder
            self._ohos_make("install", env=env)
        else:
            autotools = Autotools(self)
            autotools.install()
        # Libtool archives contain build-machine absolute paths and are not needed
        # by Conan consumers once the static archives have been installed.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cdio_paranoia", "cdio_cdda"]
        self.cpp_info.requires = ["libcdio::libcdio"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libcdio-paranoia")
        self.cpp_info.set_property(
            "cmake_target_name", "libcdio-paranoia::libcdio-paranoia"
        )
        self.cpp_info.set_property("pkg_config_name", "libcdio_paranoia")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "rt"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
