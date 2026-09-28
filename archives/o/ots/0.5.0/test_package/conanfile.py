#!/usr/bin/env python3
"""test_package for ots 0.5.0 — installed-package consumer verification.

Builds test_ots.c against the installed libots-1 (CMake + CMakeDeps),
runs it (3 real API checks: parse, grade, summarize), and smoke-tests
the installed `ots` CLI binary (`ots --version` needs no dictionary).
Emits HMBS evidence markers with real counts.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class OtsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, kind):
        """Resolve a working C/C++ compiler, tolerating a stale profile path.

        The ohos-aarch64 profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang(++). On some preflight workers that
        absolute path does not exist while a working clang is on PATH
        (e.g. harmonybrew); the main recipe already works around this via
        _resolve_ohos_compiler, but the vanilla CMakeToolchain trusts the
        stale conf value and emits a broken CMAKE_C_COMPILER, failing
        cmake configure at project(). Mirror the main-recipe chain here:
        conf -> env -> PATH -> well-known OHOS dirs. No hardcoded
        ephemeral /storage/... paths; no CMAKE_SYSTEM_NAME override.
        """
        import shlex
        try:
            conf_map = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            conf_map = {}
        conf_key = "c" if kind == "c" else "cpp"
        env_key = "CC" if kind == "c" else "CXX"
        bare = "clang" if kind == "c" else "clang++"
        conf_val = (conf_map.get(conf_key, "") or "").strip()
        if conf_val:
            try:
                first = shlex.split(conf_val)[0]
            except Exception:
                first = conf_val
            if first and os.path.isabs(first) and os.path.isfile(first):
                return conf_val
        try:
            env_val = (os.environ.get(env_key, "") or "").strip()
        except Exception:
            env_val = ""
        if env_val:
            try:
                first = shlex.split(env_val)[0]
            except Exception:
                first = env_val
            if first:
                if os.path.isabs(first):
                    if os.path.isfile(first):
                        return first
                else:
                    resolved = shutil.which(first)
                    if resolved:
                        return resolved
        which_bare = shutil.which(bare)
        if which_bare:
            return which_bare
        for cand in (
            os.path.expanduser(os.path.join("~/.harmonybrew/bin", bare)),
            os.path.join("/data/service/hnp/bin", bare),
        ):
            if cand and os.path.isfile(cand):
                return cand
        return None

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cpp")
        if cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
            self.output.info(f"OTS test_package CMAKE_C_COMPILER={cc}")
        if cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
            self.output.info(f"OTS test_package CMAKE_CXX_COMPILER={cxx}")
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_ohos_elf(self, path):
        """OHOS XPM requires a .codesign section on executed ELF binaries."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        temporary = path + ".ots-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary], check=True, capture_output=True,
            text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return
        executable = os.path.join(self.cpp.build.bindir, "test_ots")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        # Stage en.xml next to the test cwd: ots_load_xml_dictionary(name)
        # checks "./<name>.xml" first, then the baked DICTIONARY_DIR. The
        # baked dir is prefix-staged ("/share/ots/") so it misses the conan
        # package share dir at runtime; the local copy guarantees the
        # ParserBreak rules load without touching library code.
        try:
            ots_dep_pre = self.dependencies["ots"]
            _dic_candidates = [
                os.path.join(ots_dep_pre.package_folder, "share", "ots", "en.xml"),
                os.path.join(ots_dep_pre.package_folder, "res", "ots", "en.xml"),
            ]
            try:
                for _rd in (ots_dep_pre.cpp_info.resdirs or []):
                    _dic_candidates.append(os.path.join(ots_dep_pre.package_folder, _rd, "ots", "en.xml"))
                    _dic_candidates.append(os.path.join(ots_dep_pre.package_folder, _rd, "en.xml"))
            except Exception:
                pass
            _dic_src = next((c for c in _dic_candidates if os.path.isfile(c)), None)
            if _dic_src:
                import shutil as _sh
                for _dd in {self.build_folder, os.path.dirname(executable)}:
                    try:
                        os.makedirs(_dd, exist_ok=True)
                        _dst = os.path.join(_dd, "en.xml")
                        if os.path.abspath(_dic_src) != os.path.abspath(_dst):
                            _sh.copy2(_dic_src, _dst)
                    except Exception as exc:
                        self.output.warning(f"OTS dic stage to {_dd} failed: {exc}")
                self.output.info(f"OTS dic staged from {_dic_src}")
            else:
                self.output.warning(f"OTS dic not found under {ots_dep_pre.package_folder}")
        except Exception as exc:
            self.output.warning(f"OTS dic stage skipped: {exc}")
        # Real consumer run: 3 API checks, prints its own evidence marker.
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
        # CLI smoke: run the installed ots binary via absolute path.
        # VirtualRunEnv does not put the tested package's bin/ on PATH,
        # so a bare "ots --version" fails with 127 in isolated CI
        # (nng 1.10.1 precedent); resolve via dependency metadata instead
        # of relying on system PATH. Binary name "ots" comes from the
        # upstream src/Makefile (bin_PROGRAMS).
        ots_dep = self.dependencies["ots"]
        ots_bin = os.path.join(
            ots_dep.package_folder,
            ots_dep.cpp_info.bindirs[0],
            "ots",
        )
        self.run(f'"{ots_bin}" --version', env="conanrun", cwd=self.build_folder)
        marker = ('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
                  '"command":"./test_ots + ots --version",'
                  '"discovered":3,"passedCount":3}')
        self.output.info(marker)
        print(marker, flush=True)
        upstream = ('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
                    '"framework":"autotools","command":"make check",'
                    '"discovered":0,"executed":0,"passed":0,"failed":0,'
                    '"skipped":0,"reason":"ots 0.5.0 upstream tarball audited: '
                    'no TESTS/check_PROGRAMS variables, no test source files, '
                    'no tests/ directory; make check is a no-op"}')
        self.output.info(upstream)
        print(upstream, flush=True)
