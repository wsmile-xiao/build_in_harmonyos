#!/usr/bin/env python3
"""Conan recipe — libshumate 1.7.0 (Meson).

libshumate is the GNOME map widget library for GTK4 (successor of libchamplain).
Adapted to HarmonyOS PC (aarch64): built against the conan-published gtk4/4.22.4
(Broadway-only), glib/2.84.0.1.1 (shared), cairo, sqlite3, libsoup3, json-glib,
protobuf-c; introspection/vapi/gtk_doc are disabled (no cross g-ir-scanner on
OHOS). gperf (host tool) generates the vector-expression parser. See notes.md
for the platform notes and the upstream test results.
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


class LibshumateConan(ConanFile):
    name = "libshumate"
    version = "1.7.0"
    description = "libshumate — GNOME map widget library for GTK4 (OHOS adaptation)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libshumate"

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
        # libshumate 1.7.0 meson dependency() names → conan packages:
        #   glib-2.0/gobject-2.0/gio-2.0 → glib/2.84.0.1.1 (same pin as the
        #       archived gtk4/4.22.4 recipe — the whole gtk4 stack on ohpcd
        #       resolves to glib/2.84.0.1.1 shared)
        #   cairo → cairo/1.18.4
        #   sqlite3 → sqlite3/3.49.1 (pinned to the libsoup3 3.6.5-r1 revision's
        #       own pin — a different sqlite3 rev would conflict in the graph)
        #   gtk4 → gtk4/4.22.4 (Broadway-only build)
        #   libsoup-3.0 → libsoup3/3.6.5-r1
        #   json-glib-1.0 → json-glib/1.10.6
        #   libprotobuf-c → protobuf-c/1.5.1 (pkg_config_name libprotobuf-c)
        # glib/2.84.0.1.1 shared override unifies the graph (libsoup3 pins
        # glib2/2.88.0 internally; gtk4 chain pins glib/2.84.0.1.1 — the gtk4
        # recipe pairs them by relying on both pkg-config names being
        # available; here we align to the gtk4/glib pin like gtksourceview5).
        # zlib/1.3.1.1 override: PIC variant, unify graph.
        self.requires("gtk4/4.22.4")
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("cairo/1.18.4")
        # ⚠️ cairo-gobject real package (glib=enabled): libshumate public
        # headers include <cairo-gobject.h> (shumate-point.h etc.); the
        # plain cairo/1.18.4 (glib=disabled) ships a stub header whose
        # #error branch ("Cairo was not compiled with support for GObject")
        # breaks consumers (gtk4 recipe precedent — same fix, -r3 CI round).
        self.requires("cairo-gobject/1.18.4")
        # sqlite3: normal require (PkgConfigDeps only generates .pc for DIRECT
        # deps; an override-only pin would leave meson's dependency('sqlite3')
        # unresolvable). libsoup3 also pins 3.49.1 so the graph unifies.
        self.requires("sqlite3/3.49.1")
        # ⚠️ libsoup3/3.6.5-r3 (NOT -r1/-r2): -r1/-r2 statically embed glib2's
        # GObject and export 4100+ g_* symbols from libsoup-3.0.so → at runtime
        # a SECOND GObject type system registers and every g_test binary dies
        # with "cannot register existing type 'gchar'" (measured: 16/16 tests
        # 0-pass). -r3 requires glib/2.84.0.1.1 shared=True, sharing the same
        # shared glib as the gtk4 chain — single GObject copy.
        self.requires("libsoup3/3.6.5-r3")
        self.requires("json-glib/1.10.6")
        self.requires("protobuf-c/1.5.1")
        self.requires("zlib/1.3.1.1", override=True)

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
        tc.project_options["wrap_mode"] = "nodownload"
        # OHOS has no g-ir-scanner/vapigen cross toolchain and no gi-docgen.
        tc.project_options["gir"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["demos"] = "false"
        tc.project_options["sysprof"] = "disabled"
        # gperf is a hard host-tool requirement (vector-expression parser).
        _gperf = shutil.which("gperf") or "/data/service/hnp/bin/gperf"
        if os.path.isfile(_gperf):
            tc.binaries["gperf"] = _gperf
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
        # glib tools (glib-mkenums etc.) resolve from the glib package bin.
        self._pin_glib_tools()
        tc.generate()
        self._patch_conanbuildenv()
        self._forward_pc("pango", "pangoft2", requires="pango")
        self._forward_pc("pango", "pangocairo", requires="pango")
        self._fix_glib_pcs()
        self._fix_cairo_gobject_pc()

    def _fix_cairo_gobject_pc(self):
        # R15 fix (gtk4 recipe precedent): cairo-gobject.h does
        # `#if CAIRO_HAS_GOBJECT_FUNCTIONS ... #else #error`; the include dir
        # order on OHOS can put the glib=disabled cairo include first, so the
        # macro is undefined and the stub #error branch is taken. Inject
        # -DCAIRO_HAS_GOBJECT_FUNCTIONS=1 into cairo-gobject.pc Cflags so the
        # real gobject branch is used by consumers.
        pc = os.path.join(self.generators_folder, "cairo-gobject.pc")
        if not os.path.isfile(pc):
            return
        with open(pc, encoding="utf-8") as _f:
            text = _f.read()
        if "CAIRO_HAS_GOBJECT_FUNCTIONS=1" in text:
            return
        if "Cflags:" in text:
            text = text.replace("Cflags:", "Cflags: -DCAIRO_HAS_GOBJECT_FUNCTIONS=1", 1)
        else:
            text += "Cflags: -DCAIRO_HAS_GOBJECT_FUNCTIONS=1\n"
        with open(pc, "w", encoding="utf-8") as _f:
            _f.write(text)
        self.output.info("cairo-gobject.pc: appended -DCAIRO_HAS_GOBJECT_FUNCTIONS=1 to Cflags")

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
        # glib/2.84.0.1.1 package bin holds the meson gnome module tools;
        # pin them into the meson native file [binaries] and prepend PATH /
        # LD_LIBRARY_PATH (tools are signed OHOS ELF needing glib's .so).
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
                     "gio-querymodules"):
            tool_path = os.path.join(gbin, tool)
            if os.path.isfile(tool_path):
                self._tc.binaries[tool] = tool_path
        self.output.info("PATH/LD_LIBRARY_PATH prepended with glib bin/lib: %s" % gbin)

    def _resign_dependency_libs(self):
        # ⚠️ OHOS XPM: .so files downloaded from the ohpcd registry keep their
        # CI-worker code signature — the local device loader rejects them
        # ("Error loading shared library libjson-glib-1.0.so.0") even though
        # the file is on LD_LIBRARY_PATH. Re-sign EVERY dependency .so (strip
        # old .codesign + binary-sign-tool -selfSign 1) once, in build(),
        # before the upstream tests run (gtk4 recipe's glib-bin re-sign
        # pattern, extended to lib dirs). Non-blocking on failure.
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        import glob as _glob
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base:
                continue
            for _so in _glob.glob(os.path.join(_base, "lib", "*.so.*")) + \
                       _glob.glob(os.path.join(_base, "lib", "*.so")):
                _name = os.path.basename(_so)
                if _name.endswith(".so") or ".so." not in _name:
                    continue
                try:
                    self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=_so))
                    self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=_so))
                except Exception as _e:
                    self.output.warning("re-sign %s failed: %s" % (_so, _e))

    def _sign_glib_tools(self):
        """E077/E486: sign the glib package's host tool ELFs in place.

        OHOS requires host ELF binaries to carry a valid ``.codesign``
        section before the kernel will exec them. The glib Conan package
        ships unsigned/stale-signed build-time tools (glib-compile-resources,
        glib-mkenums, gdbus-codegen, glib-genmarshal …) in its ``bin/``.
        When meson invokes them (gnome.gresource()/mkenums custom targets)
        the exec fails with::

            /bin/sh: .../glib-compile-resources: Operation not permitted
            FAILED: [code=126]

        Fix (vte 0.74.2 / gtksourceview5 5.22.0 recipe precedent): for every
        ELF under the glib package ``bin/`` — remove any stale ``.codesign``
        section, self-sign in place. Done in ``build()`` before the first
        tool invocation.
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
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        signed = 0
        for name in os.listdir(glib_bin):
            binpath = os.path.join(glib_bin, name)
            if not os.path.isfile(binpath) or os.path.islink(binpath):
                continue
            try:
                with open(binpath, "rb") as f:
                    if f.read(4) != b"\x7fELF":
                        continue  # python3 scripts — leave alone
            except OSError:
                continue
            try:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=binpath))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=binpath))
                signed += 1
            except Exception as e:
                self.output.warning("re-sign %s failed: %s" % (binpath, e))
        if signed:
            self.output.info("re-signed %d glib host tools in place" % signed)

    def _fix_glib_pcs(self):
        # Inject the tool variables into the conan-generated glib-2.0.pc /
        # gio-2.0.pc (gnome.mkenums reads glib_mkenums; missing → "Could not
        # get pkg-config variable and no default provided"). Also append the
        # fribidi include subdir (headers live in include/fribidi/).
        dep = self.dependencies.get("glib")
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
        # dependency(dst_name) probes hit it (pango recipe does not expose
        # pangoft2/pangocairo separately).
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
        # before the first meson call. (NINJA= env var makes meson's
        # detect_ninja use the absolute path; the hnp ninja ELF needs
        # libc++_shared.so from the SDK lib dir on LD_LIBRARY_PATH.)
        self._patch_conanbuildenv()
        # E077: sign glib host tools BEFORE meson invokes them (custom targets
        # exec glib-compile-resources / glib-mkenums — stale CI-worker
        # signatures fail with "Operation not permitted" code=126).
        self._sign_glib_tools()
        # Re-sign dependency .so files (registry downloads carry CI-worker
        # signatures the local XPM rejects) BEFORE the upstream tests run.
        self._resign_dependency_libs()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream tests (16 g_test targets registered in tests/meson.build).
        # 13 of them only call g_test_init (no display); 3 (map/marker/
        # marker-layer) call gtk_init() which needs a display server — run
        # them all on this OHOS host, report the display-limited ones.
        self._run_upstream_tests(meson)

    def _run_upstream_tests(self, meson):
        import subprocess
        all_tests = [
            "coordinate", "data-source-request", "file-cache",
            "location", "map", "marker", "marker-layer", "memory-cache",
            "vector-expression", "vector-index", "vector-reader",
            "vector-renderer", "vector-sprite-sheet", "vector-style",
            "vector-value", "viewport",
        ]
        gtk_init_tests = {"map", "marker", "marker-layer"}
        libdir_cands = [
            os.path.join(self.build_folder, "shumate"),
            os.path.join(self.build_folder, "builddir", "shumate"),
        ]
        libdir = next((c for c in libdir_cands if os.path.isdir(c)), libdir_cands[0])
        _seen, libdirs = set(), [libdir]
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base:
                continue
            _dirs = list(_d.cpp_info.libdirs)
            # ⚠️ packages using cpp_info.components (glib/json-glib/libsoup3…)
            # keep their libdirs on the COMPONENTS, not the top-level cpp_info
            # — VirtualRunEnv/the plain iteration miss them. Collect from
            # every component too.
            try:
                for _comp in _d.cpp_info.components.values():
                    _dirs.extend(_comp.libdirs or [])
            except Exception:
                pass
            for _p in _dirs:
                if not os.path.isabs(_p):
                    _p = os.path.join(_base, _p)
                if _p not in libdirs and os.path.isdir(_p):
                    libdirs.append(_p)
        env = dict(os.environ)
        # OHOS: the test binaries are OHOS ELF processes spawned via python
        # subprocess — the musl loader needs /system/lib64 (libc++_shared.so
        # etc.) and the SDK llvm lib dir explicitly (LD_LIBRARY_PATH of the
        # parent conanbuild env is incomplete for child processes).
        for _extra in ("/system/lib64",
                       "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"):
            if _extra not in env.get("LD_LIBRARY_PATH", ""):
                env["LD_LIBRARY_PATH"] = env.get("LD_LIBRARY_PATH", "") + os.pathsep + _extra
        env["LD_LIBRARY_PATH"] = os.pathsep.join(libdirs) + os.pathsep + env.get("LD_LIBRARY_PATH", "")
        # G_TEST_OPTION_ISOLATE_DIRS tests (file-cache) write into the cwd.
        tdir_cands = [
            os.path.join(self.build_folder, "tests"),
            os.path.join(self.build_folder, "builddir", "tests"),
        ]
        tdir = next((c for c in tdir_cands if os.path.isfile(os.path.join(c, "coordinate"))), tdir_cands[0])
        passed, failed, skipped = [], [], []
        for t in all_tests:
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
                elif t in gtk_init_tests and ("Failed to open display" in proc.stderr
                                              or "Failed to open display" in proc.stdout):
                    skipped.append(t)
                else:
                    failed.append((t, "rc=%d ok=%d not_ok=%d" % (proc.returncode, n_ok, n_not)))
            except subprocess.TimeoutExpired:
                failed.append((t, "timeout"))
            except OSError as e:
                failed.append((t, str(e)))
        self.output.info(
            "UPSTREAM-TESTS: registered=16 passed=%d failed=%d display-limited=%d"
            % (len(passed), len(failed), len(skipped)))
        for t, n in passed:
            self.output.info("UPSTREAM-TEST-PASS: %s (%d assertions)" % (t, n))
        for t in skipped:
            self.output.info("UPSTREAM-TEST-SKIP-DISPLAY: %s (gtk_init needs a display; "
                             "OHOS has no window system and Broadway socket bind is SELinux-denied)" % t)
        for t, rc in failed:
            self.output.warning("UPSTREAM-TEST-FAIL: %s %s" % (t, rc))
        if failed:
            self.output.warning("upstream tests with failures: %s"
                                % ", ".join(t for t, _ in failed))

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()
        self._restore_unstripped_so()

    def _restore_unstripped_so(self):
        # meson install rewrites rpath and mutates .so post-link → the linker
        # self-sign breaks; overwrite with the ORIGINAL builddir artifact
        # (libsoup3 lesson), then re-sign below happens on the copy.
        import glob as _glob
        src_dir_cands = [
            os.path.join(self.build_folder, "shumate"),
            os.path.join(self.build_folder, "builddir", "shumate"),
        ]
        src_dir = next((c for c in src_dir_cands if os.path.isdir(c)), None)
        if not src_dir:
            return
        for _src in _glob.glob(os.path.join(src_dir, "libshumate-1.so.*")):
            _name = os.path.basename(_src)
            _dst = os.path.join(self.package_folder, "lib", _name)
            if os.path.exists(_dst):
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
        self.cpp_info.libs = ["shumate-1.0"]
        # meson installs headers to include/shumate-1.0 (NOT libshumate-1.0)
        self.cpp_info.includedirs = ["include/shumate-1.0"]
        self.cpp_info.set_property("pkg_config_name", "shumate-1.0")
        self.cpp_info.set_property("cmake_file_name", "shumate-1.0")
        self.cpp_info.set_property("cmake_target_name", "shumate-1.0::shumate-1.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
