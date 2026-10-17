#!/usr/bin/env python3
"""Conan recipe — libleidenalg 0.13.0 (CMake)"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibleidenalgConan(ConanFile):
    name = "libleidenalg"
    version = "0.13.0"
    description = "C++ library of the Leiden algorithm for community detection in networks"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/vtraag/libleidenalg"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("leiden", "community-detection", "graph", "igraph", "network")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("igraph/1.0.0", transitive_headers=True, transitive_libs=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libleidenalg supports Linux and OHOS, not {}".format(self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_writable_tmp(self):
        # HMBS [readonly_tmp]: /tmp is a read-only erofs mount on the
        # device. Reuse the HMBS-injected TMPDIR/TMP/TEMP when writable,
        # otherwise fall back to a writable dir under build_folder. Only
        # os.environ is set here (inherited by child cmake/compiler
        # processes); no conanbuild save_script, no test is skipped.
        candidates = [
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.path.join(self.build_folder, "tmp"),
        ]
        chosen = None
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_tmp_probe")
                with open(probe, "w") as f:
                    f.write("tmp-writable")
                os.remove(probe)
                chosen = cand
                break
            except Exception:
                continue
        if chosen:
            os.environ["TMPDIR"] = chosen
            os.environ["TMP"] = chosen
            os.environ["TEMP"] = chosen
        return chosen

    def generate(self):
        self._ensure_writable_tmp()
        # Cycle-6 route (differs from cycles 1-3 Linux alias via
        # cache_variables, from cycle-4 pristine-without-diagnostics, AND
        # from cycle-5 generic_system OHOS + recipe-level lld probe): use
        # Conan's NATIVE toolchain mapping untouched, exactly like the
        # proven in-repo sibling archives/i/igraph/1.0.0/conanfile.py
        # ("CMakeToolchain already sets CMAKE_SYSTEM_NAME from Conan
        # settings.os ... do not override"). Evidence that platform-name
        # mutation is the wrong family: knowledge/DRAFT-nng-*.md documents
        # "System is unknown to cmake" as WARNING-level and non-blocking
        # for POSIX C/C++ libs, and its .kv carries an explicit forbid
        # pattern on CMAKE_SYSTEM_NAME impersonation; three different
        # identity mutations (Linux alias, pristine HarmonyOS, OHOS name)
        # all reproduced the identical "identification is unknown"
        # fingerprint, proving the system name is not the blocking
        # variable. Likewise the recipe-level lld/libxml2 probe is dropped:
        # ci/conan/profiles/ohos-aarch64 already injects the SDK llvm/lib
        # LD_LIBRARY_PATH infra-wide for every package, and a bare
        # `cc src -o bin` probe without the toolchain's sysroot/target
        # flags cannot reproduce CMake's flagged compiler test, so it only
        # produced false ambient signals. No compiler override, no test
        # skipped; the only env handling kept is the HMBS-mandated TMP fix.
        #
        # Cycle-7 addition (new evidence, new family): the cycle-6
        # diagnostics proved the conf compiler itself is sandbox-invisible:
        # "cannot run /data/service/hnp/bin/clang --version: [Errno 2]".
        # All cycles 1-6 assumed that path exists and mutated everything
        # around it — wrong assumption. build() now verifies the conf
        # compilers first (runnable --version); only when the conf path is
        # missing does it resolve a verified-runnable SDK clang and point
        # the GENERATED conan_toolchain.cmake at it (recipe-scoped file
        # rewrite, never upstream CMakeLists). When the conf path exists
        # (e.g. CI workers) the toolchain is left byte-identical.
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if self.options.get_safe("fPIC") is not None:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        # igraph include-dir compensation (recipe-scoped, no upstream change):
        # in-repo igraph/1.0.0 sets includedirs=["include/igraph"], so its
        # CMakeDeps igraph::igraph target only carries -I<igraph>/include/igraph
        # (enough for <igraph.h>). Upstream libleidenalg sources instead do
        # #include <igraph/igraph.h> (see GraphHelper.h), which needs the
        # PARENT dir -I<igraph>/include — exactly what official igraph
        # packaging provides. Re-add the parent dir via extra flags; neither
        # upstream sources nor the igraph recipe are touched here.
        try:
            _igraph_include = os.path.join(
                self.dependencies["igraph"].package_folder, "include")
            tc.extra_cflags.append("-I" + _igraph_include)
            tc.extra_cxxflags.append("-I" + _igraph_include)
            self.output.info(
                "igraph include compensation: -I%s" % _igraph_include)
        except KeyError:
            self.output.warning(
                "igraph include compensation: igraph not in dependencies; skipped")
        tc.generate()
        # Persist writable TMP through conanbuild isolation (os.environ
        # alone is reset by aggregated env files). HMBS injects TMPDIR;
        # TMP only — no CC/CXX override.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP"))
        if not (_tmp and os.path.isdir(_tmp)):
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
        try:
            env = Environment()
            env.define("TMPDIR", _tmp)
            env.define("TMP", _tmp)
            env.define("TEMP", _tmp)
            env.vars(self).save_script("hmbs_tmp")
        except Exception:
            pass

    def _dump_cmake_diagnostics(self, label):
        """Fail-closed diagnostics: surface CMake's REAL error evidence.

        Cycles 1-5 all guessed at the toolchain (platform name, compiler
        override, lld runtime) from truncated summaries. This helper adds
        no fix and bypasses no check: on cmake.configure() failure it
        prints the tails of CMakeError.log / CMakeOutput.log, the real
        `clang --version` output, and the toolchain file's compiler /
        system / sysroot lines, then the caller re-raises. Read-only;
        never skips a test.
        """
        build_folder = self.build_folder or ""
        for log_name in ("CMakeError.log", "CMakeOutput.log"):
            found = ""
            if build_folder and os.path.isdir(build_folder):
                for root, _dirs, files in os.walk(build_folder):
                    if log_name in files:
                        found = os.path.join(root, log_name)
                        break
            if not found:
                self.output.info(
                    "%s: %s not found under build folder" % (label, log_name)
                )
                continue
            try:
                with open(found, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError as err:
                self.output.info(
                    "%s: cannot read %s: %s" % (label, found, err)
                )
                continue
            tail = lines[-80:]
            self.output.info(
                "%s: %s tail (%d/%d lines):\n%s"
                % (label, found, len(tail), len(lines), "\n".join(tail))
            )
        compilers = {}
        try:
            conf_compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compilers = dict(conf_compilers or {})
        except Exception:
            pass
        for key in ("c", "cpp"):
            cc = compilers.get(key, "")
            if not cc:
                continue
            try:
                proc = subprocess.run(
                    [cc, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=120, check=False,
                )
                self.output.info(
                    "%s: %s --version (rc=%s):\n%s"
                    % (label, cc, proc.returncode, (proc.stdout or "").strip()[:2000])
                )
            except (OSError, subprocess.SubprocessError) as err:
                self.output.info(
                    "%s: cannot run %s --version: %s" % (label, cc, err)
                )
        toolchain = ""
        if build_folder and os.path.isdir(build_folder):
            for root, _dirs, files in os.walk(build_folder):
                if "conan_toolchain.cmake" in files:
                    toolchain = os.path.join(root, "conan_toolchain.cmake")
                    break
        if toolchain:
            interesting = (
                "CMAKE_SYSTEM_NAME", "CMAKE_SYSTEM_PROCESSOR",
                "CMAKE_C_COMPILER", "CMAKE_CXX_COMPILER",
                "CMAKE_SYSROOT", "CMAKE_C_COMPILER_TARGET",
                "CMAKE_CXX_COMPILER_TARGET",
            )
            try:
                with open(toolchain, "r", encoding="utf-8", errors="replace") as fh:
                    kept = [ln.rstrip() for ln in fh
                            if any(k in ln for k in interesting)]
                self.output.info(
                    "%s: %s compiler/system lines:\n%s"
                    % (label, toolchain, "\n".join(kept[:40]) or "(none)")
                )
            except OSError as err:
                self.output.info(
                    "%s: cannot read %s: %s" % (label, toolchain, err)
                )
        else:
            self.output.info("%s: conan_toolchain.cmake not found" % label)

    def _compiler_runs(self, path):
        """True only if path is a file AND `path --version` exits 0."""
        if not path or not os.path.isfile(path):
            return False
        try:
            proc = subprocess.run(
                [path, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return proc.returncode == 0

    def _candidate_compilers(self, conf_cc):
        """Yield candidate clang paths, most-likely first, deduplicated.

        Sources are derived ONLY from the live sandbox (never hardcoded
        worker layouts): PATH lookup, LD_LIBRARY_PATH sibling bin dirs
        (the profile's SDK llvm/lib entry points at the SDK tree), and a
        bounded ancestor walk around the conf path / SDK dirs.
        """
        seen = set()

        def _emit(path):
            if not path:
                return
            real = os.path.realpath(path)
            if real not in seen:
                seen.add(real)
                yield real

        # 1) PATH lookup (HMBS prepends its tool dirs; profile adds the SDK).
        for name in ("clang",):
            found = shutil.which(name)
            if found:
                for p in _emit(found):
                    yield p
        # 2) Sibling bin/ dirs of every LD_LIBRARY_PATH entry: <sdk>/llvm/lib
        #    -> <sdk>/llvm/bin/clang (the profile's own SDK hint).
        for entry in (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep):
            entry = entry.strip()
            if not entry or not os.path.isdir(entry):
                continue
            parent = os.path.dirname(entry.rstrip(os.path.sep))
            for cand in (os.path.join(parent, "bin", "clang"),
                         os.path.join(entry, "..", "bin", "clang")):
                cand = os.path.normpath(cand)
                if os.path.isfile(cand):
                    for p in _emit(cand):
                        yield p
        # 3) Bounded ancestor walk around the conf path and LD dirs: cover
        #    wrapper-moved layouts (<root>/bin/clang, <root>/llvm/bin/clang,
        #    <root>/native/llvm/bin/clang, ohos-sdk.org tree variants).
        roots = set()
        if conf_cc and os.path.sep in conf_cc:
            node = os.path.dirname(os.path.realpath(conf_cc))
            for _ in range(3):
                roots.add(node)
                parent = os.path.dirname(node)
                if parent == node:
                    break
                node = parent
        for entry in (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep):
            entry = entry.strip()
            if entry and os.path.sep in entry:
                node = os.path.realpath(entry)
                for _ in range(4):
                    roots.add(node)
                    parent = os.path.dirname(node)
                    if parent == node:
                        break
                    node = parent
        rels = (os.path.join("bin", "clang"),
                os.path.join("llvm", "bin", "clang"),
                os.path.join("native", "llvm", "bin", "clang"),
                os.path.join("ohos", "native", "llvm", "bin", "clang"))
        for root in sorted(roots):
            for rel in rels:
                cand = os.path.join(root, rel)
                if os.path.isfile(cand):
                    for p in _emit(cand):
                        yield p

    def _ensure_working_compilers(self):
        """Compiler-existence gate (cycle-7, fail-closed).

        Verifies the conf compilers are runnable. When they are (CI
        workers), returns without touching anything. When the conf path is
        sandbox-invisible (preflight evidence: Errno 2 on
        /data/service/hnp/bin/clang), resolves a verified-runnable SDK
        clang from the live sandbox and rewrites the GENERATED
        conan_toolchain.cmake compiler lines to it. Raises ConanException
        with the tried-candidate list when nothing runnable is found —
        never fakes a compiler, never skips a check.
        """
        conf = {}
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            conf = {}
        conf_cc = conf.get("c", "")
        conf_cxx = conf.get("cpp", "")
        if conf_cc and self._compiler_runs(conf_cc) and \
                conf_cxx and self._compiler_runs(conf_cxx):
            self.output.info(
                "compiler gate: conf compilers runnable (%s, %s); "
                "toolchain untouched" % (conf_cc, conf_cxx)
            )
            return
        self.output.warning(
            "compiler gate: conf compiler missing/unrunnable "
            "(c=%s, cpp=%s); resolving a runnable SDK clang from the "
            "live sandbox ..." % (conf_cc or "(unset)", conf_cxx or "(unset)")
        )
        tried = []
        resolved_cc = ""
        for cand in self._candidate_compilers(conf_cc):
            tried.append(cand)
            if self._compiler_runs(cand):
                resolved_cc = cand
                break
        if not resolved_cc:
            raise ConanException(
                "compiler gate: conf C compiler '%s' is not runnable in "
                "this sandbox and no runnable clang candidate was found. "
                "Tried: %s; PATH=%s; LD_LIBRARY_PATH=%s"
                % (conf_cc or "(unset)",
                   ", ".join(tried) or "(none found)",
                   os.environ.get("PATH", ""),
                   os.environ.get("LD_LIBRARY_PATH", ""))
            )
        # CXX: same-tree clang++ first, then conf cpp, then PATH.
        resolved_cxx = ""
        sibling = os.path.join(os.path.dirname(resolved_cc), "clang++")
        for cand in (sibling, conf_cxx, shutil.which("clang++") or ""):
            if cand and self._compiler_runs(cand):
                resolved_cxx = os.path.realpath(cand)
                break
        if not resolved_cxx:
            raise ConanException(
                "compiler gate: resolved C compiler %s but found no "
                "runnable clang++ (tried %s, %s)"
                % (resolved_cc, sibling, conf_cxx or "(unset)")
            )
        self.output.info(
            "compiler gate: resolved runnable compilers c=%s cpp=%s "
            "(tried %d candidate(s))" % (resolved_cc, resolved_cxx, len(tried))
        )
        self._rewrite_toolchain_compilers(resolved_cc, resolved_cxx)

    def _rewrite_toolchain_compilers(self, cc, cxx):
        """Point the GENERATED conan_toolchain.cmake at verified compilers.

        Only the recipe's own generated file is edited (one set() line per
        language); upstream CMakeLists and the shared profile are untouched.
        """
        build_folder = self.build_folder or ""
        files = glob.glob(os.path.join(build_folder, "**", "conan_toolchain.cmake"),
                          recursive=True)
        if not files:
            raise ConanException(
                "compiler gate: conan_toolchain.cmake not found under %s; "
                "cannot apply resolved compilers (%s, %s)"
                % (build_folder, cc, cxx)
            )
        for path in files:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError as err:
                raise ConanException(
                    "compiler gate: cannot read %s: %s" % (path, err)
                )
            updated = []
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("set(CMAKE_C_COMPILER"):
                    updated.append('set(CMAKE_C_COMPILER "%s")' % cc)
                elif stripped.startswith("set(CMAKE_CXX_COMPILER"):
                    updated.append('set(CMAKE_CXX_COMPILER "%s")' % cxx)
                else:
                    updated.append(line)
            try:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write("\n".join(updated) + "\n")
            except OSError as err:
                raise ConanException(
                    "compiler gate: cannot rewrite %s: %s" % (path, err)
                )
            self.output.info(
                "compiler gate: %s now uses c=%s cpp=%s" % (path, cc, cxx)
            )

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        self._ensure_working_compilers()
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            self._dump_cmake_diagnostics("libleidenalg")
            raise
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["libleidenalg"]
        self.cpp_info.requires = ["igraph::igraph"]
        self.cpp_info.set_property("cmake_file_name", "libleidenalg")
        self.cpp_info.set_property("cmake_target_name", "libleidenalg::libleidenalg")
        self.cpp_info.set_property("pkg_config_name", "libleidenalg")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
