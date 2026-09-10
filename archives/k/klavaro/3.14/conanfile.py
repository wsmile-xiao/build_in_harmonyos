#!/usr/bin/env python3
"""Conan recipe — klavaro 3.14 (Autotools + GTK3 typing tutor, GUI application).

Product: `klavaro` executable (GTK3 GUI touch-typing tutor).

Dependency model (gtkdatabox / goffice precedent):
- gtk/3.24.43 (conan, direct): upstream configure.ac PKG_CHECK_MODULES(GTK,
  gtk+-3.0 >= 3.12) + gdk-3.0. PkgConfigDeps generates gtk+-3.0.pc; the
  package-internal gdk-3.0.pc is re-exposed by _copy_gdk_pc() because
  PkgConfigDeps only emits the aggregate component pc.
- gtkdatabox/1.0.0 (conan): upstream PKG_CHECK_MODULES(GTKDATABOX,
  gtkdatabox >= 1.0.0) + AC_CHECK_LIB(gtkdatabox, gtk_databox_new).
- curl/8.15.0 (conan): AC_CHECK_HEADERS(curl/curl.h) + AC_CHECK_LIB(curl,
  curl_global_init). Upstream assumes system curl paths — recipe injects
  CPPFLAGS/LIBS via AutotoolsToolchain env (curl cflags/libs are NOT wired
  into upstream AM_CPPFLAGS/klavaro_LDADD).
- intltool/0.51.0 (conan, tool): IT_PROG_INTLTOOL needs intltool-update/
  merge/extract on PATH. XML::Parser perl module cannot dlopen its XS
  extension from OHOS app-sandbox paths — patch 0001 bypasses the configure
  check; the only -x (XML mode) merge consumer (klavaro.appdata.xml.in) is
  handled by a perl one-liner shim (goffice precedent). The -d (desktop)
  merge mode used for klavaro.desktop.in is pure-regex and works as-is.
- libintl: glib ships proxy-libintl (g_libintl_* symbols, libintl.so.8);
  auxiliar.h includes <libintl.h> under ENABLE_NLS — recipe appends
  -L{glib libdir} -lintl to LIBS.
- fontconfig/2.18.1.1 + expat/2.8.2.1 overrides (R36 alignment): cairo/1.18.4
  recipe pins fontconfig/2.18.1.1 while gtkdatabox/1.0.0 pins 2.18.1 /
  expat/2.8.2 — top-level overrides align the graph on the cairo branch
  (2.18.1.1 / 2.8.2.1, both published for OHOS armv8).

Runtime: klavaro is a GUI app; headless CI verifies ELF + NEEDED closure
(R40 partial for interactive display, same as gtkdatabox examples probe).
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class KlavaroConan(ConanFile):
    name = "klavaro"
    version = "3.14"
    description = "Klavaro Touch Typing Tutor (GTK3 GUI application)"
    license = "GPL-3.0-or-later"
    homepage = "https://klavaro.sourceforge.io/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Direct deps only; the GTK3 sub-stack (pango/cairo/atk/gdk-pixbuf/
        # harfbuzz/fribidi/libepoxy/...) comes transitively via gtk/3.24.43.
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("gtkdatabox/1.0.0", transitive_headers=True, transitive_libs=True)
        self.requires("curl/8.15.0")
        # R36 graph alignment: cairo/1.18.4 pins fontconfig/2.18.1.1 +
        # expat/2.8.2.1; gtkdatabox/1.0.0 pins fontconfig/2.18.1 + expat/2.8.2.
        # Override to the cairo branch (both published for OHOS armv8).
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("expat/2.8.2.1", override=True)

    def build_requirements(self):
        # IT_PROG_INTLTOOL: intltool-update/merge/extract must be on PATH.
        self.tool_requires("intltool/0.51.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        self._copy_gdk_pc()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        env = tc.environment()

        if self.settings.os in ("Linux", "OHOS"):
            # curl headers/libs: upstream AC_CHECK_* only probes; it never
            # wires curl into AM_CPPFLAGS/klavaro_LDADD (system-curl assumption).
            curl_pc = os.path.join(self.generators_folder, "libcurl.pc")
            curl_inc, curl_lib = self._pc_paths(curl_pc)
            # CPPFLAGS (-I only): curl headers for main.c/top10.c. Upstream
            # AC_CHECK_HEADERS(curl/curl.h) probes but never wires curl into
            # AM_CPPFLAGS (system-curl assumption).
            env.append("CPPFLAGS", curl_inc)
            # LDFLAGS (-L only, no -l): AC_CHECK_LIB(curl, curl_global_init)
            # auto-appends -lcurl to LIBS once the -L search path exposes
            # libcurl.so; putting -l into LIBS here would break configure's
            # native-run conftest probe (loader cannot resolve libcurl.so
            # outside the conan run env).
            curl_search = " ".join(
                t for t in curl_lib.split() if t.startswith("-L"))
            env.append("LDFLAGS", curl_search)
            # proxy-libintl (g_libintl_* symbols, libintl.so.8): glib ships
            # it; auxiliar.h includes <libintl.h> under ENABLE_NLS.
            glib = self.dependencies["glib"]
            glib_libdir = glib.cpp_info.aggregated_components().libdirs[0]
            env.append("LDFLAGS", f"-L{glib_libdir}")
            # msgmerge lives in the OHOS SDK gettext tools (libomp.so lives in
            # the SDK llvm lib dir); intltool needs msgmerge/xgettext/msgfmt.
            for sdk_glob in (
                "/data/service/hnp/gettext.org/*/bin",
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
            ):
                sdk_dir = sorted(__import__("glob").glob(sdk_glob))
                if sdk_dir:
                    env.prepend_path("PATH", sdk_dir[0])
                    env.prepend_path("LD_LIBRARY_PATH", sdk_dir[0])
            # intltool-merge -x shim dir wins over the real tool (XML mode
            # needs XML::Parser which cannot load on OHOS).
            env.prepend_path("PATH", self.generators_folder)
        tc.generate(env=env)

    @staticmethod
    def _pc_paths(pc_file):
        """Extract -I/-L flags from a generated pkg-config file.

        PkgConfigDeps .pc files use ${includedir}/${libdir} variable
        references — expand them before extracting flags.
        """
        incs, libs = [], []
        if os.path.isfile(pc_file):
            text = open(pc_file).read()
            # expand ${prefix}/${libdir}/${includedir} style vars
            for _ in range(3):  # nested vars, expand iteratively
                if "${" not in text:
                    break
                text = re.sub(
                    r"\$\{(\w+)\}",
                    lambda m: next(
                        (ln.split("=", 1)[1].strip()
                         for ln in text.splitlines()
                         if ln.startswith(m.group(1) + "=")),
                    ""), text)
            for line in text.splitlines():
                if line.startswith("Cflags:"):
                    incs = [t.replace('"', '') for t in line.split()
                            if t.startswith("-I") and "${" not in t]
                elif line.startswith("Libs:"):
                    libs = [t.replace('"', '') for t in line.split()
                            if (t.startswith("-L") or t.startswith("-l"))
                            and "${" not in t]
        return " ".join(incs), " ".join(libs)

    def _copy_gdk_pc(self):
        """Re-expose the gtk package's internal gdk-3.0.pc.

        configure.ac checks gtk+-3.0 AND gdk-3.0 separately. PkgConfigDeps
        only emits the aggregate gtk+-3.0.pc for the conan gtk package, so
        the package-internal gdk-3.0.pc is copied into the generators folder
        with its prefix rewritten to the real package folder.
        """
        gtk = self.dependencies["gtk"]
        pkgdir = gtk.package_folder
        for name in ("gdk-3.0.pc", "gtk+-3.0.pc"):
            src = None
            for sub in ("lib/pkgconfig", "share/pkgconfig"):
                cand = os.path.join(pkgdir, sub, name)
                if os.path.isfile(cand):
                    src = cand
                    break
            if not src:
                continue
            text = open(src).read()
            # generic prefix rewrite: gtk ships .pc files whose prefix=
            # points at the build-machine cache path — repoint at the real
            # package folder (no hardcoded cache path, stays portable).
            if "prefix=" in text and f"prefix={pkgdir}" not in text:
                lines = text.splitlines()
                for i, ln in enumerate(lines):
                    if ln.startswith("prefix="):
                        lines[i] = f"prefix={pkgdir}"
                        break
                text = "\n".join(lines) + "\n"
            save(self, os.path.join(self.generators_folder, name), text)

    def build(self):
        apply_conandata_patches(self)
        self._patch_config_status_tmpdir()
        self._write_intltool_merge_shim()
        autotools = Autotools(self)
        autotools.configure()
        # CI #43592 lesson: patch 0003 appends a bare `-lintl` to
        # klavaro_LDADD, which relies on the -L search order resolving to the
        # glib package's proxy-libintl. On workers whose toolchain/sysroot
        # exposes another libintl (musl stub without g_libintl_* symbols)
        # the bare -lintl wins and the link fails with undefined
        # g_libintl_bindtextdomain/... from main.o (glib's libintl.h
        # #defines gettext -> g_libintl_gettext unconditionally, so a
        # command-line identity macro cannot override it either) and from
        # libgtk-3.so/libcairo-gobject.so under --no-allow-shlib-undefined.
        # Fix: pin the conan glib package's libintl.so by ABSOLUTE PATH in
        # the generated src/Makefile so the g_libintl_* symbols always come
        # from the conan closure, independent of any -L search order.
        self._pin_intl_libpath()
        # configure bakes the absolute path of the real intltool-merge into
        # INTLTOOL_MERGE; the -x (XML mode) invocations need the shim
        # instead (XML::Parser cannot load on OHOS). Rewrite the variable in
        # every generated Makefile.
        shim = os.path.join(self.generators_folder, "intltool-merge")
        for mk in (
            os.path.join(self.build_folder, "data", "Makefile"),
            os.path.join(self.build_folder, "Makefile"),
        ):
            if os.path.isfile(mk):
                text = open(mk).read()
                import re as _re
                text = _re.sub(r"^INTLTOOL_MERGE = .*$",
                               f"INTLTOOL_MERGE = {shim}",
                               text, flags=_re.M)
                save(self, mk, text)
                self.output.info(f"Redirected INTLTOOL_MERGE -> shim in {mk}")
        autotools.make(args=["-j2"])

    def _pin_intl_libpath(self):
        """Rewrite the bare `-lintl` in klavaro_LDADD to the glib package's
        absolute libintl.so path (CI worker independence).

        glib ships proxy-libintl (libintl.so.8, g_libintl_* symbols); the
        absolute path guarantees the linker picks it regardless of sysroot
        -L order, resolving both main.o's gintl.h-expanded references and
        the --no-allow-shlib-undefined closure of the gtk tree.
        """
        glib = self.dependencies["glib"]
        glib_libdir = glib.cpp_info.aggregated_components().libdirs[0]
        intl_so = os.path.join(glib_libdir, "libintl.so")
        intl_a = os.path.join(glib_libdir, "libintl.a")
        pinned = intl_so if os.path.isfile(intl_so) else (
            intl_a if os.path.isfile(intl_a) else None)
        if not pinned:
            self.output.warning(
                "glib package exposes no libintl.so/.a — -lintl left bare")
            return
        mk = os.path.join(self.build_folder, "build-release", "src", "Makefile")
        if not os.path.isfile(mk):
            mk = os.path.join(self.build_folder, "src", "Makefile")
        if not os.path.isfile(mk):
            self.output.warning("src/Makefile not found — -lintl not pinned")
            return
        text = open(mk).read()
        if "\t\t-lintl" in text or "-lcurl \\\n\t\t-lintl" in text:
            text = text.replace("\t\t-lintl", f"\t\t{pinned}")
            save(self, mk, text)
            self.output.info(f"Pinned -lintl -> {pinned} in {mk}")
        elif "-lintl" in text:
            text = text.replace("-lintl", pinned)
            save(self, mk, text)
            self.output.info(f"Pinned bare -lintl -> {pinned} in {mk}")
        else:
            # LDADD never carried -lintl (patch 0003 not applied?): append
            # the absolute path so the link still resolves g_libintl_*.
            text = text.replace(
                "\t\t-lgmodule-2.0 \\",
                f"\t\t-lgmodule-2.0 \\\n\t\t{pinned} \\", 1)
            save(self, mk, text)
            self.output.info(f"Appended {pinned} to klavaro_LDADD in {mk}")

    def _patch_config_status_tmpdir(self):
        """E114: config.status writes its awk temp files via `mktemp -d
        ./confXXXXXX` in the build dir; on HMDFS those dirs get created
        drwx--S--- and cannot be written, so config.status fails with
        "could not setup config files machinery". Redirect ac_tmp to a
        tmpfs directory (gtkdatabox / BIRD precedent).
        """
        import tempfile
        fixed_tmp = os.path.join(tempfile.gettempdir(), "klavaro-config-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        os.chmod(fixed_tmp, 0o700)
        for cand in (
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.build_folder, "configure"),
        ):
            if os.path.isfile(cand) and "ac_tmp=$tmp" in open(cand).read():
                text = open(cand).read()
                text = text.replace("ac_tmp=$tmp", f"ac_tmp={fixed_tmp}")
                save(self, cand, text)
                os.chmod(cand, 0o755)
                self.output.info(f"Patched config.status temp dir in {cand}")

    def _write_intltool_merge_shim(self):
        """PATH shim for intltool-merge (goffice precedent).

        intltool-merge -x (XML mode) requires the XML::Parser perl module,
        whose XS extension cannot dlopen from OHOS app-sandbox paths (musl
        loader "Permission denied" on user-space .so). The -d (desktop) mode
        is pure-regex and works. The shim intercepts -x invocations with a
        perl one-liner that strips the "_" translation markers from XML
        tags; all other invocations are forwarded to the real
        intltool-merge resolved from PATH.
        """
        shim = os.path.join(self.generators_folder, "intltool-merge")
        perl = (
            "my($in,$out)=($ARGV[$#ARGV-1],$ARGV[$#ARGV]);"
            "open(I,\"<\",$in) or exit 1;"
            "open(O,\">\",$out) or exit 1;"
            "while(<I>){s|<(\\/?)_([A-Za-z][A-Za-z0-9_]*)>|<$1$2>|g;print O;}"
            "close(O);"
        )
        script = (
            "#!/bin/sh\n"
            "for a in \"$@\"; do\n"
            "  if [ \"$a\" = \"-x\" ]; then\n"
            "    exec perl -e '" + perl + "' -- \"$@\"\n"
            "  fi\n"
            "done\n"
            "real=$(which -a intltool-merge 2>/dev/null | grep -v \"^$0$\" | head -1)\n"
            "exec \"${real:-intltool-merge}\" \"$@\"\n"
        )
        save(self, shim, script)
        os.chmod(shim, 0o755)
        self.output.info(f"Wrote intltool-merge -x shim: {shim}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # GUI application: binary in bin/, no linkable library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # Runtime shared-object closure is provided by conan dependencies
        # (gtk/gtkdatabox/curl trees); VirtualRunEnv in test_package wires
        # LD_LIBRARY_PATH.
