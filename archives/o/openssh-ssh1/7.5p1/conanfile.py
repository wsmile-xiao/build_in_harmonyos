#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpenSshSsh1Conan(ConanFile):
    name = "openssh-ssh1"
    version = "7.5p1"
    description = "Portable OpenSSH SSH1-compatible release"
    license = "BSD-2-Clause"
    homepage = "https://www.openssh.com/portable.html"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/1.1.1w")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is only supported on Linux/OHOS"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"{self.name} currently supports OHOS armv8 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The OpenSSL 1.1 accessor backport is a vendor-style patch whose hunks
        # apply cleanly with git's context matcher. Conan's patch helper is more
        # restrictive about the old 7.5p1 line offsets, so keep git apply here.
        for p in self.conan_data.get("patches", []):
            patch_file = os.path.join(self.source_folder, p["patch_file"])
            self.run(
                f"git apply --whitespace=nowarn -p1 '{patch_file}'",
                cwd=self.source_folder,
            )

    def _compiler_executable(self, language, fallback):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        return compilers.get(language, fallback)

    def _ohos_make_args(self):
        if self.settings.os != "OHOS":
            return []
        cc = self._compiler_executable("c", "clang")
        return [
            f'LD="{cc}"',
            f'CCLD="{cc}"',
            'LIBS="-lcrypto -lz"',
        ]

    def generate(self):
        tc = AutotoolsToolchain(self)
        zlib_root = self.dependencies["zlib"].package_folder
        openssl_root = self.dependencies["openssl"].package_folder

        tc.configure_args.extend([
            "--prefix=/",
            "--sysconfdir=/etc/ssh",
            "--libexecdir=/libexec",
            "--with-ssh1",
            f"--with-zlib={zlib_root}",
            f"--with-ssl-dir={openssl_root}",
            "--with-sandbox=no",
            "--without-zlib-version-check",
            "--without-openssl-header-check",
            "--disable-utmp",
            "--disable-utmpx",
            "--disable-wtmp",
            "--disable-wtmpx",
            "--disable-lastlog",
        ])

        if self.settings.os == "OHOS":
            # AutotoolsToolchain does not inject OHOS build/host triplets here,
            # while upstream config.sub does not know HarmonyOS uname output.
            # The linux-ohos triplet works together with 0001-config.sub patch.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
            tc.configure_args.append("ac_cv_header_linux_if_tun_h=no")
            # OHOS ships <shadow.h> with struct spwd but without getspnam, so
            # force the shadow header probe off and keep xcrypt on pw_passwd.
            tc.configure_args.append("ac_cv_header_shadow_h=no")
            # OHOS has no separate libcrypt. Also avoid configure carrying
            # -lcrypt into Makefile LIBS; build() overrides LIBS for legacy
            # OpenSSH link rules that invoke $(LD) directly.
            tc.configure_args.append("ac_cv_search_crypt=no")
            tc.configure_args.append("ac_cv_lib_crypt_crypt=no")
            tc.extra_cflags.append("-D_GNU_SOURCE")
            tc.extra_cflags.append("-D__USE_GNU")

        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=self._ohos_make_args())
        # Upstream make tests were compile-checked on device after the OpenSSL
        # accessor backport, banana typo patch, and serialized make. Runtime
        # execution hits OHOS tmpfile()/read-only /tmp behavior, so this recipe
        # relies on the Conan test_package functional SSH1 assertions instead.

    def package(self):
        autotools = Autotools(self)
        autotools.make(
            target="install-nokeys",
            args=[f"DESTDIR={self.package_folder}", *self._ohos_make_args()],
        )
        copy(
            self,
            "LICENCE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )
