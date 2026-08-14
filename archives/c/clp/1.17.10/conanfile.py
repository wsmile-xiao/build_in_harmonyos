#!/usr/bin/env python3
"""Conan recipe — Clp (COIN-OR Linear Programming) 1.17.10.

Autotools project. 上游 Depends on coinutils and osi，但两者未发布到制品仓，
本配方不声明依赖（同 klystrack 删 sdl2_image 逻辑），构建时需自带或 CI worker 预装。
"""
import os
from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
# basic_layout removed: layout() uses pass for in-source build (coin-or style)


class ClpConan(ConanFile):
    name = "clp"
    version = "1.17.10"
    description = "COIN-OR Linear Programming solver"
    license = "EPL-2.0"
    homepage = "https://github.com/coin-or/Clp"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Clp public headers include CoinUtils headers, and its static archives
        # require both CoinUtils and Osi.  Propagate this public dependency
        # closure to CMakeDeps consumers.
        self.requires(
            "coinutils/2.11.13",
            transitive_headers=True,
            transitive_libs=True,
        )
        # The published Osi recipe is named coin-or.  Its library and upstream
        # pkg-config identity remain Osi/osi, so generate() adds the alias.
        self.requires(
            "coin-or/0.108.12",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        # In-source build: COIN-OR recursive configure (top-level + Clp/ subdir)
        # does not tolerate out-of-source builds on HMDFS (same as coin-or/0.108.12).
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
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
        # R26: System-name libraries default to static; respect the shared option
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.extra_cflags.append("-fPIC")
        tc.extra_cxxflags.append("-fPIC")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS workaround: set TMPDIR to a writable location under home
        _tmpdir = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(_tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        # E072: config.guess maps HarmonyOS→Linux (coinutils/2.11.13 style sed).
        # config.sub needs no patch: once config.guess yields aarch64-unknown-linux-musl,
        # config.sub already accepts linux-musl.
        for root, dirs, files in os.walk(self.source_folder):
            if "config.guess" in files:
                path = os.path.join(root, "config.guess")
                self.run(r"""sed -i '/^case $UNAME_SYSTEM in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{path}'")
                self.run(r"""sed -i '/^case "${UNAME_SYSTEM}" in$/a\    HarmonyOS|HongMeng) UNAME_SYSTEM=Linux; LIBC=musl;;' """ + f"'{path}'")
                self.output.info(f"patched config.guess: {path}")
        # Dependency paths for configure (--with-coinutils-* / --with-osi-* / --with-clp-lib)
        _cu = self.dependencies["coinutils"]
        _cu_dir = _cu.package_folder
        _zl = self.dependencies["zlib"]
        _zl_dir = _zl.package_folder
        _osi = self.dependencies["coin-or"]
        _osi_dir = _osi.package_folder
        # Conan copies strip_root=True sources into build_folder/src/ (layout pass).
        # COIN-OR recursive configure lives under that src/ subdir.
        src = os.path.join(self.source_folder, "src")
        if not os.path.exists(os.path.join(src, "configure")):
            src = self.source_folder  # fallback if layout differs
        _shared = self.options.shared
        _static_flag = "--disable-shared" if not _shared else "--enable-shared"
        _shared_flag = "--enable-static" if not _shared else "--disable-static"
        # E165: Conan copy() drops executable bits on HMDFS — restore them.
        self.run(f"chmod +x '{src}/configure' '{src}/Clp/configure' "
                 f"'{src}/config.guess' '{src}/config.sub' "
                 f"'{src}/install-sh' '{src}/ltmain.sh' 2>/dev/null; true")
        # Build manually (same approach as coin-or/0.108.12 recipe): Conan's
        # Autotools.configure() looks for configure at the build folder root, but
        # COIN-OR recursive configure lives under source_folder.  Avoid HMDFS
        # config.status temp-file issues by pointing TMPDIR to $HOME/tmp.
        self.run(f"cd '{src}' && "
                 f"TMPDIR={_tmpdir} "
                 f"./configure --prefix=/ "
                 f"--build=aarch64-unknown-linux-musl "
                 f"{_static_flag} {_shared_flag} --disable-dependency-tracking "
                 f"--with-coinutils-incdir={_cu_dir}/include/coin "
                 # Link the archives by absolute path.  Passing -L... -lOsi
                 # makes libtool reopen coin-or's libOsi.la, whose generated
                 # dependency_libs contains the invalid //lib/libCoinUtils.la
                 # path on the OHOS package layout.
                 f"--with-coinutils-lib='{_cu_dir}/lib/libCoinUtils.a {_zl_dir}/lib/libz.a -lm' "
                 f"--with-osi-incdir={_osi_dir}/include/coin "
                 f"--with-osi-lib='{_osi_dir}/lib/libOsi.a {_cu_dir}/lib/libCoinUtils.a {_zl_dir}/lib/libz.a -lm'")
        # Patch all config.status files (root + Clp subdir) to fix HMDFS umask issue
        for cs in ["config.status", "Clp/config.status"]:
            csp = os.path.join(src, cs)
            if os.path.exists(csp):
                self.run(f"sed -i 's|mktemp -d -q \"\\./confstatXXXXXX\"|mkdir -p ./conftmp|' '{csp}'")
                self.run(f"sed -i 's|tmp=\\./confstat\\$\\$$-\\$RANDOM|tmp=./conftmp|' '{csp}'")
                self.run(f"sed -i 's|umask 077|umask 022|g' '{csp}'")
                self.run("sed -i 's|`mkdir -p \\./conftmp`|./conftmp|' '%s'" % csp)
                self.run(f"sed -i 's|tmp=\\`(umask 022 \\&\\& mkdir -p ./conftmp) 2>/dev/null\\`|tmp=`(umask 022 \\&\\& mkdir -p ./conftmp \\&\\& echo ./conftmp) 2>/dev/null`|' '{csp}'")
                self.run(f"cd '{os.path.dirname(csp)}' && "
                         f"rm -rf conftmp confstat* && "
                         f"TMPDIR={_tmpdir} && "
                         f"sh config.status")
        # Build only — no install in build() to avoid double install
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1")
        # Run upstream test suite (Clp ships unit tests under Clp/test)
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 check")
        self.run(f"cd '{src}' && MAKEFLAGS='' make -j1 test")

    def package(self):
        # The COIN-OR install target lives below Clp/, not at the source root.
        # Autotools.install() also inherits Conan's parallel -j flag, which
        # creates a jobserver FIFO under HMDFS and fails with EPERM on OHOS.
        src = os.path.join(self.source_folder, "src")
        if not os.path.exists(os.path.join(src, "Clp", "Makefile")):
            src = self.source_folder
        # Conan's copy into HMDFS can strip executable bits after build().
        # Clp's install-exec-local invokes Clp/install-sh directly.
        self.run(f"find '{src}' -name install-sh -type f -exec chmod +x {{}} \\;")
        self.run(
            f"cd '{src}/Clp' && MAKEFLAGS='' make -j1 install "
            f"DESTDIR='{self.package_folder}'"
        )
        # ClpPackedMatrix.hpp includes CoinPragma.hpp without a coin/ prefix.
        # CoinUtils currently exports only its include root, while Clp's public
        # headers are installed in include/coin.  Co-locate this compatibility
        # header so every Clp consumer resolves the upstream include as built.
        coinutils_include = os.path.join(
            self.dependencies["coinutils"].package_folder, "include", "coin"
        )
        copy(
            self,
            "CoinPragma.hpp",
            src=coinutils_include,
            dst=os.path.join(self.package_folder, "include", "coin"),
        )

    def package_info(self):
        self.cpp_info.libs = ["Clp"]
