#!/usr/bin/env python3
"""Conan recipe — gtksourceview5 5.22.0 (Meson).

GtkSourceView 5 is the GNOME syntax-highlighting text widget library for
GTK4. Adapted to HarmonyOS PC (aarch64): built against the conan-published
gtk4/4.22.4 (Broadway-only backend), glib/2.84.0.1.1 (shared), libxml2,
pcre2 and fribidi; introspection/vapi/documentation are disabled (OHOS has
no native g-ir-scanner toolchain for cross builds). See notes.md for the
platform notes and the upstream test results.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Gtksourceview5Conan(ConanFile):
    name = "gtksourceview5"
    version = "5.22.0"
    description = "GtkSourceView 5 — GNOME syntax highlighting widget for GTK4 (OHOS adaptation)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gtksourceview"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gtksourceview 5.22 meson dependency() names → conan packages:
        #   glib-2.0/gobject-2.0/gio-2.0 → glib/2.84.0.1.1 (same pin as the
        #       archived gtk4/4.22.4 recipe — the whole gtk4 stack on ohpcd
        #       resolves to glib/2.84.0.1.1 shared; NO glib2/2.88.0 in this
        #       graph, the two packages are ABI-incompatible siblings)
        #   gtk4 → gtk4/4.22.4 (Broadway-only build, published on ohpcd)
        #   libxml-2.0 → libxml2/2.15.3.1
        #   libpcre2-8 → pcre2/10.45 (8-bit component, pkg_config_name
        #       libpcre2-8; override to the glib/2.84.0.1.1 revision's own
        #       pin so the graph unifies — a different pcre2 rev conflicts)
        #   fribidi → fribidi/1.0.16
        # zlib/1.3.1.1 override: unify the graph (gtk4 chain pins zlib/1.3.1.1,
        # glib2-published recipes pull zlib/1.3.1 → version conflict without
        # the override; PIC variant so shared glib links fine).
        self.requires("gtk4/4.22.4")
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # gtk4/4.22.4 发布二进制 conaninfo 绑定 glib2/2.88.0#aa5b8908（R2 教训，
        # libshumate 1.6.3 / gtkmm 配方同款）：override 固定到 ohpcd 发布修订，
        # 整图恢复消费 gtk4 已发布二进制，避免 glib2 从源码重建/图内版本漂移。
        self.requires("glib2/2.88.0#aa5b8908c41279c288b09b5e22282c0e", override=True)
        # E538: harfbuzz/14.2.0.1 发布二进制仅基于 glib:shared=False 构建，与本图
        # glib/2.84.0.1.1 shared=True 不匹配 → 触发源码重建。harfbuzz/14.2.0.1.1.1
        # 修复版的发布二进制 requires glib/2.84.Z（动态，不锁 revision），兼容本图。
        self.requires("harfbuzz/14.2.0.1.1.1", override=True)
        self.requires("libxml2/2.15.3.1")
        self.requires("pcre2/10.45", override=True)
        self.requires("fribidi/1.0.16")
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CI/worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names not on PATH;
        # pin the real tools by ABSOLUTE PATH (same fix as gtk4/glib2 recipes).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        self._tc = tc
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # NEVER strip shared libs: OHOS loader validates the .codesign hash,
        # strip rewrites the .so → dlopen Permission denied (libsoup3 lesson).
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Don't allow meson to fetch network wraps; deps are all conan-provided.
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS has no g-ir-scanner/vapigen cross toolchain and no gi-docgen.
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "false"
        tc.project_options["documentation"] = "false"
        tc.project_options["sysprof"] = "false"
        # tests/testsuite are compiled + run manually in build() (upstream
        # tests need no display for the pure-core ones; the widget tests are
        # skipped as platform-limit, see notes.md).
        tc.project_options["build-testsuite"] = "true"
        tc.project_options["install-tests"] = "false"
        # gdbus-codegen/glib-mkenums/glib-compile-resources must resolve to the
        # glib package's tools (native scripts), not the broken hnp symlinks.
        self._pin_glib_tools()
        # meson's detect_ninja probes 'ninja' and runs `ninja --version`; the
        # hnp ninja ELF needs libc++_shared.so from the OHOS SDK llvm lib dir,
        # and conan's conanbuild env rewrite drops the inherited LD_LIBRARY_
        # PATH → "Could not detect Ninja v1.8.2 or newer" (ninja exits 127
        # with "Error loading shared library libc++_shared.so"). Inject BOTH
        # the NINJA env var (absolute path, first-priority probe) and the SDK
        # lib dir into the build environment (buildenv_info survives conan's
        # env rebuild; os.environ is also set for the current process).
        _ninja = "/data/service/hnp/bin/ninja"
        if not os.path.isfile(_ninja):
            _ninja = shutil.which("ninja") or _ninja
        os.environ["NINJA"] = _ninja
        self.buildenv_info.define_path("NINJA", _ninja)
        _sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(_sdk_lib):
            os.environ["LD_LIBRARY_PATH"] = (
                _sdk_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
            )
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _sdk_lib)
        tc.generate()
        self._patch_conanbuildenv()
        self._forward_pc("pango", "pangoft2", requires="pango")
        self._forward_pc("pango", "pangocairo", requires="pango")
        # gtksourceview meson probes dependency('libpcre2-8'); the pcre2 recipe
        # only declares pkg_config_name=pcre2 → PkgConfigDeps generates pcre2.pc
        # alone. Forward it under libpcre2-8 so the probe resolves.
        self._forward_pc("pcre2", "libpcre2-8", requires="pcre2")
        self._fix_glib_pcs()

    def _sign_glib_tools(self):
        """E077/E486: sign the glib package's host tool ELFs in place.

        OHOS requires host ELF binaries to carry a valid ``.codesign``
        section before the kernel will exec them. The glib Conan
        package ships unsigned build-time tools
        (``glib-compile-resources``, ``glib-mkenums``, ``gdbus-codegen``,
        ``glib-genmarshal`` …) in its ``bin/``. When meson invokes them
        (gnome.gresource()/mkenums custom targets) the exec fails with::

            /bin/sh: .../glib-compile-resources: Operation not permitted
            FAILED: [code=126]

        Fix (vte 0.74.2 recipe precedent): for every ELF under the glib
        package ``bin/`` — remove any stale ``.codesign`` section,
        self-sign in place, restore the executable bit. Done in
        ``build()`` before the first tool invocation.
        """
        if self.settings.os != "OHOS":
            return
        try:
            glib_pkg = self.dependencies["glib"]
        except KeyError:
            return
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")
        if not os.path.isdir(glib_bin):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        signed = 0
        for name in os.listdir(glib_bin):
            binpath = os.path.join(glib_bin, name)
            if not os.path.isfile(binpath) or os.path.islink(binpath):
                continue
            try:
                with open(binpath, "rb") as f:
                    if f.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run(f'{objcopy} --remove-section .codesign "{binpath}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{binpath}" -outFile "{binpath}" -selfSign 1 2>/dev/null || true')
            self.run(f'chmod a+x "{binpath}" 2>/dev/null || true')
            signed += 1
        self.output.info(f"signed {signed} glib host tool ELF(s) in place")

    def _patch_conanbuildenv(self):
        # ⚠️ ConanFile.run() wraps every command with `source conanbuild.sh`
        # (env="conanbuild" default) — os.environ modifications in build() are
        # discarded. The conanbuildenv-{settings}.sh is written by VirtualBuildEnv
        # AFTER generate(), so the ONLY working injection point is appending to
        # the already-generated file, from build() before the first meson call.
        # Why NINJA + LD: the hnp ninja ELF needs libc++_shared.so; the OHOS
        # musl loader does NOT search /system/lib64 for it in the conanbuild
        # child processes (linker namespace), and the SDK llvm/lib dir has no
        # libc++_shared.so either — the ONLY fix is explicitly prepending
        # /system/lib64 to LD_LIBRARY_PATH (the usr/local/bin/ninja wrapper
        # does exactly this).
        import glob as _glob
        for _envf in _glob.glob(os.path.join(self.generators_folder,
                                             "conanbuildenv-*.sh")):
            with open(_envf, encoding="utf-8") as _f:
                _text = _f.read()
            _append = ""
            if 'NINJA=' not in _text:
                _append += '\nexport NINJA="/data/service/hnp/bin/ninja"\n'
            if 'export LD_LIBRARY_PATH="/system/lib64' not in _text:
                _append += ('export LD_LIBRARY_PATH="/system/lib64'
                            ':/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18'
                            '/ohos/native/llvm/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n')
            if _append:
                if not _text.endswith("\n"):
                    _text += "\n"
                _text += _append
                with open(_envf, "w", encoding="utf-8") as _f:
                    _f.write(_text)
                self.output.info("conanbuildenv patched: NINJA + /system/lib64 injected (%s)" %
                                 os.path.basename(_envf))

    def _pin_glib_tools(self):
        # glib/2.84.0.1.1 package bin holds the meson gnome module tools
        # (glib-mkenums/glib-genmarshal/gdbus-codegen/glib-compile-resources …).
        # Pin them into the meson native file [binaries] so gnome.genmarshal()/
        # mkenums_simple()/compile_resources() resolve without pkg-config
        # variable fallback (the conan-generated glib-2.0.pc has none), and
        # prepend the glib bin to PATH. The glib tools are signed OHOS ELF
        # executables or python3 scripts; they need glib's own shared libs on
        # LD_LIBRARY_PATH to exec ("Error loading shared library libgio-2.0.so.0"
        # otherwise — gtk4 recipe lesson).
        dep = self.dependencies.get("glib")
        if not dep or not getattr(dep, "package_folder", None):
            return
        gbin = os.path.join(dep.package_folder, "bin")
        glib_lib = os.path.join(dep.package_folder, "lib")
        os.environ["LD_LIBRARY_PATH"] = (
            glib_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        if os.path.isdir(gbin):
            os.environ["PATH"] = gbin + os.pathsep + os.environ.get("PATH", "")
        for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                     "glib-compile-resources", "glib-compile-schemas",
                     "gio-querymodules", "glib-genmarshal"):
            tool_path = os.path.join(gbin, tool)
            if os.path.isfile(tool_path):
                self._tc.binaries[tool] = tool_path
        self.output.info("PATH/LD_LIBRARY_PATH prepended with glib bin/lib: %s" % gbin)

    def _fix_glib_pcs(self):
        # PkgConfigDeps generates glib-2.0.pc/gio-2.0.pc WITHOUT the tool
        # variables. gtksourceview's gnome.genmarshal reads glib_genmarshal
        # (via glib-2.0.pc) and gnome.compile_resources reads
        # glib_compile_resources (via gio-2.0.pc); missing → "Could not get
        # pkg-config variable and no default provided". Inject them pointing
        # at the glib package's bin (pinned in the native file too — belt and
        # suspenders).
        dep = self.dependencies.get("glib")
        gbin = os.path.join(dep.package_folder, "bin") if dep and getattr(dep, "package_folder", None) else None
        inject = {
            "glib-2.0.pc": {
                "glib_mkenums": "${bindir}/glib-mkenums",
                "glib_genmarshal": "${bindir}/glib-genmarshal",
                "gobject_query": "${bindir}/gobject-query",
            },
            "gio-2.0.pc": {
                "glib_compile_resources": "${bindir}/glib-compile-resources",
                "glib_compile_schemas": "${bindir}/glib-compile-schemas",
                "gdbus_codegen": "${bindir}/gdbus-codegen",
            },
        }
        for pc_name, vars_map in inject.items():
            pc = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc):
                self.output.warning("fix %s: not generated, skip" % pc_name)
                continue
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if all(k + "=" in text for k in vars_map):
                continue
            lines = text.splitlines(True)
            out = []
            for line in lines:
                out.append(line)
                if line.startswith("bindir="):
                    for k, v in vars_map.items():
                        if k + "=" not in text:
                            out.append("%s=%s\n" % (k, v))
            with open(pc, "w", encoding="utf-8") as _f:
                _f.write("".join(out))
            self.output.info("%s: injected tool variables" % pc_name)
        # fribidi public headers live in include/fribidi/ (gtksourceview.c
        # does #include <fribidi.h>) but fribidi.pc only carries
        # -I${includedir}; append the subdir (gtk4 recipe lesson R9).
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if os.path.isfile(pc):
            with open(pc, encoding="utf-8") as _f:
                text = _f.read()
            if "include/fribidi" not in text:
                if "Cflags:" in text:
                    text = text.replace("Cflags:", "Cflags: -I${includedir}/fribidi", 1)
                else:
                    text += "Cflags: -I${includedir}/fribidi\n"
                with open(pc, "w", encoding="utf-8") as _f:
                    _f.write(text)
                self.output.info("fribidi.pc: appended -I${includedir}/fribidi")

    def _forward_pc(self, src_name, dst_name, requires=None, extra_lines=None):
        # Forward a dependency .pc under an alternate name so meson
        # dependency(dst_name) probes hit it (gtk4's stack needs pangoft2 /
        # pangocairo which the pango recipe does not expose separately).
        src = os.path.join(self.generators_folder, "%s.pc" % src_name)
        if not os.path.isfile(src):
            self.output.warning("forward %s: %s.pc not generated, skip" % (dst_name, src_name))
            return
        dst = os.path.join(self.generators_folder, "%s.pc" % dst_name)
        if os.path.isfile(dst):
            return
        with open(src, encoding="utf-8") as _f:
            body = _f.read()
        body = re.sub(r"^Name: .*$", "Name: %s" % dst_name, body, count=1, flags=re.M)
        if requires and "Requires:" not in body:
            body += "Requires: %s\n" % requires
        if extra_lines:
            body += "\n%s\n" % "\n".join(extra_lines)
        with open(dst, "w", encoding="utf-8") as _f:
            _f.write(body)
        self.output.info("forwarded pkg-config: %s.pc -> %s.pc" % (src_name, dst_name))

    def build(self):
        # ⚠️ ConanFile.run() wraps every command with `source conanbuild.sh`
        # (env="conanbuild" default); the conanbuildenv-*.sh file is written by
        # VirtualBuildEnv AFTER generate() — so the ONLY working injection
        # point for NINJA is HERE, appending to the already-generated file
        # before the first meson call.
        self._patch_conanbuildenv()
        # E077: sign the glib package's host tool ELFs in place BEFORE the
        # first meson custom command — glib-compile-resources & friends are
        # unsigned OHOS binaries; the kernel refuses to exec them
        # ("Operation not permitted", code 126) and every gnome.gresource()
        # custom target dies (vte 0.74.2 recipe precedent: _sign_glib_tools).
        self._sign_glib_tools()
        apply_conandata_patches(self)
        # OHOS: meson's ninja probe spawns `ninja --version`; /data/service/hnp/bin/ninja
        # is first on the conan build PATH and needs libc++_shared.so which lives in
        # /system/lib64 (the SDK llvm/lib top dir does NOT carry it). The usr/local
        # wrapper handles that but loses to hnp on PATH order. Pin NINJA (meson's
        # first probe candidate) at the wrapper and prepend /system/lib64 so the
        # probe succeeds regardless of the outer shell env.
        _ninja = shutil.which("ninja")
        if not _ninja:
            _ninja = "/storage/Users/currentUser/usr/local/bin/ninja"
        if os.path.isfile(_ninja):
            os.environ.setdefault("NINJA", _ninja)
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream testsuite (26 g_test binaries registered in
        # testsuite/meson.build) — cross-built OHOS binaries cannot run on
        # the build host via `meson test`. Run the pure-core (no-widget)
        # subset directly on this OHOS host with LD_LIBRARY_PATH injected
        # (R30/test discipline: run what the platform can run, report the
        # rest as platform-limited). Results are recorded in notes.md.
        self._run_upstream_tests(meson)

    def _run_upstream_tests(self, meson):
        import subprocess
        # Upstream testsuite registers 26 g_test targets in testsuite/meson.build.
        # OHOS platform limit (measured, see notes.md): every test that calls
        # gtk_test_init()/gtk_init() aborts with "Failed to open display" —
        # HarmonyOS PC has no window system, and the Broadway backend's
        # unix-socket bind is SELinux-denied (EPERM), so no display server
        # can run. The pure-core tests that only exercise non-widget API
        # (streams) run green headless. Run them and report the rest as
        # display-limited (consumer test_package covers the manager APIs).
        runnable = ["test-buffer-input-stream", "test-buffer-output-stream"]
        display_limited = [
            "test-buffer", "test-completion-words", "test-encoding", "test-iter",
            "test-language", "test-languagemanager", "test-mark", "test-regex",
            "test-region", "test-snippets", "test-utils", "test-stylescheme",
            "test-styleschememanager", "test-vim-state", "test-vim-text-object",
            "test-file-loader", "test-file-saver", "test-language-specs",
            "test-printcompositor", "test-search-context", "test-space-drawer",
            "test-syntax", "test-view", "test-vim-input",
        ]
        libdir_cands = [
            os.path.join(self.build_folder, "gtksourceview"),
            os.path.join(self.build_folder, "builddir", "gtksourceview"),
        ]
        libdir = next((c for c in libdir_cands if os.path.isdir(c)), libdir_cands[0])
        # collect dependency libdirs (glib/gtk4/… .so runpaths)
        _seen, libdirs = set(), [libdir]
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base:
                continue
            for _p in _d.cpp_info.libdirs:
                if not os.path.isabs(_p):
                    _p = os.path.join(_base, _p)
                if _p not in libdirs and os.path.isdir(_p):
                    libdirs.append(_p)
        env = dict(os.environ)
        # OHOS: the test binaries are OHOS ELF processes spawned via python
        # subprocess — the musl loader needs /system/lib64 (libc++_shared.so
        # etc.) and the SDK llvm lib dir explicitly.
        for _extra in ("/system/lib64",
                       "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"):
            if _extra not in env.get("LD_LIBRARY_PATH", ""):
                env["LD_LIBRARY_PATH"] = env.get("LD_LIBRARY_PATH", "") + os.pathsep + _extra
        env["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        # build_folder follows layout.folders.build ("builddir"), i.e. the
        # meson build root; probe both spellings defensively (conan 2.29
        # build_folder = <src>/builddir, older semantics <src>).
        cands = [
            os.path.join(self.build_folder, "testsuite"),
            os.path.join(self.build_folder, "builddir", "testsuite"),
        ]
        tdir = next((c for c in cands if os.path.isfile(os.path.join(c, "test-regex"))), cands[0])
        passed, failed = [], []
        for t in runnable:
            exe = os.path.join(tdir, t)
            if not os.path.isfile(exe):
                failed.append((t, "binary missing"))
                continue
            try:
                proc = subprocess.run([exe], cwd=tdir, env=env, timeout=900,
                                      capture_output=True, text=True)
                n_ok = len([l for l in proc.stdout.splitlines() if l.startswith("ok ")])
                n_not = len([l for l in proc.stdout.splitlines() if l.startswith("not ok ")])
                if proc.returncode == 0 and n_not == 0:
                    passed.append((t, n_ok))
                else:
                    failed.append((t, "rc=%d ok=%d not_ok=%d" % (proc.returncode, n_ok, n_not)))
            except subprocess.TimeoutExpired:
                failed.append((t, "timeout"))
            except OSError as e:
                failed.append((t, str(e)))
        self.output.info(
            "UPSTREAM-TESTS: registered=26 passed=%d failed=%d display-limited=%d"
            % (len(passed), len(failed), len(display_limited)))
        for t, n in passed:
            self.output.info("UPSTREAM-TEST-PASS: %s (%d assertions)" % (t, n))
        for t, rc in failed:
            self.output.warning("UPSTREAM-TEST-FAIL: %s %s" % (t, rc))
        for t in display_limited:
            self.output.info("UPSTREAM-TEST-SKIP-DISPLAY: %s (gtk_test_init needs a display; "
                             "OHOS has no window system and Broadway socket bind is SELinux-denied)" % t)
        if failed:
            self.output.warning("upstream runnable tests with failures: %s"
                                % ", ".join(t for t, _ in failed))

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()
        self._restore_unstripped_so()

    def _restore_unstripped_so(self):
        # meson install rewrites rpath and mutates .so post-link → the linker
        # self-sign breaks; OHOS XPM dlopen then reports Permission denied.
        # Overwrite the installed lib with the ORIGINAL builddir artifact
        # (libsoup3 lesson) for the main library.
        for _lib in ("libgtksourceview-5.so.0.12.0",):
            _cands = [
                os.path.join(self.build_folder, "gtksourceview", _lib),
                os.path.join(self.build_folder, "builddir", "gtksourceview", _lib),
            ]
            _src = next((c for c in _cands if os.path.exists(c)), None)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if _src and os.path.exists(_dst):
                shutil.copy2(_src, _dst)

    def _sign_shared_libs(self):
        # Strip old .codesign + binary-sign-tool -selfSign 1 re-sign (ML-0043).
        import glob as _glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["gtksourceview-5"]
        self.cpp_info.includedirs = ["include/gtksourceview-5"]
        self.cpp_info.set_property("pkg_config_name", "gtksourceview-5")
        self.cpp_info.set_property("cmake_file_name", "gtksourceview-5")
        self.cpp_info.set_property("cmake_target_name", "gtksourceview-5::gtksourceview-5")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # Runtime env for consumers: the package ships shared libs whose deps
        # (glib/gtk4 .so) live in conan package dirs — expose own libdir.
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
