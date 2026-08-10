#!/usr/bin/env python3
"""Conan recipe — Privoxy 4.0.0-r0

Privoxy is a non-caching web proxy with advanced filtering capabilities
for enhancing privacy, modifying web page data and HTTP headers,
filtering ads, and more.

Build system: autotools (autoconf + configure + make)
  Source tarball contains configure.in (not pre-generated configure),
  so autoheader + autoconf must run first.

License: GPL-2.0-or-later
Homepage: https://www.privoxy.org/
"""
import os
import shlex
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PrivoxyConan(ConanFile):
    name = "privoxy"
    version = "4.0.0-r0"
    description = "Privoxy — a privacy-enhancing web proxy with advanced filtering capabilities"
    license = "GPL-2.0-or-later"
    homepage = "https://www.privoxy.org/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pcre2/10.45.1")
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = Environment()

        if self.settings.os == "OHOS":
            # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
            # causing config.status to fail writing subs*.awk. Create a mktemp wrapper
            # that returns failure to force autoconf AS_TMPDIR to use mkdir fallback.
            wrapper_dir = Path(self.build_folder) / ".hmos_fix"
            wrapper_dir.mkdir(exist_ok=True)
            wrapper = wrapper_dir / "mktemp"
            wrapper.write_text(
                '#!/system/bin/sh\n'
                '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
                '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
                'exit 1\n'
            )
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)
            env.prepend_path("PATH", str(wrapper_dir))

        tc = AutotoolsToolchain(self)
        # OHOS: config.guess doesn't recognize OHOS, force build triplet
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # Privoxy-specific configure options
        tc.configure_args.append("--enable-zlib")
        tc.configure_args.append("--enable-dynamic-pcre")
        tc.configure_args.append("--localstatedir=var")
        tc.configure_args.append("--sysconfdir=etc/privoxy")
        tc.configure_args.append("--docdir=share/doc/privoxy")
        tc.generate()

        # E001: Explicitly set CC/CXX from Conan conf (no cc symlink on OHOS)
        # Also add dependency paths for configure to find pcre2 and zlib
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        env.define("CC", cc)
        env.define("CXX", cxx)
        # Add dependency include/lib paths so configure can find pcre2 and zlib
        for dep in self.dependencies.values():
            for incdir in dep.cpp_info.includedirs:
                env.append("CPPFLAGS", f"-I{incdir}")
            for libdir in dep.cpp_info.libdirs:
                env.append("LDFLAGS", f"-L{libdir}")
        env.vars(self).save_script("env_cc_cxx")

    def build(self):
        apply_conandata_patches(self)

        # Source tarball has configure.in but no configure script.
        # autoconf 2.72 requires configure.ac naming.
        self.run("test -f configure.in && ! test -f configure.ac && mv configure.in configure.ac || true",
                 env="conanbuild", cwd=self.source_folder)
        # Generate config.h.in and configure script
        self.run("autoheader", env="conanbuild", cwd=self.source_folder)
        self.run("autoconf", env="conanbuild", cwd=self.source_folder)

        prefix = self.package_folder
        is_ohos = self.settings.os == "OHOS"

        if is_ohos:
            # E165: Fix shebangs for OHOS (no /bin/sh or /bin/bash)
            for script in ["configure", "install-sh"]:
                path = os.path.join(self.source_folder, script)
                if os.path.isfile(path):
                    replace_in_file(self, path, "#!/bin/sh", "#!/data/service/hnp/bin/bash", strict=False)
                    replace_in_file(self, path, "#!/bin/bash", "#!/data/service/hnp/bin/bash", strict=False)
                    st = os.stat(path)
                    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)

            # E046: On OHOS, chmod may not work (SELinux/MAC).
            # Run configure through bash explicitly instead of direct execution.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            configure_path = os.path.join(self.source_folder, "configure")
            configure_args = [
                f"--prefix={prefix}",
                "--bindir=${prefix}/bin",
                "--sbindir=${prefix}/bin",
                "--libdir=${prefix}/lib",
                "--includedir=${prefix}/include",
                "--oldincludedir=${prefix}/include",
                "--build=aarch64-unknown-linux-gnu",
                "--enable-zlib",
                "--enable-dynamic-pcre",
                f"--localstatedir={prefix}/var",
                f"--sysconfdir={prefix}/etc/privoxy",
                f"--docdir={prefix}/share/doc/privoxy",
            ]
            args_str = " ".join(shlex.quote(a) for a in configure_args)
            self.run(f'{bash} "{configure_path}" {args_str}', env="conanbuild", cwd=self.source_folder)
        else:
            autotools = Autotools(self)
            autotools.configure()

        # Make - run in source_folder where GNUmakefile was generated
        self.run("make -j1", env="conanbuild", cwd=self.source_folder)

    def package(self):
        # STRIP="" avoids ginstall treating llvm-strip as a file argument
        self.run("make install STRIP=", env="conanbuild", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
