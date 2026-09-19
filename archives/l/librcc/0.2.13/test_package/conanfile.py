#!/usr/bin/env python3
"""Conan test_package for librcc 0.2.13 (consumer verification, L1).

Device note: the HNP CMake compiler check (CMAKE_C_COMPILER identification
via /data/service/hnp/bin/clang) keeps failing on the read-only-/tmp device
even after TMPDIR/TMP/TEMP+SHELL injection into conanbuild.sh (two preflight
rounds, same fingerprint). The main package already proves direct
"${CC:-clang}" invocation under conanbuild env works (build reaches the
test_package stage), so this test_package compiles test.c directly with the
toolchain compiler instead of going through CMake. Same 3 real cases, same
machine-evidence marker; CMakeLists.txt is kept for structure only.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


def _writable_tmpdir(conanfile):
    """Reuse HMBS-injected writable tmpdir (device /tmp is read-only erofs)."""
    candidates = []
    for key in ("HMBS_TMPDIR", "HMBS_TMPDIR_RUNTIME"):
        value = os.environ.get(key)
        if value:
            candidates.append(value)
    capabilities = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
    if capabilities:
        try:
            obj = json.loads(capabilities)
            if isinstance(obj, dict):
                for sub in ("tmpdir", "tmpDir", "TMPDIR"):
                    if obj.get(sub):
                        candidates.append(str(obj[sub]))
        except Exception:
            pass
    for key in ("TMPDIR", "TMP", "TEMP"):
        value = os.environ.get(key)
        if value and value != "/tmp" and value not in candidates:
            candidates.append(value)
    fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
    if fallback and fallback not in candidates:
        candidates.append(fallback)
    for base in (getattr(conanfile, "build_folder", None),
                 getattr(conanfile, "source_folder", None)):
        if base:
            candidates.append(os.path.join(str(base), "tmp"))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
        except OSError:
            continue
        if not os.path.isdir(candidate):
            continue
        try:
            probe = os.path.join(candidate, ".hmbs_wtest")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("w")
            os.remove(probe)
            return candidate
        except OSError:
            continue
    fallback_dir = os.path.join(str(conanfile.build_folder), "tmp")
    os.makedirs(fallback_dir, exist_ok=True)
    return fallback_dir


def _ensure_tmp_env(conanfile):
    """Redirect temp files off read-only /tmp; pin shell to /bin/sh."""
    tmp = _writable_tmpdir(conanfile)
    for key in ("TMPDIR", "TMP", "TEMP"):
        os.environ[key] = tmp
    os.environ["SHELL"] = "/bin/sh"
    os.environ["CONFIG_SHELL"] = "/bin/sh"
    try:
        os.umask(0o022)
    except Exception:
        pass
    return tmp


def _dep_flags(conanfile):
    """Aggregate -I/-L/-l/-D from host deps (librcc + transitive libxml2)."""
    includes, libdirs, libs, defines = [], [], [], []
    try:
        deps = conanfile.dependencies.host.values()
    except Exception:
        deps = []
    for dep in deps:
        try:
            info = dep.cpp_info
        except Exception:
            continue
        for attr, bucket in (
            ("includedirs", includes), ("libdirs", libdirs),
            ("libs", libs), ("defines", defines),
        ):
            try:
                for value in getattr(info, attr) or []:
                    if value and value not in bucket:
                        bucket.append(value)
            except Exception:
                continue
        try:
            for value in info.system_libs or []:
                if value and value not in libs:
                    libs.append(value)
        except Exception:
            pass
    return includes, libdirs, libs, defines


class LibrccTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        _ensure_tmp_env(self)
        from conan.tools.env import VirtualBuildEnv
        VirtualBuildEnv(self).generate()
        tmp = _writable_tmpdir(self)
        hmbs_env = Environment()
        hmbs_env.define("TMPDIR", tmp)
        hmbs_env.define("TMP", tmp)
        hmbs_env.define("TEMP", tmp)
        hmbs_env.define("SHELL", "/bin/sh")
        hmbs_env.define("CONFIG_SHELL", "/bin/sh")
        hmbs_env.vars(self, scope="build").save_script("hmbs_env")

    def build(self):
        _ensure_tmp_env(self)
        includes, libdirs, libs, defines = _dep_flags(self)
        inc_flags = " ".join('"%s"' % ("-I" + d) for d in includes)
        libdir_flags = " ".join('"%s"' % ("-L" + d) for d in libdirs)
        link_libs = list(libs)
        for required in ("rcc", "rccui", "xml2", "pthread", "dl", "m"):
            if required not in link_libs:
                link_libs.append(required)
        lib_flags = " ".join("-l%s" % lib for lib in link_libs)
        define_flags = " ".join("-D%s" % d for d in defines)
        src = os.path.join(self.source_folder, "test.c").replace("\\", "/")
        out = os.path.join(self.build_folder, "test_librcc").replace("\\", "/")
        script = "set -eu\n"
        script += 'echo "[hmbs-test-build] CC=${CC:-clang}"\n'
        script += 'echo "[hmbs-test-build] TMPDIR=${TMPDIR:-<unset>}"\n'
        script += '"${CC:-clang}" -O2 %s %s "%s" -o "%s" %s %s\n' % (
            define_flags, inc_flags, src, out, libdir_flags, lib_flags)
        script += 'ls -la "%s"\n' % self.build_folder
        self.run(script, env="conanbuild")

    def test(self):
        _ensure_tmp_env(self)
        exe = os.path.join(self.build_folder, "test_librcc")
        if not os.path.exists(exe):
            for root, _, files in os.walk(self.build_folder):
                if "test_librcc" in files:
                    exe = os.path.join(root, "test_librcc")
                    break
        if not os.path.exists(exe):
            raise Exception("test_librcc binary not found")
        run_env = dict(os.environ)
        tmp = run_env.get("TMPDIR") or _writable_tmpdir(self)
        for key in ("TMPDIR", "TMP", "TEMP"):
            run_env[key] = tmp
        # Shared-link fallback: expose package + dep lib dirs to loader.
        lib_paths = []
        try:
            for dep in self.dependencies.host.values():
                try:
                    for d in dep.cpp_info.libdirs or []:
                        if d and d not in lib_paths:
                            lib_paths.append(d)
                except Exception:
                    continue
        except Exception:
            pass
        if lib_paths:
            prev = run_env.get("LD_LIBRARY_PATH", "")
            run_env["LD_LIBRARY_PATH"] = ":".join(lib_paths) + (":" + prev if prev else "")
        proc = subprocess.run(
            [exe], capture_output=True, text=True, cwd=self.build_folder,
            env=run_env)
        out = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("test_librcc output:\n" + out)
        if proc.returncode != 0:
            raise Exception("test_librcc failed with code %d" % proc.returncode)
        passed = len(re.findall(r"^ok \d+", out, re.M))
        if passed < 3:
            raise Exception("expected 3 ok cases, got %d" % passed)
        test_marker = (
            'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
            '"command":"./test_librcc","discovered":3,"passedCount":3}')
        self.output.highlight(test_marker)
        print(test_marker, flush=True)
        # Re-emit persisted upstream evidence (cache-hit safe): build() may
        # have been skipped as "Already installed", so read the JSON the
        # package carried and emit the identical marker dual-channel.
        upstream = None
        searched = []
        try:
            host_deps = self.dependencies.host.values()
        except Exception:
            host_deps = []
        for dep in host_deps:
            try:
                ref = getattr(dep, "ref", None)
                name = getattr(ref, "name", "") if ref is not None else ""
                pkg_folder = str(getattr(dep, "package_folder", "") or "")
            except Exception:
                continue
            if name != "librcc" or not pkg_folder:
                continue
            for rel in (
                os.path.join("lib", "rcc", "hmbs_upstream_test_result.json"),
                os.path.join("share", "hmbs_upstream_test_result.json"),
                "hmbs_upstream_test_result.json",
            ):
                cand = os.path.join(pkg_folder, rel)
                searched.append(cand)
                if upstream is None and os.path.isfile(cand):
                    try:
                        with open(cand, "r", encoding="utf-8") as handle:
                            upstream = json.load(handle)
                    except Exception as exc:  # noqa: BLE001
                        raise Exception(
                            "invalid persisted upstream result %s: %s"
                            % (cand, exc))
        if upstream is None:
            raise Exception(
                "persisted hmbs_upstream_test_result.json missing in librcc "
                "package (searched: %s)" % "; ".join(searched))
        for field in ("discovered", "executed", "passed", "failed", "skipped"):
            if field not in upstream:
                raise Exception(
                    "persisted upstream result missing field %s" % field)
        if upstream.get("status") != "passed":
            raise Exception(
                "unexpected upstream status %r" % upstream.get("status"))
        for field in ("command", "framework"):
            if not upstream.get(field):
                raise Exception(
                    "persisted upstream result missing field %s" % field)
        if upstream.get("discovered", 0) < 1 or upstream.get("executed", 0) < 1:
            raise Exception(
                "persisted upstream result has no executed tests: %r" % upstream)
        if upstream.get("executed") != upstream.get("passed"):
            raise Exception(
                "persisted upstream result not fully passed: %r" % upstream)
        if upstream.get("failed", 0) != 0:
            raise Exception(
                "persisted upstream result has failures: %r" % upstream)
        upstream_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            upstream, separators=(",", ":"), ensure_ascii=False)
        self.output.highlight(upstream_marker)
        print(upstream_marker, flush=True)
