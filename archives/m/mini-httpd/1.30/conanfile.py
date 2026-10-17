"""Conan recipe for mini-httpd 1.30 (ACME Labs mini_httpd + htpasswd).

Upstream ships a bare Makefile (no configure, no test suite). SSL support is
opt-in (USE_SSL, left off). The Makefile defaults LDFLAGS to `-s`; the strip
is dropped on purpose because stripping removes the linker-embedded
.codesign section and the binary then fails OHOS XPM execution (E077).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MiniHttpdConan(ConanFile):
    name = "mini-httpd"
    version = "1.30"
    description = "mini_httpd: tiny HTTP server with htpasswd utility (ACME Labs)"
    license = "BSD-3-Clause"
    homepage = "https://www.acme.com/software/mini_httpd/"
    url = ""
    topics = ("http", "server", "web", "htpasswd")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mini-httpd supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_c(self):
        # R33: take the compiler from the Conan profile, never from ${CC}.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return executables.get("c") or "clang"

    def generate(self):
        env = Environment()
        env.define("CC", self._compiler_c())
        env.vars(self).save_script("conanbuild_cc")

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler_c()
        cflags = "-O2 -fPIE -D_GNU_SOURCE"
        ldflags = "-pie -Wl,-z,relro,-z,now"
        # musl keeps the resolver and sockets in libc; CRYPT_LIB (-lcrypt) is
        # kept at the upstream default for htpasswd/mini_httpd crypt().
        self.run(
            f'make CC="{cc}" CFLAGS="{cflags}" LDFLAGS="{ldflags}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        sf = self.source_folder
        copy(self, "mini_httpd", sf, os.path.join(self.package_folder, "bin"))
        copy(self, "htpasswd", sf, os.path.join(self.package_folder, "bin"))
        for f in ("mini_httpd", "htpasswd"):
            os.chmod(os.path.join(self.package_folder, "bin", f), 0o755)
        copy(self, "mini_httpd.8", sf, os.path.join(self.package_folder, "man", "man8"))
        copy(self, "htpasswd.1", sf, os.path.join(self.package_folder, "man", "man1"))
        copy(self, "README", sf, os.path.join(self.package_folder, "licenses"))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # E077: HarmonyOS XPM requires signed executables; the hnp tools
        # resolve libc++ via their own location, so LD_LIBRARY_PATH pointing
        # at SDK/llvm libs must not leak into the signer invocation.
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in sorted(glob.glob(os.path.join(self.package_folder, "bin", "*"))):
            if not os.path.isfile(f) or os.path.islink(f) or not self._is_elf(f):
                continue
            self.run(
                'env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f)
            )
            self.run(
                'env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f)
            )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
