#!/usr/bin/env python3
"""Conan test_package — libsmf 1.3.

Compiles test_smf.c against the packaged libsmf (plus glib from the
dependency closure) with a direct cc link — no dlopen — so CI's L1e
destructive reverse check (removing lib/include) fails at compile/link
time. Runs the probe and emits HMBS machine-evidence markers.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class LibsmfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Header/lib closure across all deps (libsmf + glib). Aggregate
        # top-level cpp_info AND components: glib/2.88.x exposes libs via
        # components (glib-2.0/gobject-2.0/...) with relative dirs.
        incs = []
        libdirs = []
        other_libs = []
        for _ref, _d in self.dependencies.items():
            # Conan 2: iteration yields (Requirement, Dependency); the package
            # name lives on Requirement.ref.name (Requirement itself has no
            # .name attribute -- direct _ref.name raises AttributeError on
            # conan 2.30, which broke preflight test-package build).
            _dep_name = ""
            try:
                _r = getattr(_ref, "ref", None)
                if _r is not None:
                    _dep_name = getattr(_r, "name", "") or ""
            except Exception:
                _dep_name = ""
            if not _dep_name:
                try:
                    _r2 = getattr(_d, "ref", None)
                    if _r2 is not None:
                        _dep_name = getattr(_r2, "name", "") or ""
                except Exception:
                    pass
            try:
                _infos = [_d.cpp_info] + list(_d.cpp_info.components.values())
            except Exception:
                _infos = [_d.cpp_info]
            _pkg = getattr(_d, "package_folder", "") or ""
            for _info in _infos:
                for p in getattr(_info, "includedirs", []):
                    _a = p if os.path.isabs(p) else os.path.join(_pkg, p)
                    if ("-I" + _a) not in incs:
                        incs.append("-I" + _a)
                for p in getattr(_info, "libdirs", []):
                    _a = p if os.path.isabs(p) else os.path.join(_pkg, p)
                    if ("-L" + _a) not in libdirs:
                        libdirs.append("-L" + _a)
            if _dep_name == "libsmf":
                continue
            for _info in _infos:
                for lib in getattr(_info, "libs", []):
                    _f = "-l" + lib
                    if _f not in other_libs:
                        other_libs.append(_f)
                for lib in getattr(_info, "system_libs", []):
                    _f = "-l" + lib
                    if _f not in other_libs:
                        other_libs.append(_f)
        inc = " ".join(incs)
        libdir = " ".join(libdirs)
        extralibs = " ".join(other_libs)
        # Prefer toolchain CC from the build env; never hardcode the HNP
        # absolute path first (preflight reports it "inaccessible or not
        # found", libffi 3.4.4 Error 127). Fall back via PATH lookup.
        cc = (os.environ.get("CC", "") or "").strip().split()[0] if os.environ.get("CC", "").strip() else ""
        if not cc or ("/" in cc and not os.path.isfile(cc)):
            cc = shutil.which("clang") or shutil.which("cc") or "cc"
        # Direct link against -lsmf (R34); glib/system libs appended after.
        self.run(f"{cc} test_smf.c -o test_smf {inc} {libdir} -lsmf {extralibs} -lm")

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap execution with the injected shell. Prefer HMBS SHELL /
        # CONFIG_SHELL (capability shell=/bin/sh); the HNP absolute bash
        # proved "inaccessible or not found" on preflight, so it is only a
        # last resort after a PATH lookup.
        bash = (os.environ.get("CONFIG_SHELL", "") or os.environ.get("SHELL", "") or "").strip()
        if not bash or ("/" in bash and not os.path.isfile(bash)):
            bash = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        discovered = 8
        passed = 0
        try:
            self.run(f"{bash} -c './test_smf'", env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test_smf failed: {exc}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_smf",
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Upstream libsmf 1.3 ships no test suite (audited tarball, see
        # test_package/MANIFEST.yml upstream_tests_exist: false), so the
        # honest upstream result is no_tests/0.
        ut_result = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libsmf-1.3.tar.gz audited (sha256 "
                "d3549f15de94ac8905ad365639ac6a2689cb1b51fdfa02d77fa6640001b18099): "
                "no tests/ or test/ directory, no *test* source files in the "
                "tree (find only matches autoconf generated scripts), "
                "Makefile.am/SRC/Makefile.am define no TESTS/check_PROGRAMS/"
                "check-local targets, configure.ac contains no test macros, "
                "so make check is automake's default empty target executing "
                "zero test cases"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        # Extra smoke: the packaged smfsh CLI reports its libsmf version.
        # Resolve the binary by absolute path (package_folder/bin + declared
        # bindirs) instead of relying on conanrun PATH wiring: preflight
        # showed `/bin/sh: smfsh: inaccessible or not found` even with
        # env="conanrun", while the file is installed under the package
        # bin dir. Still fatal when truly missing (no silent skip).
        _smfsh = None
        try:
            _libsmf_pkg = ""
            try:
                _libsmf_dep = self.dependencies["libsmf"]
                _libsmf_pkg = getattr(_libsmf_dep, "package_folder", "") or ""
            except Exception:
                _libsmf_pkg = ""
            if not _libsmf_pkg:
                for _ref2, _d2 in self.dependencies.items():
                    _n2 = ""
                    try:
                        _r = getattr(_ref2, "ref", None)
                        if _r is not None:
                            _n2 = getattr(_r, "name", "") or ""
                    except Exception:
                        pass
                    if not _n2:
                        try:
                            _r2 = getattr(_d2, "ref", None)
                            if _r2 is not None:
                                _n2 = getattr(_r2, "name", "") or ""
                        except Exception:
                            pass
                    if _n2 == "libsmf":
                        _libsmf_pkg = getattr(_d2, "package_folder", "") or ""
                        break
            _candidates = []
            if _libsmf_pkg:
                _candidates.append(os.path.join(_libsmf_pkg, "bin", "smfsh"))
                try:
                    _bindirs = list(getattr(_libsmf_dep.cpp_info, "bindirs", []) or ["bin"]) if "_libsmf_dep" in locals() and _libsmf_dep is not None else ["bin"]
                except Exception:
                    _bindirs = ["bin"]
                for _b in _bindirs:
                    _p = _b if os.path.isabs(_b) else os.path.join(_libsmf_pkg, _b)
                    _c = os.path.join(_p, "smfsh")
                    if _c not in _candidates:
                        _candidates.append(_c)
            _which = shutil.which("smfsh")
            if _which and _which not in _candidates:
                _candidates.append(_which)
            for _c in _candidates:
                if _c and os.path.isfile(_c):
                    _smfsh = _c
                    break
            if _smfsh is None:
                _smfsh = _candidates[0] if _candidates else "smfsh"
        except Exception:
            _smfsh = shutil.which("smfsh") or "smfsh"
        try:
            self.run(f'"{_smfsh}" -V', env="conanrun")
        except Exception as exc:
            raise ConanException(f"smfsh -V smoke failed: {exc}")

        if passed != discovered:
            raise ConanException("test_package SMF round-trip failed")
