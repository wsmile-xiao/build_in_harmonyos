#!/usr/bin/env python3
"""Conan recipe for COIN-OR Cut Generation Library (Cgl)."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps


class CglConan(ConanFile):
    name = "cgl"
    version = "0.60.10"
    description = "COIN-OR Cut Generation Library"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Cgl"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # Cgl public headers and its static archive expose the COIN-OR
        # dependency closure to downstream consumers.
        self.requires(
            "coinutils/2.11.13",
            transitive_headers=True,
            transitive_libs=True,
        )
        # ohpcd publishes Osi under the coin-or package name.
        self.requires(
            "coin-or/0.108.12",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "clp/1.17.10",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "zlib/1.3.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        # COIN-OR recursive configure does not support Conan's VPATH layout.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # Cgl's configure script discovers Osi as "osi", while the published
        # Conan package is named "coin-or".  Preserve the upstream identity.
        coin_or_pc = os.path.join(self.generators_folder, "coin-or.pc")
        osi_pc = os.path.join(self.generators_folder, "osi.pc")
        if os.path.isfile(coin_or_pc) and not os.path.exists(osi_pc):
            with open(coin_or_pc, encoding="utf-8") as source:
                version = next(
                    (line.split(":", 1)[1].strip() for line in source
                     if line.startswith("Version:")),
                    "0",
                )
            with open(osi_pc, "w", encoding="utf-8") as alias:
                alias.write(
                    "Name: osi\nDescription: Osi compatibility alias\n"
                    f"Version: {version}\nRequires: coin-or\n"
                )
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-dependency-tracking")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        src = self.source_folder
        coinutils = self.dependencies["coinutils"].package_folder
        osi = self.dependencies["coin-or"].package_folder
        clp = self.dependencies["clp"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        self.run(f"find '{src}' -type f \( -name configure -o -name config.guess -o -name config.sub -o -name install-sh -o -name ltmain.sh \) -exec chmod +x {{}} \\;")
        for root, _, files in os.walk(src):
            if "config.guess" in files:
                guess = os.path.join(root, "config.guess")
                self.run(r"sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' " + f"'{guess}'")
                self.run(r"sed -i '/^case \"${UNAME_SYSTEM}\" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' " + f"'{guess}'")
        self.run(
            f"cd '{src}' && TMPDIR='{tmpdir}' "
            f"CPPFLAGS='-I{coinutils}/include/coin -I{osi}/include/coin -I{clp}/include/coin' "
            f"./configure --prefix=/ "
            f"--build=aarch64-unknown-linux-musl --disable-dependency-tracking "
            f"--disable-shared --enable-static "
            f"--with-coinutils-incdir='{coinutils}/include/coin' "
            f"--with-coinutils-lib='{coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm' "
            f"--with-osi-incdir='{osi}/include/coin' "
            f"--with-osi-lib='{osi}/lib/libOsi.a {coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm' "
            f"--with-clp-incdir='{clp}/include/coin' "
            f"--with-clp-lib='{clp}/lib/libOsiClp.a {clp}/lib/libClpSolver.a {clp}/lib/libClp.a "
            f"{osi}/lib/libOsi.a {coinutils}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm'"
        )
        # HMDFS applies the SGID bit with umask 077, leaving config.status'
        # temporary directory inaccessible. Recreate generated Makefiles with
        # a stable writable directory and a compatible umask.
        for config_status in [
            os.path.join(src, "config.status"),
            os.path.join(src, "Cgl", "config.status"),
        ]:
            if os.path.isfile(config_status):
                self.run(
                    f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' "
                    f"'{config_status}'"
                )
                self.run(
                    f"sed -i 's|tmp=\\./confstat\\$\\$$-\\$RANDOM|tmp=./conftmp|' "
                    f"'{config_status}'"
                )
                self.run(f"sed -i 's|umask 077|umask 022|g' '{config_status}'")
                status_dir = os.path.dirname(config_status)
                self.run(
                    f"cd '{status_dir}' && mkdir -p conftmp && "
                    f"TMPDIR='{tmpdir}' sh config.status"
                )
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 check")
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 test")

    def package(self):
        src = self.source_folder
        self.run(f"find '{src}' -name install-sh -type f -exec chmod +x {{}} \\;")
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 install DESTDIR='{self.package_folder}'")

    def package_info(self):
        self.cpp_info.includedirs = ["include/coin"]
        self.cpp_info.libs = ["Cgl"]
