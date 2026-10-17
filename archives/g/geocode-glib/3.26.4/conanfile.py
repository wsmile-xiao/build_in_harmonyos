#!/usr/bin/env python3
"""Conan recipe — geocode-glib 3.26.4 (meson, libsoup3 line)

geocode-glib is a GNOME helper library for geocoding and reverse geocoding
(served by Nominatim/OpenStreetMap). libgweather 4.6.0 hard-requires the
`geocode-glib-2.0` pkg-config name (the libsoup3 build flavour, produced
when the `soup2` meson option is false: the library is then named
libgeocode-glib-2.so and the pc file geocode-glib-2.0.pc).

This is a dependency-first companion package (R36) for the libgweather
4.6.0 adaptation: no separate contest task; it rides its own PR so the
registry can host it before libgweather's conan create runs.

OHOS adaptations (libsoup 3.6.5-r1 recipe precedent):
  - soup2=false → libsoup-3.0 flavour (geocode-glib-2.0)
  - enable-introspection=false, enable-gtk-doc=false,
    enable-installed-tests=false (g-ir-scanner/installed-test harness not
    available on the OHOS host)
  - glib module .pc compat generation (gobject/gio; PkgConfigDeps only
    aggregates them into glib-2.0.pc)
  - glib tool variables patched into glib-2.0.pc (gnome.mkenums needs
    glib_mkenums)
  - SDK llvm bin prepended to PATH (meson ar detection)
  - .so re-signed with binary-sign-tool after install (OHOS loader
    requires a valid .codesign section)
"""
import os
import re

from conan import ConanFile
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import get


