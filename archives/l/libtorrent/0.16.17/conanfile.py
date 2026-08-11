#!/usr/bin/env python3
"""Conan recipe for Rakshasa libtorrent 0.16.17 on HarmonyOS."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    replace_in_file,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibtorrentConan(ConanFile):
    name = "libtorrent"
    version = "0.16.17"
    description = "High-performance BitTorrent library used by rTorrent"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rakshasa/libtorrent"
    url = "https://github.com/rakshasa/libtorrent"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        # Upstream's configure.ac makes C++20 mandatory.
        self.settings.compiler.cppstd = "20"

        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libtorrent supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Match curl's exact transitive versions to keep one dependency graph.
        self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)
        self.requires(
            "openssl/3.5.6.1", transitive_headers=True, transitive_libs=True
        )
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.test_requires("cppunit/1.15.1")

    def build_requirements(self):
        # GitHub tag archives do not include the generated configure script.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # configure.ac discovers all four target libraries through pkg-config.
        self.dependencies["openssl"].cpp_info.components["crypto"].set_property(
            "pkg_config_name", "libcrypto"
        )
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC", False):
                tc.extra_cxxflags.append("-fPIC")

        if self.settings.build_type == "Debug":
            tc.configure_args.append("--enable-debug")
        else:
            tc.configure_args.append("--disable-debug")

        if self.settings.os == "OHOS":
            # config.guess does not recognize HarmonyOS; config.sub from
            # automake canonicalizes this explicit triplet correctly.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
            # OHOS uses musl even though its native triplet does not contain
            # "musl"; keep worker threads off the libc default small stack.
            tc.configure_args.append("--enable-pthread-setstacksize")
            # execinfo is optional and is not consistently exposed by OHOS.
            tc.configure_args.append("--disable-execinfo")
            # The device's HMDFS workspace cannot create symbolic links. Keep
            # the unrelated directory-event tests enabled and exempt only the
            # test whose sole purpose is validating symlink callback paths.
            tc.extra_cxxflags.append("-DLIBTORRENT_TEST_NO_SYMLINK")
        tc.generate()
        if self.settings.os == "OHOS":
            self._generate_autoreconf_environment()

    def _generate_autoreconf_environment(self):
        automake_root = self.dependencies.build["automake"].package_folder
        libtool_root = self.dependencies.build["libtool"].package_folder
        if not automake_root or not libtool_root:
            raise ConanException("Autotools build-tool packages are unavailable")

        perl = shutil.which("perl") or "perl"
        shell = shutil.which("bash") or shutil.which("sh") or "sh"

        automake_bin = os.path.join(automake_root, "bin")
        automake_data = os.path.join(
            automake_root, "share", "automake-1.18"
        )
        aclocal_data = os.path.join(automake_root, "share", "aclocal")
        aclocal_versioned = os.path.join(
            automake_root, "share", "aclocal-1.18"
        )
        libtoolize = os.path.join(libtool_root, "bin", "libtoolize")
        libtool_share = os.path.join(libtool_root, "share")
        libtool_sources = {
            "build-aux": os.path.join(libtool_share, "libtool", "build-aux"),
            "libltdl": os.path.join(libtool_share, "libtool", "libltdl"),
            "m4": os.path.join(libtool_share, "aclocal"),
        }
        libtool_data = os.path.join(self.generators_folder, "libtool-data")
        required = [
            os.path.join(automake_bin, ".aclocal-real"),
            os.path.join(automake_bin, ".automake-real"),
            automake_data,
            aclocal_data,
            aclocal_versioned,
            libtoolize,
            *libtool_sources.values(),
        ]
        missing = [path for path in required if not os.path.exists(path)]
        if missing:
            raise ConanException(
                "Autotools package content is missing: " + ", ".join(missing)
            )

        if os.path.isdir(libtool_data):
            shutil.rmtree(libtool_data)
        os.makedirs(libtool_data)
        for name, source in libtool_sources.items():
            shutil.copytree(
                source, os.path.join(libtool_data, name), symlinks=False
            )

        env = Environment()
        env.define(
            "ACLOCAL",
            shlex.join(
                [
                    perl,
                    os.path.join(automake_bin, ".aclocal-real"),
                    "--automake-acdir=" + aclocal_versioned,
                    "--system-acdir=" + aclocal_data,
                ]
            ),
        )
        env.define(
            "AUTOMAKE",
            shlex.join(
                [
                    perl,
                    os.path.join(automake_bin, ".automake-real"),
                    "--libdir=" + automake_data,
                ]
            ),
        )
        env.define("LIBTOOLIZE", shlex.join([shell, libtoolize]))
        env.prepend_path("PERL5LIB", automake_data)
        env.prepend_path("ACLOCAL_PATH", aclocal_versioned)
        env.prepend_path("ACLOCAL_PATH", aclocal_data)
        env.prepend_path(
            "ACLOCAL_PATH", os.path.join(libtool_root, "share", "aclocal")
        )
        env.define_path("_lt_pkgdatadir", libtool_data)
        env.vars(self).save_script("libtorrent_autoreconf")

    def build(self):
        apply_conandata_patches(self)
        build_env = ["conanbuild"]
        if self.settings.os == "OHOS":
            build_env.append("libtorrent_autoreconf")
        self.run(
            "autoreconf --install --force --verbose",
            cwd=self.source_folder,
            env=build_env,
        )
        if self.settings.os == "OHOS":
            # HMDFS setgid semantics make Autoconf's mode-0700 temporary
            # directories unwritable by the process that runs config.status.
            replace_in_file(
                self, os.path.join(self.source_folder, "configure"),
                "umask 077", "umask 022",
            )

        autotools = Autotools(self)
        self._configure(autotools)
        autotools.make(args=["-j1"])
        if can_run(self):
            test_args = ["-j1"]
            if self.settings.os == "OHOS":
                # HMDFS rejects a libtool wrapper's shebang interpreter even
                # though the same shell works when invoked explicitly.
                shell = shutil.which("bash") or shutil.which("sh") or "sh"
                test_args.append("TESTS_ENVIRONMENT=" + shlex.quote(shell))
            with self._test_environment().vars(self).apply():
                autotools.make(target="check", args=test_args)
        else:
            self.output.info("Cross-building: upstream CppUnit tests skipped")

    def _configure(self, autotools):
        if self.settings.os != "OHOS":
            autotools.configure()
            return

        shell = shutil.which("bash") or shutil.which("sh") or "sh"
        configure = os.path.join(self.source_folder, "configure")
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        command = "{} {} {}".format(
            shlex.quote(shell),
            shlex.quote(configure),
            configure_args,
        ).strip()
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def _test_environment(self):
        env = Environment()
        if self.settings.os == "Windows":
            loader_path = "PATH"
        else:
            loader_path = "LD_LIBRARY_PATH"
        for dependency in self.dependencies.values():
            cpp_info = dependency.cpp_info.aggregated_components()
            for libdir in cpp_info.libdirs:
                env.prepend_path(loader_path, libdir)
        return env

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["torrent"]
        self.cpp_info.set_property("cmake_file_name", "libtorrent")
        self.cpp_info.set_property("cmake_target_name", "libtorrent::torrent")
        self.cpp_info.set_property("pkg_config_name", "libtorrent")
