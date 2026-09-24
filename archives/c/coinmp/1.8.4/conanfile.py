#!/usr/bin/env python3
"""Conan recipe for COIN-OR CoinMP 1.8.4 - OpenHarmony aarch64 port.

CoinMP is the C-API interface library for CLP, CBC and CGL.  Autotools
build; its configure probes Cbc via pkg-config (`cbc`, `clp`, `osi-clp`),
and the Cbc dependency closure (CoinUtils, Osi/coin-or, Clp, Cgl, zlib)
is pulled in transitively from the published cbc/2.10.13 package.
"""

import glob
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps


class CoinmpConan(ConanFile):
    name = "coinmp"
    version = "1.8.4"
    description = "COIN-OR C-API interface library for CLP, CBC and CGL"
    topics = ("coin-or", "coinmp", "lp", "milp", "solver")
    url = "https://github.com/coin-or/CoinMP"
    homepage = "https://github.com/coin-or/CoinMP"
    license = "EPL-2.0"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # CoinMP public headers and its static archive expose the COIN-OR
        # dependency closure to downstream consumers, so every member of the
        # closure is a direct (public/transitive) requirement.  The same
        # layout is used by the published cbc/2.10.13 recipe.
        self.requires("cbc/2.10.13", transitive_headers=True, transitive_libs=True)
        self.requires("coinutils/2.11.13", transitive_headers=True, transitive_libs=True)
        self.requires("coin-or/0.108.12", transitive_headers=True, transitive_libs=True)
        self.requires("clp/1.17.10", transitive_headers=True, transitive_libs=True)
        self.requires("cgl/0.60.10.1", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        # COIN-OR recursive configure does not support Conan's VPATH layout.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()

        # CoinMP's configure probes Cbc as "cbc", Clp as "clp" and OsiClp
        # as "osi-clp" (AC_COIN_CHECK_PACKAGE(Cbc, [cbc clp osi-clp])).
        # The published packages only export "coin-or" and "clp" .pc files,
        # so write the same compatibility aliases as cgl/0.60.10.1, clp and
        # cbc recipes.
        coin_or_pc = os.path.join(self.generators_folder, "coin-or.pc")
        osi_pc = os.path.join(self.generators_folder, "osi.pc")
        if os.path.isfile(coin_or_pc) and not os.path.exists(osi_pc):
            with open(coin_or_pc, encoding="utf-8") as fh:
                version = next(
                    (line.split(":", 1)[1].strip() for line in fh
                     if line.startswith("Version:")),
                    "0",
                )
            with open(osi_pc, "w", encoding="utf-8") as fh:
                fh.write(
                    "Name: osi\nDescription: Osi compatibility alias\n"
                    f"Version: {version}\nRequires: coin-or\n"
                )
        clp_pc = os.path.join(self.generators_folder, "clp.pc")
        osi_clp_pc = os.path.join(self.generators_folder, "osi-clp.pc")
        if os.path.isfile(clp_pc) and not os.path.exists(osi_clp_pc):
            with open(clp_pc, encoding="utf-8") as fh:
                version = next(
                    (line.split(":", 1)[1].strip() for line in fh
                     if line.startswith("Version:")),
                    "0",
                )
            with open(osi_clp_pc, "w", encoding="utf-8") as fh:
                fh.write(
                    "Name: OsiClp\nDescription: OsiClp compatibility alias\n"
                    f"Version: {version}\nRequires: clp\n"
                )

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-musl",
            "--host=aarch64-unknown-linux-musl",
            "--disable-dependency-tracking",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # This OHOS port targets aarch64 (armv8) with the clang 15 toolchain;
        # arch-dependent configure flags (--build/--host=...) assume arm64.
        tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        src = self.source_folder

        self.run(
            "find '%s' -type f \\( -name configure -o -name config.guess "
            "-o -name config.sub -o -name install-sh -o -name ltmain.sh \\) "
            "-exec chmod +x {} \\;" % src
        )
        # CoinMP 1.8.4 ships config.sub (2019-02-24) that does not recognise
        # the aarch64-unknown-linux-musl triplet used for OHOS builds.
        # Minimal fix: accept `-musl*` as a valid OS component (same spirit
        # as the config.guess HarmonyOS injection used by cbc/cgl recipes).
        for sub in (
            os.path.join(src, "config.sub"),
            os.path.join(src, "CoinMP", "config.sub"),
        ):
            if not os.path.isfile(sub):
                continue
            with open(sub, encoding="utf-8") as fh:
                text = fh.read()
            new_text = text.replace(
                "  nto-qnx* | linux-gnu* | linux-dietlibc | linux-newlib* "
                "| linux-uclibc* | \\",
                "  nto-qnx* | linux-gnu* | linux-musl* | linux-dietlibc "
                "| linux-newlib* | linux-uclibc* | \\",
            ).replace(
                "      | -mingw32* | -linux-gnu* | -linux-newlib* "
                "| -linux-uclibc* \\",
                "      | -mingw32* | -linux-gnu* | -linux-musl* "
                "| -linux-newlib* | -linux-uclibc* \\",
            )
            if new_text != text:
                with open(sub, "w", encoding="utf-8") as fh:
                    fh.write(new_text)
                self.output.info("config.sub: added linux-musl* support")
        # HMDFS applies umask 077: configure's confstat temp dir becomes
        # inaccessible. Patch configure scripts to a permissive umask.
        for configure in (
            os.path.join(src, "configure"),
            os.path.join(src, "CoinMP", "configure"),
        ):
            if os.path.isfile(configure):
                self.run(f"sed -i 's|umask 077|umask 022|g' '{configure}'")

        # --- configure -----------------------------------------------------
        # CoinMP's configure probes Cbc through pkg-config (cbc, clp, osi-clp)
        # and, like cbc/clp/cgl, needs explicit dependency library paths so
        # libtool never resolves the published packages' .la files (whose
        # libdir='//lib' is invalid in a clean CI build).
        cbc = self.dependencies["cbc"].package_folder
        clp = self.dependencies["clp"].package_folder
        osi = self.dependencies["coin-or"].package_folder
        cgl = self.dependencies["cgl"].package_folder
        cu = self.dependencies["coinutils"].package_folder
        zlib = self.dependencies["zlib"].package_folder

        command = (
            f"cd '{src}' && TMPDIR='{tmpdir}' "
            f"PKG_CONFIG_PATH='{self.generators_folder}' "
            f"CPPFLAGS='-I{cbc}/include/coin -I{clp}/include/coin "
            f"-I{osi}/include/coin -I{cgl}/include/coin "
            f"-I{cu}/include/coin' "
            f"./configure --prefix=/ "
            f"--build=aarch64-unknown-linux-musl "
            f"--host=aarch64-unknown-linux-musl "
            f"--disable-dependency-tracking "
            f"--disable-shared --enable-static "
            f"--with-cbc-incdir='{cbc}/include/coin' "
            f"--with-cbc-lib='{cbc}/lib/libOsiCbc.a {cbc}/lib/libCbcSolver.a "
            f"{cbc}/lib/libCbc.a {clp}/lib/libOsiClp.a {clp}/lib/libClpSolver.a "
            f"{clp}/lib/libClp.a {cgl}/lib/libCgl.a {osi}/lib/libOsi.a "
            f"{cu}/lib/libCoinUtils.a {zlib}/lib/libz.a -lm'"
        )
        self.run(command)

        # HMDFS umask 077 + SGID: configure's confstat temp dir becomes
        # inaccessible; regenerate config.status with a stable writable dir
        # and permissive umask (same fix as cgl/0.60.10.1 and cbc/2.10.13).
        for config_status in [
            os.path.join(src, "config.status"),
            os.path.join(src, "CoinMP", "config.status"),
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

        # libtool refuses dependency packages' .la files (libdir='//lib'
        # invalid in clean CI cache). Replace -l* flags with absolute .a
        # paths in the generated Makefiles (same fix as cbc/2.10.13).
        self.run(
            "find '%s' -name Makefile -exec sed -i "
            "'s|-lCbcSolver|%s/lib/libCbcSolver.a|g; "
            "s|-lOsiCbc|%s/lib/libOsiCbc.a|g; "
            "s|-lClpSolver|%s/lib/libClpSolver.a|g; "
            "s|-lOsiClp|%s/lib/libOsiClp.a|g; "
            "s|-lClp|%s/lib/libClp.a|g; "
            "s|-lCgl|%s/lib/libCgl.a|g; "
            "s|-lOsi|%s/lib/libOsi.a|g; "
            "s|-lCoinUtils|%s/lib/libCoinUtils.a|g; "
            "s|-lz|%s/lib/libz.a|g' {} \\;"
            % (src, cbc, cbc, clp, clp, clp, cgl, osi, cu, zlib)
        )

        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 check")

    def package(self):
        src = self.source_folder
        self.run(f"find '{src}' -name install-sh -type f -exec chmod +x {{}} \\;")
        self.run(
            f"cd '{src}' && MAKEFLAGS='' make -j1 install DESTDIR='{self.package_folder}'"
        )
        # Drop libtool .la files: their hardcoded libdir breaks consumers.
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "coinmp")
        self.cpp_info.libs = ["CoinMP"]
        self.cpp_info.includedirs = [os.path.join("include", "coin")]
        # CoinMP public headers include headers from Cgl/Clp/Osi/CoinUtils by
        # bare name; pass the dependency include dirs through so consumers
        # can compile against the installed public headers.
        for dep in ("cbc", "coinutils", "coin-or", "clp", "cgl"):
            inc = os.path.join(self.dependencies[dep].package_folder,
                               "include", "coin")
            if os.path.isdir(inc) and inc not in self.cpp_info.includedirs:
                self.cpp_info.includedirs.append(inc)
        self.cpp_info.requires = [
            "cbc::cbc",
            "coinutils::coinutils",
            "coin-or::coin-or",
            "clp::clp",
            "cgl::cgl",
            "zlib::zlib",
        ]
