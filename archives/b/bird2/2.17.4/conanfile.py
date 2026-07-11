#!/usr/bin/env python3
"""Conan recipe — bird2 2.17.4 (BIRD Internet Routing Daemon) for OHOS.

OHOS-specific adaptations:
  - config.guess/config.sub replaced for HarmonyOS platform recognition (E007)
  - autoconf + autoheader run before configure (source has configure.ac only)
  - -D__MUSL__ added to resolve sockaddr_storage conflict (bionic linux/socket.h)
  - OHOS SDK sysroot include paths for Linux UAPI kernel headers
  - --disable-client (ncurses headers not available on OHOS)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Bird2Conan(ConanFile):
    name = "bird2"
    version = "2.17.4"
    package_type = "application"
    description = "BIRD Internet Routing Daemon — dynamic IP routing daemon"
    license = "GPL-2.0-or-later"
    homepage = "https://bird.network.cz/"
    url = "https://gitlab.nic.cz/labs/bird"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # bird2 has no external Conan dependencies
        # R27: if dependencies are added, they must use @ohpcd/stable
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception as e:
            # Only fall back to curl for SSL-related failures (Python ssl module
            # unavailable). Re-raise all other errors including SHA256 mismatch.
            if "SSL" not in str(e) and "ssl" not in str(e):
                raise
            # curl has its own SSL support, independent of Python's ssl module.
            import hashlib
            url = self.conan_data["sources"]["url"]
            filename = os.path.basename(url)
            sha256_expected = self.conan_data["sources"]["sha256"]
            ret = self.run(f'curl -fSL -o "{filename}" "{url}"')
            if ret != 0:
                raise ConanException(f"curl download failed with exit code {ret}")
            # Verify SHA256 checksum
            h = hashlib.sha256()
            with open(filename, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            if h.hexdigest() != sha256_expected:
                raise ConanException(
                    f"SHA256 mismatch for {filename}: "
                    f"expected {sha256_expected}, got {h.hexdigest()}"
                )
            ret = self.run(f'tar xzf "{filename}" --strip-components=1')
            if ret != 0:
                raise ConanException(f"tar extraction failed with exit code {ret}")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R32: settings.os must be in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bird2 does not support {self.settings.os}"
            )

        # OHOS-specific: add -D__MUSL__ to resolve sockaddr_storage redefinition
        # conflict between sys/socket.h and linux/socket.h (bionic UAPI headers)
        if self.settings.os == "OHOS":
            tc.extra_cflags.append("-D__MUSL__")
            # R33: sysroot comes from Conan profile conf, not env vars
            sysroot = self.conf.get("tools.build:sysroot", default="", check_type=str)
            if sysroot:
                tc.extra_cflags.append(f"-I{sysroot}/usr/include")
                tc.extra_cflags.append(f"-I{sysroot}/usr/include/aarch64-linux-ohos")
                tc.extra_ldflags.append(f"-L{sysroot}/usr/lib")

            # Disable client (requires ncurses which is not available on OHOS)
            tc.configure_args.append("--disable-client")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: No shell environment variable dependencies
        # All compiler/flags come from Conan AutotoolsToolchain

        # E007: Replace config.guess/config.sub with OHOS-aware versions
        # The source ships old 2018-03-08 versions that don't recognize HarmonyOS
        tools_dir = os.path.join(self.source_folder, "tools")
        config_guess_path = os.path.join(tools_dir, "config.guess")
        config_sub_path = os.path.join(tools_dir, "config.sub")

        # Write a self-contained OHOS-aware config.guess
        ohos_config_guess = '''#!/bin/sh
# OHOS-aware config.guess (self-contained, replaces 2018-03-08 version)
machine=$(uname -m 2>/dev/null || echo unknown)
system=$(uname -s 2>/dev/null || echo unknown)
case "$system" in
    HarmonyOS|OHOS)
        echo "${machine}-unknown-linux-ohos"
        ;;
    Linux)
        echo "${machine}-unknown-linux-gnu"
        ;;
    Darwin)
        echo "${machine}-apple-darwin"
        ;;
    *)
        echo "${machine}-unknown-linux-gnu"
        ;;
esac
exit 0
'''
        with open(config_guess_path, "w") as f:
            f.write(ohos_config_guess)
        os.chmod(config_guess_path, 0o755)

        # Write a self-contained OHOS-aware config.sub
        ohos_config_sub = '''#!/bin/sh
# OHOS-aware config.sub (self-contained, replaces 2018-03-08 version)
# Always pass through the input triplet; exit 0 for any input
if [ $# -eq 0 ] || [ -z "$1" ]; then
    echo "aarch64-unknown-linux-ohos"
    exit 0
fi
echo "$1"
exit 0
'''
        with open(config_sub_path, "w") as f:
            f.write(ohos_config_sub)
        os.chmod(config_sub_path, 0o755)

        # Run autoconf to generate configure script (source has configure.ac only)
        ret = self.run("autoconf", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"autoconf failed with exit code {ret}")
        # Run autoheader to generate sysdep/autoconf.h.in
        ret = self.run("autoheader", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"autoheader failed with exit code {ret}")

        # Patch configure to replace umask 077 with umask 022
        # config.status (generated by configure) uses umask 077 which creates
        # temp dirs with 0700 perms, causing "Permission denied" on HMDFS
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            with open(configure_path, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(configure_path, "w") as f:
                f.write(content)

        autotools = Autotools(self)
        autotools.configure()

        # Also patch config.status (generated by configure) for safety
        # In out-of-source builds, config.status is in build_folder, not source_folder
        config_status = os.path.join(self.build_folder, "config.status")
        if os.path.exists(config_status):
            with open(config_status, "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 022")
            with open(config_status, "w") as f:
                f.write(content)
            # Re-run config.status to regenerate files with correct umask
            ret = self.run("./config.status", cwd=self.build_folder)
            if ret != 0:
                raise ConanException(f"config.status failed with exit code {ret}")

        autotools.make(args=["-j1"])

        # Copy test config files to build directory for make check.
        # filter_test uses relative path "filter/test.conf" to find config,
        # but in out-of-source builds these files are only in the source dir.
        filter_src = os.path.join(self.source_folder, "filter")
        filter_build = os.path.join(self.build_folder, "filter")
        if os.path.isdir(filter_src) and os.path.isdir(filter_build):
            copy(self, "test.conf*", filter_src, filter_build)

        # Run upstream official tests (CI gate requirement)
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # bird2 is a daemon, not a library — no cpp_info.libs needed
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
