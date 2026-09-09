#!/usr/bin/env python3
"""Conan recipe — nvi 1.81.6 (Autotools, ex/vi text editor CLI tool).

nvi is the Berkeley implementation of the ex/vi text editor. Builds as a
command-line tool (vi/ex/view) plus libvi (shared + static). Depends on
berkeley-db (db_create, configure probes -ldb) and ncurses (wide-char,
configure probes -lncursesw), both statically linked into the vi binary.

Key platform adaptations (HarmonyOS PC / arm64):
  * dist/config.guess + dist/config.sub patched for ohos triplet
    (patches/0001-config-guess-ohos.patch, applied via conandata patches).
  * configure lives in the dist/ subdir; autotools.configure is invoked with
    build_script_folder="dist" (same pattern as berkeley-db/4.8.30).
  * HMDFS hard-link restriction: `make install` creates vi->ex/view links via
    $(ln); a wrapper (`exec /usr/bin/ln -s "$@"`) is passed as ln=... so the
    editor aliases are soft links (hard links fail with Operation not
    permitted on HMDFS).
  * Dependency injection uses build_folder-relative paths only (R49): never
    pollute shared /usr/local.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NviConan(ConanFile):
    name = "nvi"
    version = "1.81.6"
    description = "nvi — Berkeley implementation of the ex/vi text editor (vi/ex/view CLI tools)"
    license = "BSD-3-Clause"
    homepage = "https://sites.google.com/view/bostic-nvi"
    url = "https://mirrors.ocf.berkeley.edu/debian/pool/main/n/nvi/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml", "patches/*"

    def requirements(self):
        # configure probes `db_create` in -ldb (berkeley-db) and links the
        # wide-char ncurses (-lncursesw); both are statically linked into the
        # final vi binary (vi NEEDED is only libvi.so.0 + libc.so).
        self.requires("berkeley-db/4.8.30")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # nvi configure probes libs via AC_CHECK_LIB(-lncursesw/-ldb) and
        # headers via AC_CHECK_HEADERS; inject dependency include/lib paths.
        # Paths come from conan package folders (private per-build), never a
        # shared /usr/local (R49).
        # ⚠️ nvi's Makefile hard-codes `CFLAGS = $(OPTFLAG)` and rebuilds
        # CPPFLAGS/LDFLAGS from configure-time variables — so the dependency
        # -I/-L MUST be passed as configure arguments (CPPFLAGS=... LDFLAGS=...),
        # NOT via AutotoolsToolchain.extra_cflags (which lands in CFLAGS and is
        # discarded by the generated Makefile; observed in G2 build log).
        ncurses = self.dependencies["ncurses"]
        db = self.dependencies["berkeley-db"]
        ncurses_inc = os.path.join(ncurses.package_folder, "include")
        ncurses_inc_sub = os.path.join(ncurses_inc, "ncurses")
        db_inc = os.path.join(db.package_folder, "include")
        ncurses_lib = os.path.join(ncurses.package_folder, "lib")
        db_lib = os.path.join(db.package_folder, "lib")

        cppflags = [f"-I{ncurses_inc}"]
        if os.path.isdir(ncurses_inc_sub):
            cppflags.append(f"-I{ncurses_inc_sub}")
        cppflags.append(f"-I{db_inc}")
        tc.configure_args.append(f"CPPFLAGS={' '.join(cppflags)}")
        tc.configure_args.append(f"LDFLAGS=-L{ncurses_lib} -L{db_lib}")

        # nvi db backend: use bundled db4 (-ldb from berkeley-db dep).
        tc.configure_args.append("--with-db_type=bundled")
        # vi.recover path must be on a writable dir; use build-folder private
        # path (R49) instead of a fixed system temp location.
        tc.configure_args.append(
            f"vi_cv_path_preserve={os.path.join(self.build_folder, 'vi.recover')}"
        )
        tc.generate()

        # pkg-config path for ncurses .pc files (ncursesw.pc etc.)
        env = Environment()
        env.append_path("PKG_CONFIG_PATH", os.path.join(ncurses_lib, "pkgconfig"))
        env.vars(self).save_script("conanbuild_pkgconfig")

    def build(self):
        # HMDFS hard-link restriction: make install links vi->ex/view with
        # $(ln); wrap /usr/bin/ln to emit soft links instead of hard links.
        wrapper = os.path.join(self.build_folder, "nvi-ln-wrapper")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!/bin/sh\nexec /usr/bin/ln -s \"$@\"\n")
        os.chmod(wrapper, 0o755)
        self._ln_wrapper = wrapper

        # config.status temp dir on HMDFS: configure 内嵌的 umask 077 创建的
        # 临时目录（confXXXXXX）下 subs-*.sed/out 文件被 MAC 拒绝写（E114 类）。
        # 探索阶段已实测 work 目录将 umask 077→002 后 configure 通过；此处对
        # dist/configure 动态执行同样替换（refresh-patch 会把 configure 判为
        # generated 无法生成补丁文件，故在 build() 内联处理——alpine 先例）。
        self._patch_configure_umask()

        autotools = Autotools(self)
        # configure lives in the dist/ subdir; run out-of-source in the
        # conan build folder (same pattern as berkeley-db/4.8.30).
        autotools.configure(build_script_folder="dist")
        # -j1: HMDFS jobserver (mkfifo) restriction; sandbox has no fifo.
        autotools.make(args=["-j1"])

    def _patch_configure_umask(self):
        """dist/configure: config.status temp dir umask 077→002 (HMDFS MAC)."""
        configure = os.path.join(self.source_folder, "dist", "configure")
        if not os.path.isfile(configure):
            return
        with open(configure, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if "umask 002" in content:
            return  # already patched
        new_content = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp=`(umask 002 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(umask 002 && mkdir "$tmp")',
        )
        if new_content != content:
            with open(configure, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(new_content)
            os.chmod(configure, 0o755)
            self.output.info("Patched dist/configure umask 077→002 (config.status tmp dir)")

    def package(self):
        # install-exec-local (vi->ex/view links) does `cd $(DESTDIR)$(bindir)`
        # without creating it first; ensure bin/ exists before make install
        # (parallel -j20 previously raced install-binPROGRAMS' MKDIR_P).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        autotools = Autotools(self)
        # -j1: HMDFS jobserver (mkfifo) restriction + serial install keeps
        # install-exec-local ordered after install-binPROGRAMS (bin dir ready).
        # pass ln=<wrapper> so vi->ex/view are created as soft links
        # (hard links fail on HMDFS with Operation not permitted).
        wrapper = getattr(self, "_ln_wrapper", None)
        if not wrapper:
            wrapper = os.path.join(self.build_folder, "nvi-ln-wrapper")
        autotools.install(args=["-j1", f"ln={wrapper}"])

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["vi"]
        # vi/ex/view are the shipped CLI tools (commands.json at software level)
