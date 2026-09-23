#!/usr/bin/env python3
"""Conan recipe -- xraylib 4.2.1 (Meson, core C library only).

xraylib provides 50+ C functions for X-ray matter interactions (cross
sections, line/edge energies, fluorescence yields, scattering factors,
refractive indices, crystal diffraction, radionuclides, ...).

Build: Meson + Ninja (upstream ships meson.build alongside autotools).
The Meson route needs no autoreconf/perl/autoconf bootstrap, so it is
immune to the broken conan automake/1.18 wrapper observed on HMBS
workers (bin/aclocal calling a missing bin/.aclocal-real, exit 126)
and to the autoconf mktemp storms on the read-only /tmp.

Options mirror upstream meson_options.txt: Fortran/Python bindings are
explicitly disabled; the C++ test programs (cplusplus/tests, 8 files)
build automatically when a C++ compiler exists and are counted as part
of the upstream suite together with the 27 C tests in tests/.
No external dependencies besides system libm.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class XraylibConan(ConanFile):
    name = "xraylib"
    version = "4.2.1"
    description = "Library for X-ray matter interaction cross sections (XRF applications)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/tschoonj/xraylib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    topics = ("xray", "xrf", "physics", "cross-section")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # Upstream is a dual-build project (autotools + meson >= 0.60).
        # Meson needs no generated-configure bootstrap, so a single
        # tool_require replaces the automake/autoconf/libtool/perl quartet
        # that kept failing on HMBS workers (missing .aclocal-real).
        self.tool_requires("meson/1.11.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xraylib is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # Core C library only: no Fortran/Python bindings.
        tc.project_options["fortran-bindings"] = "disabled"
        tc.project_options["python-bindings"] = "disabled"
        tc.project_options["python-numpy-bindings"] = "disabled"
        tc.generate()
        self._fix_meson_compilers()
        self._pin_meson_archiver()

        # Writable TMPDIR for meson/ninja compiler probes and tests.
        # HMBS injects a task-private TMPDIR/TMP/TEMP; reuse it when valid,
        # otherwise fall back to a build-folder subdir (always writable).
        # Meson/ninja honor TMPDIR via mktemp, so no hardcoded /tmp remains
        # on the recipe side (readonly_tmp platform diagnosis).
        tmp = self._writable_tmpdir()
        Path(tmp).mkdir(parents=True, exist_ok=True)
        bash = shutil.which("bash") or "/bin/sh"
        cc = self._resolve_compiler("c", ("clang", "cc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++"))
        self.output.info("resolved C compiler: %s" % cc)
        self.output.info("resolved C++ compiler: %s" % cxx)
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("SHELL", bash)
        env.define("CONFIG_SHELL", bash)
        env.define("CC", cc)
        env.define("CXX", cxx)
        for key in (
            "HMBS_AUTOCONF_MKTEMP_FALLBACK",
            "HMBS_CAP_LOCAL_MKTEMP",
            "HMBS_TMPDIR",
            "HMBS_CAP_CHMOD",
            "HMBS_CAP_HARDLINK",
        ):
            val = os.environ.get(key)
            if val:
                env.define(key, val)
        env.vars(self, scope="build").save_script("hmbs_env")

    def _writable_tmpdir(self):
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder or ".", "tmp")
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        return d

    def _resolve_compiler(self, key, fallbacks):
        """Return a working compiler path, tolerating a stale profile.

        The repo profile hardcodes /data/service/hnp/bin/clang(++); on some
        preflight workers that file is gone and meson setup fails with
        "Unknown compiler(s): [['/data/service/hnp/bin/clang']]". Prefer the
        conf value only when it names an existing executable, otherwise fall
        back to HMBS-prepended PATH plus the OHOS SDK llvm dir. Never raises:
        returns the raw conf value (or first fallback name) so the toolchain
        can still report the real error. Netcode 1.4.3 precedent.
        """
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            executables = {}
        cand = executables.get(key)
        if cand:
            if os.path.isabs(cand):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except OSError:
                    pass
            else:
                found = shutil.which(cand)
                if found:
                    return found
                return cand
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        for sdk in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
            for name in fallbacks:
                p = os.path.join(sdk, name)
                if os.path.isfile(p):
                    return p
        for d in (os.environ.get("HMBS_LLVM_BIN", ""),
                  "/data/service/hnp/bin"):
            if d:
                for name in fallbacks:
                    p = os.path.join(d, name)
                    if os.path.isfile(p):
                        return p
        return cand or fallbacks[0]

    def _fix_meson_compilers(self):
        """Rewrite c/cpp in both meson machine files to working compilers.

        MesonToolchain copies tools.build:compiler_executables verbatim into
        conan_meson_native.ini (and cross). When the profile path is stale,
        setup aborts before any compilation. Patch both files in place.
        """
        cc = self._resolve_compiler("c", ("clang", "cc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++"))
        for fname in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, fname)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            orig = content
            for var, val in (("c", cc), ("cpp", cxx)):
                content = re.sub(
                    r"(?m)^(\s*%s\s*=\s*').*?(')" % re.escape(var),
                    lambda m: m.group(1) + val.replace("\\", "/") + m.group(2),
                    content, count=1,
                )
            if content != orig:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.output.info(
                        "patched %s compilers to c=%s cpp=%s" % (fname, cc, cxx))
                except OSError:
                    pass

    def _pin_meson_archiver(self):
        """Pin `ar` in the meson native file next to the profile compiler.

        Meson probes a static archiver while detecting the C toolchain;
        when the native file names no `ar` and PATH carries no bare
        llvm-ar/ar, setup fails with "Unknown linker(s)". Derive the
        archiver from tools.build:compiler_executables (c-stdaux precedent)
        instead of hardcoding one absolute path.
        """
        for fname in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            native_file = os.path.join(self.generators_folder, fname)
            if not os.path.isfile(native_file):
                continue
            try:
                with open(native_file, encoding="utf-8") as f:
                    content = f.read()
            except OSError:
                continue
            if "[binaries]" not in content:
                continue
            binaries = content.split("[binaries]", 1)[1].split("\n\n", 1)[0]
            if "ar =" in binaries or "\nar =" in content:
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            candidates = []
            for cc_cand in (compilers.get("c") or "",
                            self._resolve_compiler("c", ("clang", "cc"))):
                if cc_cand and os.path.sep in cc_cand:
                    candidates.append(os.path.join(os.path.dirname(cc_cand), "llvm-ar"))
                    candidates.append(os.path.join(os.path.dirname(cc_cand), "ar"))
            for extra in (
                os.environ.get("HMBS_LLVM_BIN", ""),
                "/data/service/hnp/bin",
            ):
                if extra:
                    candidates.append(os.path.join(extra, "llvm-ar"))
                    candidates.append(os.path.join(extra, "ar"))
            for sdk in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
                candidates.append(os.path.join(sdk, "llvm-ar"))
                candidates.append(os.path.join(sdk, "ar"))
            ar_abs = None
            for cand in candidates:
                if cand and os.path.isfile(cand):
                    ar_abs = cand
                    break
            if ar_abs is None:
                found = shutil.which("llvm-ar") or shutil.which("ar")
                if found:
                    ar_abs = found
            if ar_abs is None:
                continue
            marker = "[binaries]\nc ="
            if marker not in content:
                continue
            content = content.replace(
                marker, "[binaries]\nar = '%s'\nc =" % ar_abs, 1
            )
            try:
                with open(native_file, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info("pinned meson archiver to " + ar_abs + " in " + fname)
            except OSError:
                pass

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _meson_test_env(self):
        """Build a subprocess env with tool bindirs + writable TMPDIR.

        ``subprocess.run`` bypasses the ``conanbuild`` env that ``self.run``
        (c-siphash 1.1.0 precedent) gets for free, so the ``meson/1.11.0``
        tool_require binary is invisible to ``shutil.which`` on HMBS
        workers (``[Errno 2] No such file or directory: 'meson'``).
        Prepend every build-require package ``bin/`` dir to PATH here and
        force TMPDIR/TMP/TEMP to a writable dir (readonly_tmp diagnosis).
        """
        env = dict(os.environ)
        tmp = self._writable_tmpdir()
        try:
            Path(tmp).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        env["TMPDIR"] = tmp
        env["TMP"] = tmp
        env["TEMP"] = tmp
        bindirs = []
        try:
            for _, dep in self.dependencies.build.items():
                try:
                    folder = dep.package_folder
                except Exception:
                    continue
                if not folder or not os.path.isdir(folder):
                    continue
                for sub in ("bin",):
                    p = os.path.join(folder, sub)
                    if os.path.isdir(p) and p not in bindirs:
                        bindirs.append(p)
                try:
                    info_dirs = dep.cpp_info.bindirs or []
                except Exception:
                    info_dirs = []
                for b in info_dirs:
                    q = b if os.path.isabs(b) else os.path.join(folder, b)
                    if os.path.isdir(q) and q not in bindirs:
                        bindirs.append(q)
        except Exception:
            pass
        if bindirs:
            env["PATH"] = os.pathsep.join(
                bindirs + [env.get("PATH", "")] if env.get("PATH") else bindirs
            )
        return env

    def _resolve_meson_args(self, env):
        """Return argv list to invoke meson test under the given env."""
        path = env.get("PATH", os.environ.get("PATH", ""))
        cand = shutil.which("meson", path=path)
        if cand:
            return [cand]
        # Fall back to the tool_require package folder directly.
        folder = None
        try:
            try:
                dep = self.dependencies.build.get("meson")
            except AttributeError:
                try:
                    dep = self.dependencies.build["meson"]
                except Exception:
                    dep = None
            folder = dep.package_folder if dep is not None else None
        except Exception:
            folder = None
        if folder:
            for rel in ("bin/meson", "bin/meson.py"):
                p = os.path.join(folder, rel)
                if os.path.isfile(p):
                    py = (os.environ.get("HMBS_PYTHON3")
                          or shutil.which("python3", path=path)
                          or sys.executable)
                    if p.endswith(".py") or not os.access(p, os.X_OK):
                        return [py, p] if py else [sys.executable, p]
                    return [p]
        # Last resort: python -m mesonbuild (meson is pure-python).
        py = (os.environ.get("HMBS_PYTHON3")
              or shutil.which("python3", path=path)
              or sys.executable)
        return [py, "-m", "mesonbuild.mesonmain"]

    def _run_upstream_tests(self):
        """Run `meson test` (27 C tests + 8 C++ tests) and emit the marker."""
        env = self._meson_test_env()
        meson_argv = self._resolve_meson_args(env)
        self.output.info("resolved meson test argv: %s" % " ".join(meson_argv))
        output = ""
        exit_code = 0
        try:
            result = subprocess.run(
                meson_argv + ["test", "-C", self.build_folder,
                              "--print-errorlogs", "--num-processes", "1"],
                capture_output=True,
                text=True,
                timeout=600,
                env=env,
            )
            output = (result.stdout or "") + (result.stderr or "")
            exit_code = result.returncode
            tail = "\n".join(output.splitlines()[-40:])
            self.output.info("meson test output (tail):\n%s" % tail)
            self.output.info("meson test exit=%d" % exit_code)
        except Exception as exc:
            output = str(exc)
            exit_code = 1
            self.output.warning("meson test failed to run: %s" % exc)

        discovered, executed, passed, failed, skipped = self._parse_test_output(
            output, exit_code
        )
        status = "passed" if (
            exit_code == 0 and failed == 0 and skipped == 0
            and executed == discovered and discovered > 0
        ) else "failed"
        marker = {
            "status": status,
            "framework": "meson",
            "command": "meson test -C build --print-errorlogs",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        # Persist for cache-hit rounds: build() is skipped when the package
        # binary is already in cache, so test_package re-emits this file
        # every round (ali/0.8.0 evidence-persist precedent). Republication
        # only, numbers stay from this real `meson test` run.
        try:
            persist = os.path.join(self.build_folder, "hmbs_upstream.json")
            with open(persist, "w", encoding="utf-8") as f:
                json.dump(marker, f)
            self.output.info("persisted upstream evidence to " + persist)
        except OSError as exc:
            self.output.warning("persist upstream evidence failed: %s" % exc)
        if status != "passed":
            raise Exception("upstream meson test failed: %s" % json.dumps(marker))

    @staticmethod
    def _parse_test_output(output, exit_code):
        """Parse `meson test` per-test lines plus the Ok/Fail summary."""
        passed = 0
        failed = 0
        skipped = 0
        # Per-test lines look like " 1/35 xraylib:atomicweight OK 0.05s".
        for line in output.splitlines():
            if not re.search(r"^\s*\d+\s*/\s*\d+\s+\S+", line):
                continue
            upper = line.upper()
            if re.search(r"\bSKIP\b", upper) or re.search(r"\bSKIPPED\b", upper):
                skipped += 1
            elif re.search(r"\bFAIL\b", upper) or re.search(r"\bFAILED\b", upper) \
                    or re.search(r"\bTIMEOUT\b", upper):
                failed += 1
            elif re.search(r"\bOK\b", upper):
                passed += 1
        # Summary lines ("Ok: 35", "Fail: 0", "Skipped: 0") win when present.
        m = re.search(r"^Ok:\s*(\d+)", output, re.M)
        if m:
            passed = int(m.group(1))
        m = re.search(r"^Fail:\s*(\d+)", output, re.M)
        if m:
            failed = int(m.group(1))
        m = re.search(r"^(?:Skipped|Skip):\s*(\d+)", output, re.M | re.I)
        if m:
            skipped = int(m.group(1))
        m = re.search(r"^(?:Expected Fail|Unexpected Pass|Timeout):\s*(\d+)",
                      output, re.M | re.I)
        extra_fail = 0
        for mm in re.finditer(
                r"^(?:Expected Fail|Unexpected Pass|Timeout):\s*(\d+)",
                output, re.M | re.I):
            try:
                extra_fail += int(mm.group(1))
            except ValueError:
                pass
        failed += extra_fail
        executed = passed + failed + skipped
        # Total: prefer the "1/35" denominator, else summary sum.
        discovered = 0
        for mm in re.finditer(r"^\s*\d+\s*/\s*(\d+)\s+\S+", output, re.M):
            try:
                discovered = max(discovered, int(mm.group(1)))
            except ValueError:
                pass
        if discovered <= 0:
            discovered = executed
        if executed > discovered:
            discovered = executed
        if discovered <= 0:
            discovered = 35
        return discovered, executed, passed, failed, skipped

    def package(self):
        meson = Meson(self)
        meson.install()
        for root, _, files in os.walk(self.package_folder):
            for fname in files:
                if fname.endswith(".la"):
                    try:
                        os.remove(os.path.join(root, fname))
                    except OSError:
                        pass
        # Ship the upstream evidence with the package so cache-hit rounds
        # (build() skipped) can still re-emit a real-result marker.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(dst_dir, "hmbs_upstream.json"))
                self.output.info("packaged upstream evidence res/hmbs_upstream.json")
        except OSError as exc:
            self.output.warning("package upstream evidence failed: %s" % exc)

    def package_info(self):
        self.cpp_info.libs = ["xrl"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
        # Headers install to includedir/xraylib (meson install_headers with
        # subdir xraylib). Expose both dirs to support <xraylib.h> and
        # <xraylib/xraylib.h> spellings.
        self.cpp_info.includedirs = ["include", "include/xraylib"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libxrl")
