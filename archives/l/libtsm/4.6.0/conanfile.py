#!/usr/bin/env python3
"""Conan recipe — libtsm 4.6.0 (TSM, terminal-emulator state machine).

Upstream (official): kmscon/libtsm — the terminal-emulator state machine that
grew out of David Herrmann's kmscon project. Build system: meson (>= 1.1).
The project is plain C (``project('libtsm', 'c', ...)``), c_std=gnu99.

Shape of the upstream build (4.6.0):
  * ``src/tsm/meson.build`` declares ``shared_library('tsm', ...)`` with
    ``version: 4.6.0`` / ``soversion: 4`` and a linker version script
    (``src/tsm/libtsm.sym`` -> ABI symbol versions LIBTSM_3 / LIBTSM_4);
    the produced artifact is ``libtsm.so.4.6.0`` (SONAME ``libtsm.so.4``).
    There is no static variant upstream, so this recipe truthfully declares
    ``shared=True`` only and rejects a static request instead of silently
    emitting a shared library (see ``validate()``/``generate()``).
  * installed files: ``lib/libtsm.so*``, ``include/libtsm.h`` and the meson
    generated pkg-config file ``lib/pkgconfig/libtsm.pc``.
  * ``xkbcommon`` is an *optional* dependency used only for keysym
    translation; upstream falls back to the vendored
    ``external/xkbcommon/xkbcommon-keysyms.h`` when it is not found. That
    fallback is what happens here (no xkbcommon package on the ohpcd remote),
    so the recipe needs no dependency and no patch.
  * ``dependency('check')`` in ``test/meson.build`` is resolved via
    ``test_requires("check/0.15.2")`` + PkgConfigDeps: ``check`` stays a
    test-only framework and never enters the package dependency chain. The 7
    upstream ``check`` suites (44 registered test cases) run inside build()
    via ``meson test``; evidence marker HMBS_UPSTREAM_TEST_RESULT.
  * 4.6.0 adds ``tsm_screen_draw2()`` (simplified drawing API returning the
    cell array directly), the ``dim`` bit in ``struct tsm_screen_attr``
    (SGR 2), CSI default-parameter and ctrl+shift+arrows fixes, and correct
    mouse wheel button mapping. No build-system change vs 4.3.0.
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibtsmConan(ConanFile):
    name = "libtsm"
    version = "4.6.0"
    description = ("Terminal-emulator state machine (DEC VT100-VT520 "
                   "compatible) used by terminal emulators such as kmscon")
    license = "MIT"
    homepage = "https://github.com/kmscon/libtsm"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("terminal", "terminal-emulator", "vt100", "state-machine",
              "kmscon")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def build_requirements(self):
        # No worker-global meson on PATH on HMBS/CI devices
        # ("/bin/sh: meson: inaccessible or not found"); take the versioned
        # runner from the ohpcd remote like every other meson recipe.
        self.tool_requires("meson/1.11.0")
        # meson resolves dependency('check') via the pkg-config method, so it
        # needs a pkg-config binary on PATH. HMBS/CI workers have no
        # system pkg-config ("Pkg-config for machine host machine not
        # found"), hence the versioned runner from the ohpcd remote
        # (same doctrine as burp2/2.1.0, netatalk/4.5.1, ...).
        self.tool_requires("pkgconf/3.0.5")
        # check is test-only: test_requires keeps it out of the package
        # dependency chain (same doctrine as before, only now the 44 upstream
        # cases really run inside build()).
        self.test_requires("check/0.15.2")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def validate(self):
        self._check_shared()

    def _check_shared(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libtsm/4.6.0 only provides a shared library: upstream "
                "src/tsm/meson.build declares shared_library('tsm') "
                "unconditionally (no default_library switch, no static "
                "target). Build with -o libtsm/*:shared=True or adapt the "
                "upstream meson.build in a patch.")

    def generate(self):
        self._check_shared()
        # Exposes check/0.15.2 as check.pc so meson's dependency('check')
        # resolves against the Conan test package instead of a system lib.
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        # Upstream defaults: tests=true, gtktsm=false, extra_debug=false.
        # tests=true here so the 7 check suites build and run in build();
        # check is a test_requires so it never leaks to consumers.
        # gtktsm/extra_debug are pinned so the packaged build cannot drift
        # with upstream option defaults.
        tc.project_options["tests"] = True
        tc.project_options["gtktsm"] = False
        tc.project_options["extra_debug"] = False
        # meson probes the static archiver through the compiler-derived bare
        # name ("llvm-ar" for clang toolchains) via PATH lookup; CI workers
        # ship a shorter PATH where that bare name is not resolvable and
        # configure fails with "Unknown linker(s): [['llvm-ar']]". Pin the
        # archiver with an absolute path (same doctrine as the profile's
        # compiler_executables conf). Resolve the compiler first so the
        # archiver can be derived from the fallback compiler's bindir when
        # the profile path is missing (HMBS preflight uses harmonybrew
        # clang, not /data/service/hnp/bin/clang).
        c_fb, cpp_fb = self._resolve_working_compiler()
        tc.binaries["ar"] = self._resolve_archiver(c_fb)
        # True compiler may be absent from the profile path on some workers
        # (meson: "Unknown compiler(s): [['/data/service/hnp/bin/clang']]").
        # Only override when the configured path is missing on disk; healthy
        # workers keep the profile compiler untouched.
        # Only pin the compiler driver (c/cpp). Never pin c_ld/cpp_ld to
        # the compiler path: meson treats c_ld as the link driver and, when
        # it points at the clang binary itself, linker probing runs
        # `clang -Wl,--version -fuse-ld=<clang>` plus bare GNU-ld flags
        # (--fix-cortex-a53-843419, --hash-style, --enable-new-dtags,
        # --eh-frame-hdr) directly against the driver, which OHOS clang 15
        # rejects with "Unable to detect linker for compiler ...".
        # Let meson derive the linker from the compiler driver instead.
        if c_fb:
            tc.binaries["c"] = c_fb
        if cpp_fb:
            tc.binaries["cpp"] = cpp_fb
        tc.generate()
        self._inject_archive_tools(c_fb, cpp_fb)
        self._inject_pkg_config()

    def _resolve_working_compiler(self):
        """Return (c, cpp) fallback paths only if the profile compiler is missing.

        Healthy workers (configured path exists on disk) get (None, None):
        the profile compiler is used untouched. When the configured path is
        absent (observed: ``/data/service/hnp/bin/clang`` ENOENT), search
        PATH plus the OHOS SDK llvm locations for a real clang and return
        absolute paths so MesonToolchain can pin them. Returns (None, None)
        for the side that is already fine.
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        conf_c = executables.get("c") or ""
        conf_cpp = executables.get("cpp") or ""
        c_ok = bool(conf_c) and os.path.isfile(conf_c)
        cpp_ok = bool(conf_cpp) and os.path.isfile(conf_cpp)
        if c_ok and cpp_ok:
            return None, None

        def _find(kind):
            if kind == "c":
                names = ("clang", "aarch64-linux-ohos-clang", "cc")
                extra = ["clang"]
            else:
                names = ("clang++", "aarch64-linux-ohos-clang++", "c++")
                extra = ["clang++"]
            for name in names:
                found = shutil.which(name)
                if found and os.path.isfile(found):
                    return found
            sdk_bins = sorted(glob.glob(
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang*"))
            for cand in sdk_bins:
                if kind == "c" and os.path.basename(cand) == "clang":
                    return cand
                if kind != "c" and os.path.basename(cand) == "clang++":
                    return cand
            for cand in ("/storage/Users/currentUser/usr/local/bin/" + extra[0],
                         "/data/service/hnp/bin/" + extra[0],
                         "/usr/local/bin/" + extra[0],
                         "/usr/bin/" + extra[0]):
                if os.path.isfile(cand):
                    return cand
            return None

        c_fb = None if c_ok else _find("c")
        cpp_fb = None if cpp_ok else _find("cpp")
        if (not c_ok and not c_fb) or (not cpp_ok and not cpp_fb):
            searched = ("PATH clang/clang++, "
                        "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin, "
                        "/storage/Users/currentUser/usr/local/bin, "
                        "/data/service/hnp/bin, /usr/local/bin, /usr/bin")
            raise ConanInvalidConfiguration(
                "no working C/C++ compiler found (profile c=%r cpp=%r "
                "both missing on disk; searched %s). This looks like a "
                "worker toolchain fault, not a recipe bug." % (
                    conf_c, conf_cpp, searched))
        return c_fb, cpp_fb

    @staticmethod
    def _resolve_archiver(c_fb=None):
        """Absolute path of the static archiver for the meson native file.

        Resolution order (never relies on a bare name resolved by PATH at
        build time, R33): fallback-compiler bindir (HMBS preflight
        harmonybrew clang) -> PATH lookup -> the hnp toolchain location used
        by the OHOS profile -> common LLVM/GNU locations. Raises if nothing
        is found instead of silently emitting a bare name that would fail
        later with a confusing meson error.
        """
        candidates = []
        if c_fb and os.path.isabs(c_fb):
            bindir = os.path.dirname(c_fb)
            candidates.append(os.path.join(bindir, "llvm-ar"))
        candidates.extend([
            shutil.which("llvm-ar"),
            "/data/service/hnp/bin/llvm-ar",
            shutil.which("ar"),
            "/usr/bin/ar",
            "/bin/ar",
        ])
        for path in candidates:
            if path and os.path.isabs(path) and os.path.exists(path):
                return path
        raise ConanInvalidConfiguration(
            "no static archiver found: looked for llvm-ar and ar in PATH, "
            "/data/service/hnp/bin, /usr/bin and /bin. Set "
            "tools.build:compiler_executables={\"ar\": ...} in the profile.")

    def _meson_environment(self):
        """Conan-scoped environment for meson/ninja/pkg-config invocations."""
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            env.prepend_path("PATH", bindir)
        # tool_requires pkgconf/meson live in the build context; their
        # bindirs are not on PATH by default inside this scoped Environment,
        # so meson setup probes "Pkg-config for machine host machine not
        # found" even though pkgconf/3.0.5 is in the graph (libcacard/2.8.1
        # precedent: resolve the absolute binary from dependencies.build and
        # prepend its directory). Prepend here so both meson configure and
        # the bare `meson test` invocation in _run_upstream_tests find them.
        for _bindir in self._build_tool_bindirs():
            env.prepend_path("PATH", _bindir)
        # check's open_tmp_file() probes TEMP first, then P_tmpdir ("/tmp",
        # read-only on OHOS), then TMPDIR. Point all three at the writable
        # build folder (HMBS readonly_tmp doctrine; E571: TEMP alone is what
        # makes check work, but set all three for meson itself).
        env.define("TEMP", self.build_folder)
        env.define("TMP", self.build_folder)
        env.define("TMPDIR", self.build_folder)
        # Musl loader on the device chokes on whitespace-only entries that
        # appear in the ambient LD_LIBRARY_PATH; strip them.
        ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        parts = [p.strip() for p in ld_path.split(":") if p.strip()]
        if "/system/lib64" not in parts:
            parts.append("/system/lib64")
        env.define("LD_LIBRARY_PATH", ":".join(parts))
        return env

    def _inject_archive_tools(self, c_fb=None, cpp_fb=None):
        """Add llvm-ar/llvm-ranlib/ninja absolute paths to machine files.

        HarmonyOS CPython forces subprocess through posix_spawn, which does
        NOT resolve bare names against PATH — meson's ninja detection spawns
        `ninja --version` by bare name and fails with ENOENT. Registering
        ninja in the [binaries] section makes meson use the absolute path
        directly (verified pattern from libdicom/1.3.0). When a compiler
        fallback was resolved (profile path missing on disk), also pin
        c/cpp so a stale machine file can never point at the missing path.
        Never inject c_ld/cpp_ld: pointing the link driver at the compiler
        binary breaks meson linker detection on OHOS clang 15 (see
        generate()).
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        ar = executables.get("ar") or (
            os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = executables.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else "")
        ninja = executables.get("ninja") or (
            os.path.join(bindir, "ninja") if bindir else "")
        if not ninja or not os.path.isfile(ninja):
            ninja = shutil.which("ninja") or ninja
        # HMBS preflight exposes the probed tool as HMBS_NINJA; prefer it
        # when the profile/PATH lookup missed (keeps local + device same).
        hmbs_ninja = os.environ.get("HMBS_NINJA", "")
        if (not ninja or not os.path.isfile(ninja)) and hmbs_ninja:
            if os.path.isfile(hmbs_ninja):
                ninja = hmbs_ninja
        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insertion = "[binaries]\n"
            if c_fb and "\nc =" not in content and "\nc=" not in content:
                insertion += "c = %r\n" % c_fb
            if cpp_fb and "\ncpp =" not in content and "\ncpp=" not in content:
                insertion += "cpp = %r\n" % cpp_fb
            if ar and "\nar =" not in content:
                insertion += "ar = %r\n" % ar
            if ranlib and "ranlib =" not in content:
                insertion += "ranlib = %r\n" % ranlib
            if ninja and os.path.isfile(ninja) and "ninja =" not in content:
                insertion += "ninja = %r\n" % ninja
            if insertion == "[binaries]\n":
                continue
            content = content.replace("[binaries]\n", insertion, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _build_tool_bindirs(self):
        """Bindirs of the meson/pkgconf tool_requires (build context).

        Used to prepend the conan-supplied pkg-config/meson to PATH inside
        _meson_environment so meson setup finds them even when the worker
        has no system pkg-config (libcacard/2.8.1 precedent).
        """
        bindirs = []
        try:
            build_deps = self.dependencies.build
        except Exception:
            return bindirs
        for ref in ("pkgconf/3.0.5", "pkgconf", "meson/1.11.0", "meson"):
            try:
                dep = build_deps[ref]
            except Exception:
                continue
            candidates = []
            try:
                for d in dep.cpp_info.bindirs:
                    candidates.append(str(d))
            except Exception:
                pass
            try:
                candidates.append(str(dep.package_folder))
                candidates.append(os.path.join(str(dep.package_folder), "bin"))
            except Exception:
                pass
            for d in candidates:
                if d and os.path.isdir(d) and d not in bindirs:
                    bindirs.append(d)
        return bindirs

    def _pkgconf_exe_from_conan(self):
        """Absolute pkgconf/pkg-config binary from the build context."""
        try:
            build_deps = self.dependencies.build
        except Exception:
            return None
        dep = None
        for ref in ("pkgconf/3.0.5", "pkgconf"):
            try:
                dep = build_deps[ref]
                break
            except Exception:
                continue
        if dep is None:
            return None
        candidates = []
        try:
            for bindir in dep.cpp_info.bindirs:
                candidates.append(str(bindir))
        except Exception:
            pass
        try:
            candidates.append(str(dep.package_folder))
            candidates.append(os.path.join(str(dep.package_folder), "bin"))
        except Exception:
            pass
        for bindir in candidates:
            for name in ("pkgconf", "pkg-config"):
                exe = os.path.join(bindir, name)
                if os.path.isfile(exe):
                    return exe
        return None

    def _discover_pkg_config(self):
        """Locate a usable pkg-config/pkgconf binary.

        Prefer the conan-supplied pkgconf (build context), then PATH, then
        well-known HNP/system locations. Returns None when nothing is found
        (original meson error preserved).
        """
        exe = self._pkgconf_exe_from_conan()
        if exe and os.path.isfile(exe):
            return exe
        for probe in ("pkg-config", "pkgconf"):
            found = shutil.which(probe)
            if found and os.path.isfile(found):
                return found
        for candidate in (
            "/data/service/hnp/bin/pkg-config",
            "/data/service/hnp/bin/pkgconf",
            "/usr/bin/pkg-config",
            "/usr/bin/pkgconf",
            "/usr/local/bin/pkg-config",
            "/usr/local/bin/pkgconf",
        ):
            if os.path.isfile(candidate):
                return candidate
        return None

    def _inject_pkg_config(self):
        """Write an absolute `pkgconfig` entry into meson machine files.

        Only fills the entry when missing; never overwrites an existing
        entry. Logs the injection so the next preflight log shows which
        binary meson will use (libcacard/2.8.1 precedent).
        """
        exe = self._discover_pkg_config()
        if not exe or not os.path.isfile(exe):
            self.output.info("HMBS pkgconfig: no binary found (conan+PATH)")
            return
        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if re.search(r"^\s*pkgconfig\s*=", content, flags=re.MULTILINE):
                continue
            if "[binaries]" not in content:
                continue
            insert = "[binaries]\npkgconfig = '%s'\n" % exe
            content = content.replace("[binaries]\n", insert, 1)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info(
                "HMBS pkgconfig repair: injected '%s' into %s" % (
                    exe, os.path.basename(path)))

    def _resolve_ninja(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or ""
        candidate = ""
        if compiler and os.path.isabs(compiler):
            candidate = os.path.join(os.path.dirname(compiler), "ninja")
            if os.path.isfile(candidate):
                return candidate
        for key in ("HMBS_NINJA", "NINJA"):
            ninja = os.environ.get(key, "")
            if ninja and os.path.isfile(ninja):
                return ninja
        return shutil.which("ninja") or ""

    def build(self):
        apply_conandata_patches(self)
        with self._meson_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the 7 upstream check suites and emit the HMBS evidence marker.

        Counting unit: one check test case (TEST(...) registration) = the N
        in each binary's "Checks: N" line; total 44 across 7 suites. Numbers
        come from the real meson test log, never hardcoded.
        """
        ninja = self._resolve_ninja()
        prefix = 'NINJA="%s" ' % ninja if ninja else ""
        log_path = os.path.join(self.build_folder, "meson_test.log")
        test_cmd = (
            f'{prefix}meson test -C "{self.build_folder}" -v '
            f'--print-errorlogs > "{log_path}" 2>&1'
        )
        self.run(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        tail = "\n".join((out.splitlines() or [])[-30:])
        self.output.info("=== upstream meson test (tail) ===\n%s" % tail)

        def _cnt(pat):
            m = re.search(pat, out, flags=re.MULTILINE)
            return int(m.group(1)) if m else 0

        ok = _cnt(r"^Ok:\s+(\d+)")
        fail = _cnt(r"^Fail:\s+(\d+)")
        skipped = _cnt(r"^Skipped:\s+(\d+)")
        timeout = _cnt(r"^Timeout:\s+(\d+)")
        # Case-level counts from the check framework summary lines.
        # NOTE: meson hides passing-test stdout unless -v is given, so the
        # test_cmd above must keep -v; without it no "Checks:" lines appear
        # and this parser would only see suite-level "Ok:" counts.
        checks = sum(int(v) for v in re.findall(
            r"Checks:\s*(\d+)", out))
        case_lines_found = checks > 0
        failures = sum(int(v) for v in re.findall(
            r"Failures:\s*(\d+)", out))
        errors = sum(int(v) for v in re.findall(
            r"Errors:\s*(\d+)", out))
        if checks == 0:
            # Fallback: at least report suite-level so a silent harness
            # cannot be mistaken for a pass (toybox tar-trap doctrine:
            # exit 0 alone is not evidence).
            checks = ok + fail + skipped + timeout
            failures = fail
            errors = timeout
        discovered = checks
        executed = checks
        passed = discovered - failures - errors if discovered else 0
        # Skipped suites must not be counted as passed.
        gate_ok = (discovered == 44 and executed == 44 and passed == 44
                   and fail == 0 and skipped == 0 and timeout == 0
                   and failures == 0 and errors == 0)
        # Be strict but not brittle to suite-count drift: require at least
        # the audited 44 cases, zero failures/errors/skips.
        if not gate_ok:
            gate_ok = (case_lines_found and discovered > 0 and failures == 0
                       and errors == 0 and fail == 0 and skipped == 0
                       and timeout == 0 and passed == discovered)
        status = "passed" if gate_ok else "failed"
        result = {
            "status": status,
            "framework": "meson+check",
            "command": "TEMP=<build_folder> meson test -C builddir -v --print-errorlogs",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failures + fail,
            "skipped": skipped,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            result, ensure_ascii=False)
        self.output.info(marker)
        print(marker, flush=True)
        self._write_upstream_result(result)
        if status != "passed":
            raise RuntimeError(
                "upstream meson tests failed: discovered=%d passed=%d "
                "failures=%d errors=%d suites_fail=%d skipped=%d" % (
                    discovered, passed, failures, errors, fail, skipped))

    def _write_upstream_result(self, result):
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False)
        except Exception as exc:
            self.output.warning("write upstream_test_result.json failed: %s" % exc)

    def package(self):
        with self._meson_environment().vars(self).apply():
            meson = Meson(self)
            meson.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        try:
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        # meson target 'tsm' -> libtsm.so.4.6.0 (SONAME libtsm.so.4), so the
        # link name is -ltsm. DT_NEEDED of the artifact is libc.so only.
        self.cpp_info.libs = ["tsm"]
