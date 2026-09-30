#!/usr/bin/env python3
"""Installed-package API tests for kim-api 2.4.1."""

import glob
import json
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


TEST_EXECUTABLES = ("kimapi_semver_contract", "kimapi_collections_contract")


class KimApiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _probe_compiler(self, cc):
        """True if cc exists and executes --version successfully."""
        if not cc:
            return False
        p = cc.strip().strip('"').strip("'").split(" ")[0]
        if not p:
            return False
        exe = p if os.path.isfile(p) else shutil.which(p)
        if not exe:
            return False
        try:
            r = subprocess.run(
                [exe, "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _select_compilers(self):
        """Pick working C/C++ compilers, falling back from dead conf paths.

        Mirrors the main kim-api recipe (metashell/5.0.0 precedent): the
        profile compiler (/data/service/hnp/bin/clang{,++}) can be a dead
        path inside the preflight container. Probe it; only when it is
        missing or fails --version, fall back to the PATH-discovered
        clang/clang++ (HMBS prepends the real toolchain dirs).
        Returns (c, cxx, fell_back).
        """
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            conf = {}
        conf = conf if isinstance(conf, dict) else {}
        c_conf = conf.get("c")
        cxx_conf = conf.get("cpp")
        c_path = shutil.which("clang")
        cxx_path = shutil.which("clang++")
        c = c_conf
        cxx = cxx_conf
        fell_back = False
        if not self._probe_compiler(c_conf):
            if c_path and self._probe_compiler(c_path):
                self.output.warning(
                    "kim-api-test: configured C compiler "
                    f"{c_conf!r} is dead, falling back to PATH {c_path}"
                )
                c = c_path
                fell_back = True
            else:
                self.output.warning(
                    f"kim-api-test: configured C compiler {c_conf!r} is dead "
                    f"and no working PATH clang ({c_path!r}); keeping config"
                )
        if not self._probe_compiler(cxx_conf):
            if cxx_path and self._probe_compiler(cxx_path):
                self.output.warning(
                    "kim-api-test: configured C++ compiler "
                    f"{cxx_conf!r} is dead, falling back to PATH {cxx_path}"
                )
                cxx = cxx_path
                fell_back = True
            else:
                self.output.warning(
                    f"kim-api-test: configured C++ compiler {cxx_conf!r} is dead "
                    f"and no working PATH clang++ ({cxx_path!r}); keeping config"
                )
        if fell_back:
            self.output.info(f"kim-api-test: compilers selected C={c} CXX={cxx}")
        return c, cxx, fell_back

    def _dump_cmake_logs(self):
        """Emit CMake configure failure forensics into the conan output."""
        patterns = (
            "**/CMakeFiles/CMakeError.log",
            "**/CMakeFiles/CMakeOutput.log",
        )
        for pat in patterns:
            for log in sorted(glob.glob(os.path.join(self.build_folder, pat))):
                try:
                    with open(log, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                except OSError as e:
                    self.output.error(f"kim-api-test: cannot read {log}: {e}")
                    continue
                tail = lines[-60:] if len(lines) > 60 else lines
                self.output.error(
                    f"kim-api-test: --- {log} ({len(lines)} lines, tail) ---"
                )
                for line in tail:
                    self.output.error(f"kim-api-test: {line.rstrip()}"[:2000])

    def generate(self):
        # tmx/1.10.1 precedent: serial cap for the consumer build as well;
        # the small shared runner OOM-kills even tiny consumers when the
        # daemon schedules back-to-back parallel links.
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        tc = CMakeToolchain(self)
        # tmx/1.10.1 precedent: pin the working compiler into the toolchain
        # cache so the dead profile path never reaches the test configure.
        # Only override when the configured path is actually dead (probe
        # above); otherwise keep the profile compiler untouched.
        c_sel, cxx_sel, fell_back = self._select_compilers()
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            conf = {}
        conf = conf if isinstance(conf, dict) else {}
        c_old = conf.get("c")
        cxx_old = conf.get("cpp")
        if fell_back:
            if c_sel:
                tc.cache_variables["CMAKE_C_COMPILER"] = c_sel
                tc.variables["CMAKE_C_COMPILER"] = c_sel
            if cxx_sel:
                tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx_sel
                tc.variables["CMAKE_CXX_COMPILER"] = cxx_sel
        tc.generate()
        CMakeDeps(self).generate()
        # Belt and suspenders (tmx/1.10.1): the cache pin alone did not
        # override the stale profile compiler on some true devices, so
        # rewrite the generated conan_toolchain.cmake single file and
        # export CC/CXX -- only when the configured path is dead.
        pairs = []
        if (
            fell_back
            and c_old
            and c_sel
            and c_old != c_sel
            and not self._probe_compiler(c_old)
            and os.path.exists(c_sel)
        ):
            pairs.append((c_old, c_sel))
        if (
            fell_back
            and cxx_old
            and cxx_sel
            and cxx_old != cxx_sel
            and not self._probe_compiler(cxx_old)
            and os.path.exists(cxx_sel)
        ):
            pairs.append((cxx_old, cxx_sel))
        if pairs:
            try:
                gf = getattr(self, "generators_folder", None)
                path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
                if path and os.path.isfile(path):
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                    orig = text
                    for old_p, new_p in pairs:
                        text = text.replace(old_p, new_p)
                    if text != orig:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(text)
                        self.output.info(
                            "kim-api-test: fixed toolchain %s" % path
                        )
                else:
                    self.output.warning(
                        "kim-api-test: toolchain not found: %s" % path
                    )
            except Exception as e:
                self.output.warning("kim-api-test: toolchain fix failed: %s" % e)
            try:
                comp_env = Environment()
                for old_p, new_p in pairs:
                    if old_p == c_old:
                        comp_env.define("CC", new_p)
                    if old_p == cxx_old:
                        comp_env.define("CXX", new_p)
                comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
            except Exception as e:
                self.output.warning("kim-api-test: compiler env failed: %s" % e)

    def build(self):
        # Explicit serial consumer build (experience 1: library and consumer
        # both serially capped). Covers the daemon's back-to-back link peak.
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # Sync the compiler fallback into the build env so the toolchain
        # cache and CC/CXX-driven probes agree.
        _c, _cxx, fell_back = self._select_compilers()
        if fell_back:
            if _c:
                os.environ["CC"] = _c
            if _cxx:
                os.environ["CXX"] = _cxx
            self.output.info(f"kim-api-test: build env CC={_c} CXX={_cxx}")
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                self.output.info(f"kim-api-test: {key}={val}")
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            self._dump_cmake_logs()
            raise
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        if not can_run(self):
            raise ConanException("kim-api target consumers are not runnable")
        runtime_dir = None
        try:
            if str(self.settings.os) == "OHOS":
                runtime_dir = tempfile.mkdtemp(
                    prefix="kimapi-test-", dir="/data/storage/el2/base/cache"
                )
            for name in TEST_EXECUTABLES:
                executable = os.path.join(self.cpp.build.bindir, name)
                if runtime_dir is not None:
                    staged = os.path.join(runtime_dir, name)
                    shutil.copy2(executable, staged)
                    self._sign_ohos_elf(staged)
                    executable = staged
                self.run(f'"{executable}"', env="conanrun")
        finally:
            if runtime_dir is not None:
                shutil.rmtree(runtime_dir, ignore_errors=True)
        # Both consumer executables exited 0 above: 2 real cases.
        self._hmbs_emit(
            "HMBS_TEST_PACKAGE_RESULT="
            + json.dumps(
                {
                    "executed": True,
                    "passed": True,
                    "command": "kimapi_semver_contract && kimapi_collections_contract",
                    "discovered": 2,
                    "passedCount": 2,
                },
                separators=(",", ":"),
            )
        )
        # Re-emit the real upstream result carried in the package res so
        # cache-hit runs still provide evidence every round (zydis
        # precedent). The main-recipe build() runs the 46-case ctest suite
        # for real and persists hmbs_upstream.json into res/; a missing or
        # inconsistent payload here means the recipe is broken, so fail.
        try:
            res = os.path.join(
                self.dependencies["kim-api"].package_folder,
                "res", "hmbs_upstream.json")
            with open(res, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            raise ConanException(
                f"kim-api-test: packaged upstream evidence missing: {e}")
        try:
            discovered = int(payload.get("discovered"))
            executed = int(payload.get("executed"))
            passed = int(payload.get("passed"))
            failed = int(payload.get("failed"))
            skipped = int(payload.get("skipped"))
        except Exception:
            raise ConanException(
                f"kim-api-test: upstream payload counts illegal: {payload}")
        if (discovered <= 0 or executed <= 0
                or passed + failed != executed
                or executed + skipped > discovered
                or executed > discovered
                or any(v < 0 for v in (
                    discovered, executed, passed, failed, skipped))):
            raise ConanException(
                f"kim-api-test: upstream payload inconsistent: {payload}")
        self._hmbs_emit(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(payload, separators=(",", ":")))

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
