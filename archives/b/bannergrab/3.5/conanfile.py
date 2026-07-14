#!/usr/bin/env python3
"""Conan recipe for bannergrab 3.5 — banner grabbing tool.

BannerGrab performs connection, trigger and basic service information
collection. It connects to TCP/UDP services and collects banners.

Build system: simple Makefile (no configure script).
The Makefile respects CPPFLAGS, CFLAGS and LDFLAGS from the environment.
License: GPL-3.0
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, unzip, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain


class BannergrabConan(ConanFile):
    name = "bannergrab"
    version = "3.5"
    description = "BannerGrab - performs connection, trigger and basic service information collection"
    license = "GPL-3.0"
    homepage = "https://github.com/CiscoCXSecurity/bannergrab"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    # OpenSSL headers are bundled as openssl_headers.tar.gz (54 files from
    # OpenSSL 1.1.1w). The CI worker (uid 100) cannot read system-installed
    # OpenSSL at /storage/Users/currentUser/usr/local/ (perms 660/770).
    # Linking uses system OpenSSL 3.x shared libs at /usr/lib (world-readable).
    # The SSL API bannergrab uses is stable across 1.x→3.x.

    def export_sources(self):
        export_conandata_patches(self)
        # Copy bundled OpenSSL headers tarball to export sources folder
        import shutil
        src = os.path.join(self.recipe_folder, "openssl_headers.tar.gz")
        dst = os.path.join(self.export_sources_folder, "openssl_headers.tar.gz")
        if os.path.exists(src):
            shutil.copy2(src, dst)

    def layout(self):
        # Build in source directory — bannergrab's Makefile is in the source root
        self.folders.build = "."
        self.folders.generators = "."

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"OS {self.settings.os} not supported, requires Linux or OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Extract bundled OpenSSL headers into _openssl/ subdirectory
        unzip(self, "openssl_headers.tar.gz", "_openssl")

    def generate(self):
        # AutotoolsToolchain generates CC, CFLAGS, CPPFLAGS, LDFLAGS, etc.
        # R33: All flags come from Conan toolchain, no shell env vars in build()
        tc = AutotoolsToolchain(self)
        # Bundled OpenSSL headers (extracted in source())
        openssl_include = os.path.join(self.build_folder, "_openssl")
        tc.extra_cflags.append(f"-I{openssl_include}")
        # System OpenSSL 3.x libraries (world-readable in /usr/lib)
        tc.extra_ldflags.append("-L/usr/lib")
        # Embed RPATH so the binary finds libssl/libcrypto at runtime
        # without requiring LD_LIBRARY_PATH (fixes L2 smoke test)
        tc.extra_ldflags.append("-Wl,-rpath,/usr/lib")
        # E106: OHOS SDK lld depends on libxml2.so.16 which is not in
        # LD_LIBRARY_PATH. Use GNU ld instead to avoid the lld dependency.
        tc.extra_ldflags.append("-fuse-ld=/data/service/hnp/bin/ld")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # bannergrab uses a plain Makefile (no configure script)
        # R9: Use -j1, never -j$(nproc)
        # R33: CC, CPPFLAGS, CFLAGS, LDFLAGS come from Conan toolchain (conanbuildenv)
        self.run("make -j1")

    def package(self):
        # bannergrab is a CLI tool — copy binary and man page
        copy(self, "bannergrab", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "bannergrab.1", src=self.build_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

        # Sign ELF binary (HarmonyOS requires ELF signature for execution)
        bin_path = os.path.join(self.package_folder, "bin", "bannergrab")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool):
            import shutil
            import subprocess
            # Remove old signature if present
            subprocess.run([objcopy, "--remove-section", ".codesign", bin_path],
                           capture_output=True, timeout=10)
            # Sign with self-signed certificate
            tmp = bin_path + ".signed.tmp"
            for _attempt in range(3):
                r = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path,
                     "-outFile", tmp, "-selfSign", "1"],
                    capture_output=True, timeout=30)
                if r.returncode == 0 and os.path.exists(tmp):
                    shutil.move(tmp, bin_path)
                    break
                import time; time.sleep(1)
            else:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise ConanException(
                    f"ELF signing failed after 3 attempts for {bin_path}. "
                    f"Binary will not be executable on HarmonyOS."
                )
            os.chmod(bin_path, 0o755)

    def package_info(self):
        # bannergrab is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Declares runtime dependency on system OpenSSL
        self.cpp_info.system_libs = ["ssl", "crypto"]
        # System OpenSSL 3.x libraries are in /usr/lib (standard path).
        # RPATH already points there, but also set runenv for test_package.
        openssl_lib_dir = "/usr/lib"
        if os.path.isdir(openssl_lib_dir):
            self.runenv_info.append_path("LD_LIBRARY_PATH", openssl_lib_dir)
