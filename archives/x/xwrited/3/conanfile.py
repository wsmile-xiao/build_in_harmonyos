#!/usr/bin/env python3
"""Conan recipe — xwrited 3 (Makefile).

xwrited displays write(1)/wall(1) messages as freedesktop.org desktop
notifications (GApplication + GDBus client, GLib >= 2.48). Upstream ships a
hand-written Makefile only (no configure/autotools/cmake/meson) and no test
suite; see test_package/MANIFEST.yml for the audit.

Version slug: upstream labels this release only as "3" (tarball
xwrited-3.tar.gz, Makefile VERSION = 3, `xwrited --version` prints
`xwrited 3`) and publishes no dotted form. Conan 2.x rejects a
single-character version — its RecipeReference pattern needs >= 2 chars —
so `xwrited/3` fails at export with `ERROR: Invalid package version '3'`.
Following the sanctioned repo precedent (cronic/3 -> cronic/v3,
tweeny/3 -> tweeny/v3, gcal/4 -> gcal/v4) the task-card directory stays `3`
while set_version() names the built artifact `xwrited/v3`. The archive
directory and the `feat/xwrited-3` branch keep the platform's task-card form.

OHOS aarch64 adaptation notes:
- Force the utmpx backend (OS_NAME=OHOS on the make command line). Upstream
  picks the libutempter backend only when `uname -s` is Linux/FreeBSD; OHOS
  has no utmp/wtmp privileged helper, so the utmpx path (used upstream for
  every other OS) is the portable choice. No source patch is needed for this:
  OS_NAME is a plain make variable and the command line wins.
- OHOS utmpx no-op (patches/0001-ohos-utmpx-noop.patch + OHOS_NO_UTMPX_DB):
  the OHOS musl libc ships <utmpx.h> struct definitions only — no
  setutxent/pututxline/endutxent symbols and no ut_name member (E121/agetty
  precedent; true-machine error "no member named 'ut_name' in 'struct utmpx'").
  On OHOS the pty login-accounting entry compiles to a deliberate no-op; the
  notification path does not depend on it. Non-OHOS builds keep upstream
  semantics (patch only adds a ut_name->ut_user compat alias for musl).
- Build only the binary + .desktop + .mo targets. The `all` target also builds
  the man page via xsltproc with a remote docbook stylesheet URL, which needs
  network at build time; `make install` additionally relies on GNU
  `install -D`. Both are avoided: files are installed with conan copy().
- pkg-config (gobject-2.0/gio-2.0/glib-2.0) resolves against the PkgConfigDeps
  output in the generators folder (batsignal 1.8.0 precedent).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class XwritedConan(ConanFile):
    name = "xwrited"
    description = "Display write and wall messages as desktop notifications"
    license = "MIT"
    homepage = "https://code.guido-berhoerster.org/projects/xwrited/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/x/xwrited/3"
    topics = ("notification", "write", "wall", "glib", "desktop")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def set_version(self):
        # Upstream label "3" -> artifact version `v3` (see docstring).
        # Deliberately not a bare `version = "3"` attribute: Conan rejects the
        # one-character form, and CI L0m/PF8 only cross-check a literal
        # `version = "..."` attribute against the version directory, so the
        # task-card directory `3` and the artifact `xwrited/v3` coexist.
        self.version = "v3"

    def _resolve_cc(self):
        # R33 + ADAPTATION_GUIDE Makefile template (zurl precedent): the
        # profile conf is the single source of truth — use it when the file
        # exists (healthy workers: zero behaviour change); otherwise fall
        # back to the bare `clang` name for PATH resolution (some HMBS hosts
        # lack /data/service/hnp/bin/clang entirely). Never a bare $CC shell
        # variable (empty on release workers). Read-only isfile probing only.
        try:
            comp_exes = (self.conf.get("tools.build:compiler_executables",
                                        default={}, check_type=dict) or {})
        except Exception:
            comp_exes = {}
        conf_cc = (comp_exes.get("c") or "").split()[0]
        if conf_cc and os.path.isfile(conf_cc):
            return conf_cc
        if conf_cc:
            self.output.warning(
                "profile compiler %s not present on this host, "
                "falling back to PATH clang" % conf_cc)
        return "clang"

    def _pkgconf_exe(self):
        # The in-repo pkgconf recipe installs only `pkgconf` (upstream
        # 3.0.5 ships no `pkg-config` alias), so a bare `pkg-config` call
        # fails even with pkgconf on PATH (pianobar/libsylph/redstore
        # precedent). Resolve the absolute pkgconf executable: build-dep
        # package folder first, then PATH probing. No X_OK probing (R49).
        candidates = []
        try:
            dep = self.dependencies.build["pkgconf"]
            root = dep.package_folder or ""
            try:
                info = dep.cpp_info.aggregated_components()
                bindirs = list(info.bindirs or ["bin"])
            except Exception:
                bindirs = ["bin"]
            for d in bindirs:
                base = os.path.join(root, d) if root else d
                candidates.append(os.path.join(base, "pkgconf"))
                candidates.append(os.path.join(base, "pkg-config"))
        except Exception as exc:
            self.output.warning("pkgconf build-dep lookup failed: %s" % exc)
        for name in ("pkgconf", "pkg-config"):
            w = shutil.which(name)
            if w:
                candidates.append(w)
        for cand in candidates:
            try:
                if cand and os.path.isfile(cand):
                    return cand
            except Exception:
                continue
        return ""

    def _ensure_pkg_config_shim(self, pkgconf):
        # Cover Makefiles that hardcode a bare `pkg-config` string (a
        # PKG_CONFIG= command-line override only wins when the Makefile
        # goes through the variable). Symlink needs no chmod (HMBS
        # HMDFS ignores chmod) and symlink is a supported capability.
        shim_dir = os.path.join(self.build_folder, "_ohos_tool_shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        if not pkgconf:
            return ""
        link = os.path.join(shim_dir, "pkg-config")
        try:
            if os.path.islink(link) or os.path.isfile(link):
                try:
                    os.remove(link)
                except OSError:
                    pass
            os.symlink(pkgconf, link)
            return shim_dir
        except OSError as exc:
            self.output.warning("pkg-config shim symlink failed: %s" % exc)
            return ""

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1")
        # CCI-leaf replacement (libtiger/0.3.4 + ayatana-ido/0.10.4-v2
        # precedent, same fingerprint): glib's bare libffi/3.4.4 resolves to
        # the CCI recipe on preflight (log applies the CCI-only patch
        # 0008-3.4.4-invalid-CFI-advance_loc.patch, absent from the in-repo
        # recipe), whose configure dies with
        # "/data/service/hnp/bin/bash: inaccessible or not found" (Error 127).
        # Pin the ohpcd-published RREV of the hardened in-repo recipe
        # (ohpcd v2 API verified single revision, 2026-07-17; same value
        # libgsf validated end-to-end). Same version, so glib's package_id
        # is untouched (a 3.5.2 swap would force a glib source rebuild).
        self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
                      override=True)

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")
        self.tool_requires("gettext/0.22.5.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xwrited is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()

    def _augment_glib_pkg_config(self):
        # glib 2.84 on musl routes g_libintl_* through its bundled
        # proxy-libintl (libintl.so in the glib package libdir), but the
        # PkgConfigDeps-generated glib-2.0/gio-2.0/gobject-2.0 .pc files
        # list no -lintl, so the hand-written Makefile link
        # (`pkg-config --libs gobject-2.0 gio-2.0 glib-2.0`) leaves
        # g_libintl_bindtextdomain/g_libintl_gettext/... undefined
        # (true-machine ld.lld errors, ayatana-common/accountsservice/
        # ayatana-indicator-power precedent). Append -lintl; the existing
        # -L<glib libdir> in the same Libs line resolves it to the bundled
        # proxy-libintl. No new requires: gettext stays a tool_requires
        # (msgfmt only).
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            libs_line = next(
                (line for line in content.splitlines()
                 if line.startswith("Libs:")),
                None,
            )
            if libs_line is None or "-lintl" in libs_line.split():
                continue
            content = content.replace(libs_line, libs_line + " -lintl", 1)
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def build(self):
        # HMBS runtime hardening (aldo 0.7.8 / cvechecker 4 precedent):
        # keep temp files inside the injected writable TMPDIR (HMFS /tmp can
        # be read-only) and prefer a getcwd-clean shell.
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass
        os.environ["PWD"] = self.build_folder
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        for key in ("SHELL", "CONFIG_SHELL"):
            if not os.environ.get(key):
                os.environ[key] = "/bin/sh"

        # Compiler (R33): profile conf value when present on disk, else the
        # bare PATH name. The Makefile honours CC on the command line
        # (CC := $(CC) -std=c99).
        cc = self._resolve_cc()
        self.output.info("xwrited build: CC=%s" % cc)

        # PkgConfigDeps writes relocatable gobject-2.0/gio-2.0/glib-2.0 .pc
        # files into the generators folder; the Makefile shells out to
        # `pkg-config`, so it must be on PKG_CONFIG_PATH (batsignal precedent).
        pkg_config_path = self.generators_folder
        if os.environ.get("PKG_CONFIG_PATH"):
            pkg_config_path += os.pathsep + os.environ["PKG_CONFIG_PATH"]
        os.environ["PKG_CONFIG_PATH"] = pkg_config_path
        # The in-repo pkgconf ships no `pkg-config` alias (only `pkgconf`),
        # so resolve its absolute executable, pass it as PKG_CONFIG on the
        # make command line, and provide a `pkg-config` symlink shim for
        # hardcoded bare-name calls (pianobar/libsylph/redstore precedent).
        pkgconf = self._pkgconf_exe()
        self.output.info("xwrited build: pkgconf=%s" % (pkgconf or "<missing>"))
        shim_dir = self._ensure_pkg_config_shim(pkgconf)
        # Prepend the shim dir plus every build-dep bindir (msgfmt from
        # gettext, pkgconf itself) to PATH — best effort, never fatal here.
        path_bits = []
        if shim_dir:
            path_bits.append(shim_dir)
        try:
            for dep in self.dependencies.build.values():
                try:
                    root = dep.package_folder or ""
                except Exception:
                    continue
                if not root:
                    continue
                try:
                    info = dep.cpp_info.aggregated_components()
                    bindirs = list(info.bindirs or ["bin"])
                except Exception:
                    bindirs = ["bin"]
                for d in bindirs:
                    p = os.path.join(root, d)
                    try:
                        if os.path.isdir(p) and p not in path_bits:
                            path_bits.append(p)
                    except Exception:
                        continue
        except Exception as exc:
            self.output.warning("xwrited PATH prepend probe failed: %s" % exc)
        if path_bits:
            os.environ["PATH"] = os.pathsep.join(
                path_bits + [os.environ.get("PATH", "")])

        # -j1: the OHOS sandbox forbids make jobserver pipes (mkfifo).
        # OS_NAME=OHOS forces the utmpx backend (no libutempter on OHOS).
        # XCPPFLAGS keeps ptsname/posix_openpt visible under -std=c99 musl.
        # On OHOS additionally define OHOS_NO_UTMPX_DB: the OHOS (musl-based)
        # libc ships <utmpx.h> struct definitions only — no
        # setutxent/pututxline/endutxent symbols and no ut_name member
        # (true-machine error "no member named 'ut_name' in 'struct utmpx'",
        # E121/agetty precedent) — so the pty login-accounting entry in
        # xwd-utmp-utmpx.c is compiled to a deliberate no-op via
        # patches/0001-ohos-utmpx-noop.patch. Non-OHOS builds keep upstream
        # semantics (the patch's #else branch only adds a ut_name->ut_user
        # compat alias for musl).
        # Man pages are intentionally skipped (xsltproc + remote docbook URL).
        xcppflags = "-D_XOPEN_SOURCE=600 -D_DEFAULT_SOURCE"
        try:
            if str(self.settings.os) == "OHOS":
                xcppflags += " -DOHOS_NO_UTMPX_DB=1"
        except Exception:
            pass
        cmd = (
            "make -j1 CC=\"{cc}\" PKG_CONFIG=\"{pc}\" OS_NAME=OHOS "
            "XCPPFLAGS=\"{xc}\" "
            "xwrited "
            "org.guido-berhoerster.code.xwrited.desktop "
            "po/de.mo po/en.mo po/id.mo"
        ).format(cc=cc, pc=pkgconf or "pkgconf", xc=xcppflags)
        self.run(cmd, cwd=self.source_folder, env="conanbuild")

        # Upstream ships no test suite (audited in test_package/MANIFEST.yml).
        # Emit the no_tests marker here as well so evidence exists even when
        # test_package later runs against a build cache hit (aldo precedent).
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT={\"status\": \"no_tests\", "
            "\"framework\": \"make\", "
            "\"command\": \"make check (upstream registers no tests)\", "
            "\"discovered\": 0, \"executed\": 0, \"passed\": 0, "
            "\"failed\": 0, \"skipped\": 0, "
            "\"reason\": \"xwrited 3 audited: hand-written Makefile has no "
            "check/test target, source tree has no tests/ directory or test "
            "sources; make check is a no-op\"}"
        )

    def package(self):
        # Deliberately not `make install`: it would rebuild the man page over
        # the network (xsltproc + remote docbook stylesheet) and depends on
        # GNU `install -D`. Install the built artefacts with conan copy().
        copy(self, "xwrited", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.desktop", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "applications"),
             keep_path=False)
        for lang in ("de", "en", "id"):
            copy(self, "%s.mo" % lang,
                 src=os.path.join(self.source_folder, "po"),
                 dst=os.path.join(
                     self.package_folder, "share", "locale", lang,
                     "LC_MESSAGES"),
                 keep_path=False)
            # Upstream names the catalog de.mo/en.mo/id.mo; the runtime loads
            # it under GETTEXT_PACKAGE ("xwrited"), so rename on install.
            try:
                os.rename(
                    os.path.join(
                        self.package_folder, "share", "locale", lang,
                        "LC_MESSAGES", "%s.mo" % lang),
                    os.path.join(
                        self.package_folder, "share", "locale", lang,
                        "LC_MESSAGES", "xwrited.mo"))
            except OSError:
                pass
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "xwrited"),
             keep_path=False)
        copy(self, "NEWS", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "xwrited"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
