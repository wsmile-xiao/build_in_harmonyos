#!/usr/bin/env python3
"""Conan recipe — gtksourceview4 4.8.4 (Meson).

GtkSourceView 4 is the GNOME syntax-highlighting text widget library for
GTK3 (the 4.x series keeps the GTK3 backend; 5.x is the GTK4 rewrite).
Adapted to HarmonyOS PC (aarch64): built against the conan-published
gtk/3.24.43 (OHOS shared binary) plus libxml2/2.15.3 and fribidi/1.0.16.

Disabled on OHOS: gir (gobject-introspection), vapi, gtk-doc, glade-catalog
(no g-ir-scanner / vapigen / gtk-doc cross toolchain) and install_tests
(installed-tests are a desktop deployment concept).

See notes.md for the platform notes (glib build-time host tools, meson/ninja
probe quirk, headless testsuite limits) and the upstream test results.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class Gtksourceview4Conan(ConanFile):
    name = "gtksourceview4"
    version = "4.8.4"
    description = "GtkSourceView 4 — GNOME syntax highlighting widget for GTK3 (OHOS adaptation)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtksourceview"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: platform check accepts os=OHOS (CI profile) and Linux (dev runs).
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gtksourceview4 requires Linux or OHOS, got {self.settings.os}")

    def requirements(self):
        # gtksourceview 4.8.4 meson dependency() → conan package mapping:
        #   glib-2.0 / gobject-2.0 / gio-2.0  → transitive via gtk (shared glib)
        #   gtk+-3.0 (>= 3.24)                → gtk/3.24.43 (identical pin to
        #       the archived gtksourceview3/3.24.11 recipe: the GTK3 stack on
        #       ohpcd only publishes a shared OHOS binary at this revision,
        #       R36/PF4 dependency gate probes each of them)
        #   libxml-2.0 (>= 2.6)               → libxml2/2.15.3
        #   fribidi (>= 0.19.7)               → fribidi/1.0.16 (GTK3 graph pin;
        #       gtk3 -> pango already pulls it, declaring it keeps the graph
        #       unified and the header probe honest)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)

    def layout(self):
        # meson_layout() was removed in conan 2.29.x — replicate its folders:
        # builddir/ holds the meson build root, generators/ the .pc files.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI/worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are not
        # on PATH; pin the real toolchain binaries by ABSOLUTE PATH (gtk4 /
        # glib2 recipe precedent, otherwise meson picks nonexistent tools).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}")

        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        self._tc = tc
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # NEVER strip shared libs: the OHOS loader validates the .codesign hash,
        # strip rewrites the .so → dlopen Permission denied (libsoup3 lesson).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # No network wraps: every dependency is conan-provided.
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS has no g-ir-scanner / vapigen / gtk-doc / gladeui cross
        # toolchain (4.8.4 defaults: gir=true, vapi=true → must be turned off).
        tc.project_options["gir"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["glade_catalog"] = "false"
        # tests/ and testsuite/ are compiled (subdir() is unconditional) and the
        # headless-runnable subset is executed in build(); installed-tests are
        # not packaged.
        tc.project_options["install_tests"] = "false"
        self._pin_build_env()
        tc.generate()
        self._patch_conanbuildenv()
        self._fix_glib_pcs()
        self._augment_pcs_intl()

    # ------------------------------------------------------------------
    # Build-time environment / glib host tools (OHOS specifics)
    # ------------------------------------------------------------------

    def _pin_build_env(self):
        """Pin meson's probe targets and the glib host tools by absolute path.

        OHOS measured facts (gtk4 / gtksourceview5 recipe precedents):
        * meson's ``detect_ninja`` runs ``ninja --version``; the hnp ninja ELF
          needs libc++_shared.so which the conan-rewritten environment drops →
          the probe fails ("Could not detect Ninja v1.8.2 or newer"). Inject the
          NINJA variable (meson's first probe candidate) plus /system/lib64 and
          the SDK llvm lib dir on LD_LIBRARY_PATH.
        * glib-mkenums / glib-compile-resources must come from the conan glib
          package (the hnp copies are stale and their shebangs are broken), and
          those ELFs need glib's own libs on LD_LIBRARY_PATH to exec at all.
        """
        _ninja = "/data/service/hnp/bin/ninja"
        if not os.path.isfile(_ninja):
            _ninja = shutil.which("ninja") or _ninja
        os.environ["NINJA"] = _ninja
        self.buildenv_info.define_path("NINJA", _ninja)

        for _p in ("/system/lib64",
                   "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"):
            if os.path.isdir(_p):
                os.environ["LD_LIBRARY_PATH"] = (
                    _p + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _p)

        gbin, glib_lib = self._glib_tool_dirs()
        if not gbin:
            self.output.warning("no dependency ships glib build-time tools "
                                "(glib-mkenums / glib-compile-resources)")
            return
        os.environ["PATH"] = gbin + os.pathsep + os.environ.get("PATH", "")
        self.buildenv_info.prepend_path("PATH", gbin)
        if glib_lib:
            os.environ["LD_LIBRARY_PATH"] = (
                glib_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", ""))
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", glib_lib)
        # gnome.mkenums_simple()/compile_resources() resolve these from the
        # meson native file [binaries] section when present.
        for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                     "glib-compile-resources", "glib-compile-schemas"):
            tool_path = os.path.join(gbin, tool)
            if os.path.isfile(tool_path):
                self._tc.binaries[tool] = tool_path
        self.output.info("glib build-time tools pinned from %s" % gbin)

    def _glib_tool_dirs(self):
        """Return (bindir, libdir) of the dependency shipping glib's build-time
        tools — the graph may name that package glib or glib2."""
        for _ref, dep in self.dependencies.items():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            bdir = os.path.join(folder, "bin")
            if (os.path.isfile(os.path.join(bdir, "glib-compile-resources"))
                    or os.path.isfile(os.path.join(bdir, "glib-mkenums"))):
                return bdir, os.path.join(folder, "lib")
        return None, None

    def _patch_conanbuildenv(self):
        # ConanFile.run() wraps every command with `source conanbuild.sh`, and
        # the conanbuildenv-{settings}.sh file is (re)written after generate()
        # → the only working injection point is appending to the generated file
        # from build(), before the first meson call. NINJA + the two extra lib
        # dirs must be re-declared there because conan's env rebuild discards
        # the os.environ mutations made in generate().
        _sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        for envf in glob.glob(os.path.join(self.generators_folder, "conanbuildenv-*.sh")):
            with open(envf, encoding="utf-8") as handle:
                text = handle.read()
            append = ""
            if "NINJA=" not in text:
                append += '\nexport NINJA="/data/service/hnp/bin/ninja"\n'
            if 'export LD_LIBRARY_PATH="/system/lib64' not in text:
                append += ('export LD_LIBRARY_PATH="/system/lib64:%s'
                           '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n' % _sdk_lib)
            if append:
                if not text.endswith("\n"):
                    text += "\n"
                with open(envf, "w", encoding="utf-8") as handle:
                    handle.write(text + append)
                self.output.info("conanbuildenv patched: NINJA + /system/lib64 (%s)"
                                 % os.path.basename(envf))

    def _sign_glib_tools(self):
        """E077/E486: sign the glib package's host tool ELFs in place.

        OHOS refuses to exec an ELF carrying no valid ``.codesign`` section
        ("Operation not permitted", code 126). glib ships unsigned
        glib-compile-resources / glib-mkenums binaries in its ``bin/`` and
        meson drives them through gnome.gresource() / mkenums_simple() custom
        targets, so without signing every one of those targets dies
        (vte 0.74.2 / gtksourceview5 recipe precedent).
        """
        if self.settings.os != "OHOS":
            return
        gbin, _glib_lib = self._glib_tool_dirs()
        if not gbin or not os.path.isdir(gbin):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        signed = 0
        for name in os.listdir(gbin):
            binpath = os.path.join(gbin, name)
            if not os.path.isfile(binpath) or os.path.islink(binpath):
                continue
            try:
                with open(binpath, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run(f'{objcopy} --remove-section .codesign "{binpath}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{binpath}" -outFile "{binpath}" '
                     f'-selfSign 1 2>/dev/null || true')
            self.run(f'chmod a+x "{binpath}" 2>/dev/null || true')
            signed += 1
        self.output.info("signed %d glib host tool ELF(s) in place" % signed)

    def _fix_glib_pcs(self):
        # PkgConfigDeps generates glib-2.0.pc / gio-2.0.pc WITHOUT the tool
        # variables; meson's gnome module reads glib_mkenums (glib-2.0.pc) and
        # glib_compile_resources (gio-2.0.pc) → "Could not get pkg-config
        # variable and no default provided". Inject ABSOLUTE paths (the .pc's
        # ${bindir} may point at a different package than the one shipping the
        # tools, e.g. glib vs glib2 in the same graph).
        gbin, _glib_lib = self._glib_tool_dirs()
        if gbin:
            inject = {
                "glib-2.0.pc": ("glib_mkenums", "glib_genmarshal", "gobject_query"),
                "gio-2.0.pc": ("glib_compile_resources", "glib_compile_schemas",
                               "gdbus_codegen"),
            }
            for pc_name, varnames in inject.items():
                pc = os.path.join(self.generators_folder, pc_name)
                if not os.path.isfile(pc):
                    self.output.warning("%s not generated, skip" % pc_name)
                    continue
                with open(pc, encoding="utf-8") as handle:
                    text = handle.read()
                add = []
                for var in varnames:
                    if var + "=" in text:
                        continue
                    tool = os.path.join(gbin, var.replace("_", "-"))
                    if os.path.isfile(tool):
                        add.append("%s=%s\n" % (var, tool))
                if not add:
                    continue
                out, inserted = [], False
                for line in text.splitlines(True):
                    out.append(line)
                    if not inserted and line.startswith("prefix="):
                        out.extend(add)
                        inserted = True
                if not inserted:
                    out.extend(add)
                with open(pc, "w", encoding="utf-8") as handle:
                    handle.write("".join(out))
                self.output.info("%s: injected glib tool variables" % pc_name)
        # fribidi public headers live in include/fribidi/ (gtksourceview.c does
        # #include <fribidi.h>) while fribidi.pc only carries -I${includedir}
        # → append the subdir (gtk4 / gtksourceview5 recipe lesson R9).
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as handle:
                text = handle.read()
            if "include/fribidi" not in text:
                if "Cflags:" in text:
                    text = text.replace("Cflags:", "Cflags: -I${includedir}/fribidi", 1)
                else:
                    text += "Cflags: -I${includedir}/fribidi\n"
                with open(pc, "w", encoding="utf-8") as handle:
                    handle.write(text)
                self.output.info("fribidi.pc: appended -I${includedir}/fribidi")

    def _augment_pcs_intl(self):
        """Append -lintl to every generated .pc whose libs are used to link.

        glib's OHOS package routes gettext through proxy-libintl: its
        include/libintl.h remaps dgettext/bindtextdomain/... to g_libintl_*
        (see glib/include/libintl.h:49), and those are implemented in
        glib/lib/libintl.so — libglib-2.0.so itself only *imports* them.
        PkgConfigDeps regenerates the .pc files from cpp_info and therefore
        drops the -lintl that the packaged glib-2.0.pc carries, so linking
        the shared library (built with -Wl,--no-undefined / -z defs) fails:

            ld.lld: error: undefined symbol: g_libintl_bindtextdomain
            >>> referenced by gtksourceinit.c
            libgtksourceview-4core.a.p/gtksourceinit.c.o:(gtk_source_init)
            ld.lld: error: undefined symbol: g_libintl_dgettext
            >>> referenced by gtksourceutils.c

        gtksourceview 4.8.4 calls bindtextdomain()/dgettext()
        unconditionally (upstream NEWS: "remove ENABLE_NLS option, always
        support gettext translation"), so the link always needs libintl.
        Same fix as the gtkspell3/3.0.10-r3 and gtk/3.24.43 recipes.
        """
        for name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc",
                     "gmodule-2.0.pc", "gtk+-3.0.pc", "gdk-3.0.pc",
                     "gdk-pixbuf-2.0.pc", "atk.pc", "pango-1.0.pc",
                     "pangocairo-1.0.pc", "cairo-gobject.pc", "cairo.pc"):
            pc = os.path.join(self.generators_folder, name)
            if not os.path.isfile(pc):
                continue
            with open(pc, encoding="utf-8") as handle:
                text = handle.read()
            out, changed = [], False
            for line in text.splitlines(True):
                if line.startswith("Libs:") and "-lintl" not in line.split():
                    line = line.rstrip("\r\n") + " -lintl\n"
                    changed = True
                out.append(line)
            if changed:
                with open(pc, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("".join(out))
                self.output.info("%s: appended -lintl" % name)

    # ------------------------------------------------------------------
    # Build / upstream tests / package
    # ------------------------------------------------------------------

    def build(self):
        # ConanFile.run() re-sources conanbuild.sh for every command, so the
        # NINJA / LD_LIBRARY_PATH injection must be re-applied to the already
        # generated conanbuildenv file from here (see _patch_conanbuildenv).
        self._patch_conanbuildenv()
        # E077: sign the glib host tools BEFORE the first meson custom command.
        self._sign_glib_tools()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the headless-runnable subset of the upstream meson testsuite.

        testsuite/meson.build registers 23 g_test binaries. On OHOS every test
        that calls gtk_test_init() aborts with "Failed to open display"
        (HarmonyOS PC has no window system and the Broadway backend's
        unix-socket bind is SELinux-denied), so only the two pure-core stream
        tests — the ones using plain g_test_init() — are executed. The other 21
        are reported as platform-limited, never as failures.
        """
        import subprocess
        runnable = ["test-buffer-input-stream", "test-buffer-output-stream"]
        display_limited = [
            "test-buffer", "test-completion-model", "test-completion-words",
            "test-encoding", "test-file-loader", "test-file-saver", "test-iter",
            "test-language", "test-languagemanager", "test-language-specs",
            "test-mark", "test-printcompositor", "test-regex", "test-region",
            "test-search-context", "test-space-drawer", "test-stylescheme",
            "test-styleschememanager", "test-undo-manager", "test-utils",
            "test-view",
        ]
        _seen, libdirs = set(), []
        for _ref, dep in self.dependencies.items():
            base = getattr(dep, "package_folder", None)
            if not base:
                continue
            for _p in dep.cpp_info.libdirs:
                if not os.path.isabs(_p):
                    _p = os.path.join(base, _p)
                if _p not in libdirs and os.path.isdir(_p):
                    libdirs.append(_p)
        env = dict(os.environ)
        for _extra in ("/system/lib64",
                       "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"):
            if _extra not in env.get("LD_LIBRARY_PATH", ""):
                env["LD_LIBRARY_PATH"] = env.get("LD_LIBRARY_PATH", "") + os.pathsep + _extra
        env["LD_LIBRARY_PATH"] = (os.pathsep.join(libdirs) + os.pathsep
                                  + env.get("LD_LIBRARY_PATH", ""))
        # equivalent of the upstream test_env[] from testsuite/meson.build
        env["GSETTINGS_BACKEND"] = "memory"
        env["NO_AT_BRIDGE"] = "1"
        # build_folder already contains layout.folders.build ("builddir") in
        # conan 2.29; probe both spellings defensively.
        cands = [os.path.join(self.build_folder, "testsuite"),
                 os.path.join(self.source_folder, "builddir", "testsuite")]
        tdir = next((c for c in cands if os.path.isfile(os.path.join(c, "test-regex"))),
                    cands[0])
        env["G_TEST_BUILDDIR"] = tdir
        env["G_TEST_SRCDIR"] = os.path.join(self.source_folder, "testsuite")
        passed, failed = [], []
        for name in runnable:
            exe = os.path.join(tdir, name)
            if not os.path.isfile(exe):
                failed.append((name, "binary missing"))
                continue
            try:
                proc = subprocess.run([exe], cwd=tdir, env=env, timeout=600,
                                      capture_output=True, text=True)
                n_ok = len([l for l in proc.stdout.splitlines() if l.startswith("ok ")])
                n_not = len([l for l in proc.stdout.splitlines() if l.startswith("not ok ")])
                if proc.returncode == 0 and n_not == 0:
                    passed.append((name, n_ok))
                else:
                    failed.append((name, "rc=%d ok=%d not_ok=%d"
                                   % (proc.returncode, n_ok, n_not)))
            except subprocess.TimeoutExpired:
                failed.append((name, "timeout"))
            except OSError as exc:
                failed.append((name, str(exc)))
        self.output.info("UPSTREAM-TESTS: registered=23 passed=%d failed=%d display-limited=%d"
                         % (len(passed), len(failed), len(display_limited)))
        for name, n_ok in passed:
            self.output.info("UPSTREAM-TEST-PASS: %s (%d assertions)" % (name, n_ok))
        for name, reason in failed:
            self.output.warning("UPSTREAM-TEST-FAIL: %s %s" % (name, reason))
        for name in display_limited:
            self.output.info("UPSTREAM-TEST-SKIP-DISPLAY: %s (gtk_test_init needs a display; "
                             "OHOS has no window system and the Broadway socket bind is "
                             "SELinux-denied)" % name)

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_shared_libs()
        self._restore_unstripped_so()

    def _restore_unstripped_so(self):
        # meson install rewrites the rpath and mutates the .so after linking →
        # the linker's self-signature is invalidated and OHOS XPM dlopen then
        # reports "Permission denied". Overwrite the installed library with the
        # pristine builddir artifact (libsoup3 / gtksourceview5 precedent).
        src_dir_cands = [os.path.join(self.build_folder, "gtksourceview"),
                         os.path.join(self.source_folder, "builddir", "gtksourceview")]
        src_dir = next((d for d in src_dir_cands if os.path.isdir(d)), None)
        if not src_dir:
            return
        for src in glob.glob(os.path.join(src_dir, "libgtksourceview-4.so*")):
            if os.path.islink(src):
                continue
            dst = os.path.join(self.package_folder, "lib", os.path.basename(src))
            if os.path.isfile(dst):
                shutil.copy2(src, dst)
                self.output.info("restored pristine %s from the build dir"
                                 % os.path.basename(src))

    def _sign_shared_libs(self):
        # Strip any stale .codesign section and re-sign in place with
        # binary-sign-tool -selfSign 1 (ML-0043).
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'
                     .format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'
                     .format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["gtksourceview-4"]
        incs = [d for d in ("include/gtksourceview-4", "include")
                if os.path.isdir(os.path.join(self.package_folder, d))]
        self.cpp_info.includedirs = incs or ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "gtksourceview-4")
        self.cpp_info.set_property("cmake_target_name", "gtksourceview-4::gtksourceview-4")
        self.cpp_info.set_property("pkg_config_name", "gtksourceview-4")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # resdir: language-specs/ and styles/ are installed under
        # share/gtksourceview-4; consumers either point
        # gtk_source_language_manager_set_search_path() at it or export
        # XDG_DATA_DIRS (the test_package does the latter).
        self.runenv_info.prepend_path("LD_LIBRARY_PATH",
                                      os.path.join(self.package_folder, "lib"))