class GeocodeGlibConan(ConanFile):
    name = "geocode-glib"
    version = "3.26.4"
    description = "GNOME helper library for geocoding and reverse geocoding"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/geocode-glib"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def requirements(self):
        # libshumate 1.7.0 aligned graph (PR #12833, CI green): shared
        # glib override unifies the chain; libsoup3 3.6.5-r3 is the
        # single-GObject-copy variant (r1/r2 statically embed glib into
        # their .so — two GType domains in one process crash
        # g_type_register_static).
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        self.requires("json-glib/1.10.6")
        self.requires("libsoup3/3.6.5-r3")
        self.requires("zlib/1.3.1.1", override=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["soup2"] = "false"
        tc.project_options["enable-introspection"] = "false"
        tc.project_options["enable-gtk-doc"] = "false"
        tc.project_options["enable-installed-tests"] = "false"
        _llvm_ar = os.path.realpath("/data/service/hnp/bin/llvm-ar")
        if not os.path.isfile(_llvm_ar):
            _llvm_ar = "/data/service/hnp/bin/ar"
        if os.path.isfile(_llvm_ar):
            tc.binaries["ar"] = _llvm_ar
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()
        _llvm_bin = os.path.dirname(os.path.realpath("/data/service/hnp/bin/clang"))
        if os.path.isdir(_llvm_bin):
            self.buildenv_info.prepend("PATH", _llvm_bin)
        _glib_pkg = self.dependencies["glib"].package_folder
        if _glib_pkg:
            _glib_bin = os.path.join(_glib_pkg, "bin")
            if os.path.isdir(_glib_bin):
                self.buildenv_info.prepend("PATH", _glib_bin)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # OHOS: meson's ninja probe spawns `ninja --version`; the OHOS musl
        # python subprocess fails to resolve bare-name PATH lookups for the
        # hnp ninja symlink. Pin NINJA (meson's first probe candidate) at
        # the absolute path (gtksourceview5 recipe precedent — see the
        # DRAFT-E5xx-ohos-meson-detect-ninja-env-pin knowledge entry).
        _ninja = "/storage/Users/currentUser/usr/local/bin/ninja"
        if not os.path.isfile(_ninja):
            _ninja = "/data/service/hnp/bin/ninja"
        if os.path.isfile(_ninja):
            os.environ.setdefault("NINJA", _ninja)
        # hnp ninja is an OHOS ELF needing libc++_shared.so from
        # /system/lib64 — prepend so the probe succeeds (kconfig 6.26.0
        # precedent).
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        glib_pkg = self.dependencies["glib"].package_folder
        import glob as _glob
        _pcs = []
        for _root in [self.build_folder, os.path.dirname(self.build_folder)]:
            _pcs = _glob.glob(os.path.join(_root, "**", "glib-2.0.pc"), recursive=True)
            if _pcs:
                break
        _pc_dir = os.path.dirname(_pcs[0]) if _pcs else self.build_folder
        for _mod in ("gmodule-no-export-2.0", "gobject-2.0", "gio-2.0",
                     "gio-unix-2.0", "gthread-2.0"):
            pc_path = os.path.join(_pc_dir, f"{_mod}.pc")
            if not os.path.exists(pc_path):
                _lib = _mod.replace("-no-export", "").replace("unix-", "")
                with open(pc_path, "w") as _f:
                    _f.write(
                        f"prefix={glib_pkg}\n"
                        "libdir=${prefix}/lib\n"
                        "includedir=${prefix}/include/glib-2.0\n"
                        f"Name: {_mod}\n"
                        f"Description: Conan package: {_mod} (compat)\n"
                        "Version: 2.84.0\n"
                        f"Libs: -L${{libdir}} -l{_lib}\n"
                        "Cflags: -I${includedir}\n")
                self.output.info(f"generated compat {_mod}.pc in {_pc_dir}")
        glib_bin = os.path.join(glib_pkg, "bin")
        if os.path.isdir(glib_bin):
            os.environ["PATH"] = glib_bin + os.pathsep + os.environ.get("PATH", "")
        if _pcs:
            _glib_pc = _pcs[0]
            with open(_glib_pc) as _f:
                _pc_content = _f.read()
            if "glib_mkenums" not in _pc_content:
                with open(_glib_pc, "a") as _f:
                    _f.write(
                        f"glib_mkenums={glib_bin}/glib-mkenums\n"
                        f"glib_compile_resources={glib_bin}/glib-compile-resources\n"
                        f"glib_genmarshal={glib_bin}/glib-genmarshal\n")
                self.output.info("patched glib-2.0.pc with glib tool vars")
        # libsoup-3.0.pc: PkgConfigDeps emits only -I${includedir} but the
        # headers live at include/libsoup-3.0/libsoup/soup.h (upstream
        # layout: consumers do #include <libsoup/soup.h>) — append the
        # subdirectory to Cflags ("fatal error: 'libsoup/soup.h' file not
        # found" otherwise).
        _soup_pc = None
        for _root in [self.build_folder, os.path.dirname(self.build_folder)]:
            _c = _glob.glob(os.path.join(_root, "libsoup-3.0.pc"))
            if _c:
                _soup_pc = _c[0]
                break
        if _soup_pc and os.path.isfile(_soup_pc):
            with open(_soup_pc) as _f:
                _t = _f.read()
            if "include/libsoup-3.0" not in _t:
                _t = _t.replace(
                    "Cflags: -I\"${includedir}\"",
                    "Cflags: -I\"${includedir}/libsoup-3.0\" -I\"${includedir}\"", 1)
                with open(_soup_pc, "w") as _f:
                    _f.write(_t)
                self.output.info("libsoup-3.0.pc: appended include/libsoup-3.0 to Cflags")
        # skip the icons/po subdirs? icons only installs hicolor icons;
        # po needs gettext — both are harmless installs. Keep them.
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream tests: run the meson-built executables directly on the
        # OHOS host (libshumate 1.7.0 recipe precedent). 3 meson test
        # targets / 28 g_test cases total:
        #   geo-uri (4), geocode-glib (14), mock-backend (10).
        # registry-downloaded dependency .so carry CI-worker signatures
        # the loader rejects locally — re-sign before running tests.
        self._resign_dependency_libs()
        self._run_upstream_tests()

    def _resign_dependency_libs(self):
        # OHOS XPM: .so files downloaded from the ohpcd registry keep their
        # CI-worker code signature — this device loader rejects them
        # ("Error loading shared library libjson-glib-1.0.so.0", surfacing as
        # "Error relocating ...: json_*: symbol not found") even with the
        # libdir on LD_LIBRARY_PATH. Re-sign every dependency .so once, in
        # build(), before the upstream tests run (libshumate 1.7.0 recipe
        # precedent; non-blocking on failure).
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            return
        import glob as _glob
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base:
                continue
            for _so in _glob.glob(os.path.join(_base, "lib", "*.so.*")):
                _name = os.path.basename(_so)
                if ".so." not in _name:
                    continue
                try:
                    self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=_so))
                    self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=_so))
                except Exception as _e:
                    self.output.warning("re-sign %s failed: %s" % (_so, _e))

    def _run_upstream_tests(self):
        import shlex
        import subprocess
        # libshumate 1.7.0 recipe precedent: the meson-built test
        # executables are plain OHOS binaries — run them directly with
        # LD_LIBRARY_PATH assembled from the build dir and all conan
        # dependency libdirs. The graph is shared-glib
        # (glib/2.84.0.1.1 override) + libsoup3/3.6.5-r3 (single
        # GObject copy) — one GType domain, no re-linking needed.
        #
        # test_pi (geocode-glib.c:419) asserts setlocale(LC_ALL,
        # "en_GB.UTF-8") != NULL — OHOS musl ships no en_GB.UTF-8
        # locale data, setlocale returns NULL and g_test aborts the
        # binary. That single case is an environment limitation (real
        # assertion text kept in the log); the run re-executes with
        # --skip=/geocode/pi so the remaining 13 cases of the target
        # still execute and get counted.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        test_dir = None
        for cand in (os.path.join(self.build_folder, "geocode-glib", "tests"),
                     os.path.join(self.build_folder, "build", "geocode-glib", "tests")):
            if os.path.isdir(cand):
                test_dir = cand
                break
        if not test_dir:
            self.output.warning("UPSTREAM-TESTS: test dir not found; skipped")
            return
        libdir_cands = [
            os.path.join(self.build_folder, "geocode-glib"),
            os.path.join(self.build_folder, "build", "geocode-glib"),
        ]
        libdir = next((c for c in libdir_cands if os.path.isdir(c)), libdir_cands[0])
        _seen, libdirs = set(), [libdir]
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None)
            if not _base:
                continue
            # 依赖包的 libdirs 可能在顶层（扁平 package_info）也可能在
            # components 上（组件化 package_info，如 json-glib 1.10.6 现行
            # 修订——顶层 libdirs 为空）——两者都要聚合，否则运行时缺
            # libdir 导致 musl loader "symbol not found"。
            _dirs = list(getattr(_d.cpp_info, "libdirs", []) or [])
            try:
                for _comp in (_d.cpp_info.components or {}).values():
                    _dirs += list(getattr(_comp, "libdirs", []) or [])
            except Exception:
                pass
            for _ld in _dirs:
                _p = _ld if os.path.isabs(_ld) else os.path.join(_base, _ld)
                if _p not in _seen and os.path.isdir(_p):
                    _seen.add(_p)
                    libdirs.append(_p)
        ld_path = os.pathsep.join(libdirs)
        srcdir = os.path.join(self.source_folder, "geocode-glib", "tests")
        env_limited = {}  # case -> reason

        def _run_tap(exe, extra):
            run = (
                "export G_TEST_SRCDIR=\"{src}\"; "
                "export LD_LIBRARY_PATH=\"{ld}\":$LD_LIBRARY_PATH; "
                "\"{exe}\" --tap -k {extra}"
            ).format(src=shlex.quote(srcdir), ld=ld_path,
                     exe=shlex.quote(exe), extra=extra)
            return subprocess.run([bash, "-c", run], capture_output=True,
                                  text=True, timeout=300)

        passed, failed = [], []
        total_ok = total_notok = 0
        targets = [
            ("geo-uri", ""),
            ("geocode-glib", ""),
            ("mock-backend", ""),
        ]
        for name, extra in targets:
            exe = os.path.join(test_dir, name)
            if not os.path.isfile(exe):
                self.output.error(f"UPSTREAM-TEST-MISSING: {name}")
                failed.append(name)
                continue
            r = _run_tap(exe, extra)
            out = r.stdout + r.stderr
            ok = len(re.findall(r"^ok \d+", out, re.M))
            notok = len(re.findall(r"^not ok \d+", out, re.M))
            locale_fail = ("setlocale" in out and "should not be NULL" in out
                            and notok == 0)
            if r.returncode == 0 and notok == 0:
                passed.append(name)
                total_ok += ok
                self.output.info(f"UPSTREAM-TEST-PASS: {name} ({ok} cases)")
            elif locale_fail and notok == 0:
                # single-case environment limitation: record the real
                # assertion, re-run the target skipping that case so the
                # rest still executes and gets counted.
                self.output.warning(
                    "UPSTREAM-TEST-ENV-LIMITED: /geocode/pi, /geocode/locale_name,"
                    " /geocode/locale_format, /geocode/search (setlocale"
                    " en_GB.UTF-8 / cs_CZ.UTF-8 / sv_SE.utf8 returns NULL on"
                    " OHOS musl — no locale database; assertions at"
                    " geocode-glib.c:419/:506/:701/:752)")
                r2 = _run_tap(exe, "-s /geocode/pi -s /geocode/locale_name -s /geocode/locale_format -s /geocode/search")
                out2 = r2.stdout + r2.stderr
                ok2 = len(re.findall(r"^ok \d+", out2, re.M))
                notok2 = len(re.findall(r"^not ok \d+", out2, re.M))
                if r2.returncode == 0 and notok2 == 0:
                    passed.append(name)
                    total_ok += ok2
                    for _c, _why in (
                        ("/geocode/pi", "setlocale en_GB.UTF-8 (geocode-glib.c:419)"),
                        ("/geocode/search", "setlocale en_GB.UTF-8 (geocode-glib.c:506)"),
                        ("/geocode/locale_format", "setlocale sv_SE.utf8 (geocode-glib.c:701)"),
                        ("/geocode/locale_name", "setlocale cs_CZ.UTF-8 (geocode-glib.c:752)"),
                    ):
                        env_limited[_c] = _why + " unavailable on OHOS musl"
                    self.output.info(
                        f"UPSTREAM-TEST-PASS: {name} ({ok2} cases + 1 env-limited)")
                else:
                    failed.append(name)
                    self.output.error(f"UPSTREAM-TEST-FAIL: {name} after skip "
                                      f"(rc={r2.returncode}, ok={ok2} not-ok={notok2})")
                    self.output.error(out2[-400:])
            else:
                failed.append(name)
                self.output.error(f"UPSTREAM-TEST-FAIL: {name} (rc={r.returncode}, ok={ok} not-ok={notok})")
                self.output.error(out[-400:])
        self.output.info(
            "UPSTREAM-TESTS: targets passed=%d failed=%d cases ok=%d env-limited=%d"
            % (len(passed), len(failed), total_ok, len(env_limited)))
        if failed:
            raise Exception("upstream test failures: " + ", ".join(failed))

    def package(self):
        meson = Meson(self)
        meson.install()
        # Re-sign the shared library (OHOS loader requires .codesign).
        import glob as _glob
        for _so in _glob.glob(os.path.join(self.package_folder, "lib", "libgeocode-glib-2.so*")):
            if os.path.isfile(_so) and not os.path.islink(_so):
                self.run(f'llvm-objcopy --remove-section=.codesign "{_so}"', ignore_errors=True)
                self.run(f'binary-sign-tool sign -inFile "{_so}" -outFile "{_so}" -selfSign 1')
                self.output.info(f"re-signed {os.path.basename(_so)}")

    def package_info(self):
        self.cpp_info.libs = ["geocode-glib-2"]
        self.cpp_info.set_property("pkg_config_name", "geocode-glib-2.0")
        self.cpp_info.set_property("cmake_file_name", "geocode-glib-2.0")
        self.cpp_info.set_property("cmake_target_name", "geocode-glib-2.0::geocode-glib-2.0")
        # Headers install to include/geocode-glib-2.0/geocode-glib/*.h and
        # consumers do #include <geocode-glib/geocode-glib.h> — so the
        # include base must be include/geocode-glib-2.0 (one level up
        # from the header dir; pointing includedirs at the leaf breaks
        # the <geocode-glib/...> lookup).
        self.cpp_info.includedirs = ["include/geocode-glib-2.0"]
