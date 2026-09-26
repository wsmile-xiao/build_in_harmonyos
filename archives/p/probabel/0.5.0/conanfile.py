#!/usr/bin/env python3
"""Conan recipe — ProbABEL 0.5.0 (GWAS analysis toolkit, GenABEL).

ProbABEL is a set of command-line tools (palinear, palogist, pacoxph,
extract-snp) for genome-wide association analysis of imputed genetic
data. Upstream ships an autotools build (no generated configure —
autoreconf is run in build()) and an integration test suite wired into
`make check` (11 shell tests comparing tool output against verified
results); the build() below executes it for real. The R-reference tests
(checks/R-tests) are only wired in when configure detects R, which the
build environment does not provide, so they register zero tests here.
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class ProbabelConan(ConanFile):
    name = "probabel"
    version = "0.5.0"
    description = "ProbABEL: genome-wide association analysis of imputed genetic data (GWAS toolkit)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/GenABEL-Project/ProbABEL"
    url = ""  # CI fills this
    topics = ("gwas", "genetics", "association", "bioinformatics")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"probabel not validated for {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Upstream tarball ships no generated configure; autoreconf -fi needs
        # automake (aclocal) which the CI sandbox lacks (only the autoconf
        # suite exists under /data/service/hnp/bin).  tool_requires resolved
        # with the build profile: automake/1.18 + libtool/2.5.4, published
        # in the ohpcd repo (rrev 65a7ba60 / verified 2026-09-26), same as
        # archives/a/abiword-plugin-clarisworks/3.0.8:113-114.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def generate(self):
        # The bundled Eigen 3.2.1 (2014) uses std::binder1st/binder2nd,
        # which were removed in C++17 — build against C++14 regardless of
        # the profile default (the appended flag wins over the earlier
        # -std flag). ProbABEL is an application, so no consumer ABI
        # contract applies.
        tc = AutotoolsToolchain(self)
        tc.extra_cxxflags.append("-std=gnu++14")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS/OpenHarmony shell routing: everything runs under /bin/sh —
        # autoconf's re-exec cannot getcwd under HMDFS when routed through
        # the hnp bash (E386), and the upstream CPPFLAGS+="..." bashisms
        # are fixed by patches/0001 so /bin/sh suffices for configure.
        # `make check` overrides SHELL with bash because the upstream test
        # scripts are bash (run_diff.sh uses echo -e / substring ops).
        src = self.source_folder
        # The CI worker (and this host's non-login PATH) lacks aclocal:
        # bootstrap tools come in via tool_requires below — repo-standard
        # approach (argp-standalone / abiword-plugin-* precedent) — and are
        # exposed through the conanbuild environment.
        self.run(
            'env -u CONFIG_SHELL SHELL=/bin/sh autoreconf -fi',
            cwd=src, env="conanbuild",
        )
        # E011/E114: HMDFS cannot write the 0700-mode temp dirs configure
        # creates via `umask 077` (config.status machinery dies with
        # "could not setup config files machinery"). Drop the umask
        # wrapper, keep the real temp dir creation.
        replace_in_file(self, f"{src}/configure",
                        "umask 077 && ", "")
        # The upstream check scripts carry #!/bin/bash shebangs, but bash
        # lives at /data/service/hnp/bin/bash on OpenHarmony — without
        # this every TEST fails with exec ENOENT.
        self.run(
            "sed -i '1s|^#!.*bash|#!/data/service/hnp/bin/bash|' "
            "checks/*.sh",
            cwd=src,
        )
        # The hnp bash, starting with a broken HMDFS cwd, cannot keep the
        # scripts' fd-3 silencing idiom alive (fd 3 goes bad between
        # uses). Replace `>& 3` with the equivalent direct /dev/null
        # redirection; the diff-based assertions are unchanged.
        self.run(
            "sed -i -e 's/exec 3>\\/dev\\/null/true/' "
            "-e 's/exec 3>&1/true/' "
            "-e 's/>& 3/>\\/dev\\/null 2>\\&1/g' "
            "-e 's/>&3/>\\/dev\\/null 2>\\&1/g' checks/*.sh && sync",
            cwd=src,
        )
        self.run(
            'env -u CONFIG_SHELL SHELL=/bin/sh '
            f'./configure --prefix="{self.package_folder}"',
            cwd=src,
        )
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh make -j2", cwd=src)
        # The probabel wrapper (dist_bin_SCRIPTS) is a perl script with a
        # #!/usr/bin/perl shebang; perl lives at /data/service/hnp/bin on
        # OpenHarmony. Fix it at the source; the copies the check suite
        # and make install take from src/ inherit the fixed shebang.
        self.run(
            "sed -i '1s|^#!.*perl|#!/data/service/hnp/bin/perl|' "
            "src/probabel && sync",
            cwd=src,
        )
        # Upstream integration suite: 11 shell tests in checks/Makefile.am
        # (TESTS), comparing tool output against verified_results/. Run for
        # real; the R-reference tests register zero tests without R.
        self.run(
            "env SHELL=/data/service/hnp/bin/bash make -j1 check", cwd=src
        )

    def package(self):
        self.run(
            "env -u CONFIG_SHELL SHELL=/bin/sh make install",
            cwd=self.source_folder,
        )
        self._fix_probabel_pl_symlink()

    def _fix_probabel_pl_symlink(self):
        # 上游 src/Makefile.am:436 用 `ln -s $(DESTDIR)$(bindir)/probabel probabel.pl`
        # 安装别名——链接目标里带着 DESTDIR，于是打包后它指向**构建缓存里的绝对路径**，
        # 换机/换 CONAN_HOME 即成悬空链接（可重定位安装的经典缺陷）。
        # 这里改写成相对链接；HMDFS 拒绝建软链时（E018/E050 家族）退化为直接复制一份。
        import os
        import shutil

        bindir = os.path.join(self.package_folder, "bin")
        alias = os.path.join(bindir, "probabel.pl")
        if not os.path.islink(alias) and not os.path.exists(alias):
            return
        if os.path.islink(alias):
            os.unlink(alias)
        try:
            os.symlink("probabel", alias)
        except OSError:
            shutil.copyfile(os.path.join(bindir, "probabel"), alias)
            # chmod only applies to the copied regular file: on a symlink it
            # would follow to bin/probabel itself, and symlink modes are not
            # expressible on Linux/HMDFS.
            os.chmod(alias, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
