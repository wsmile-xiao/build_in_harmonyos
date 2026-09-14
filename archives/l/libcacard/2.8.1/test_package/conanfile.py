#!/usr/bin/env python3
"""Installed-package consumer for libcacard 2.8.1.

Builds test_cacard.c against the installed libcacard (headers under
include/cacard/, link -lcacard) and runs it. The test exercises the
real option-parsing and card-type-mapping API; no NSS database or
smart-card hardware is required. Emits HMBS_TEST_PACKAGE_RESULT with
the real assertion count from the test source (6 checks).
"""

import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibcacardTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            toolchain.cache_variables["CMAKE_SKIP_RPATH"] = True
        # Same stale-profile clang as the main recipe (this round fails
        # at test_package `cmake.configure`: CMAKE_C_COMPILER
        # /data/service/hnp/bin/clang is missing on this worker).
        # CMakeToolchain bakes tools.build:compiler_executables into
        # conan_toolchain.cmake, so exporting CC/CXX in build() alone
        # cannot fix it. Pin the cache variables to a usable compiler
        # before generate() and patch the file afterwards.
        for _kind, _var in (("c", "CMAKE_C_COMPILER"),
                            ("cpp", "CMAKE_CXX_COMPILER")):
            _exe = self._discover_compiler(_kind)
            if _exe and os.path.isfile(_exe):
                toolchain.cache_variables[_var] = _exe
        toolchain.generate()
        self._repair_cmake_toolchain()
        VirtualRunEnv(self).generate()

    def build(self):
        # CMake compiler checks spill temp files into TMPDIR; the
        # default /tmp is read-only on this target (readonly_tmp).
        with self._writable_tmp().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            # Cross build: the consumer cannot run here, but the
            # upstream evidence from build() is still forwarded when
            # the package carries it (cache-hit runs skip build()).
            self._reemit_upstream_result()
            self.output.warning(
                "Cross build: the consumer linked but was not run on this host."
            )
            return
        # 6 explicit checks in test_cacard.c
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "./libcacard_consumer",
            "discovered": 6,
            "passedCount": 6,
        }
        suffix = ".exe" if self.settings.os == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "libcacard_consumer" + suffix
        )
        self._sign_elf_for_ohos(executable)
        try:
            self.run(
                '"{}"'.format(executable), env="conanrun", cwd=self.build_folder
            )
        except Exception:
            test_pkg["passed"] = False
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg)
            )
            self._reemit_upstream_result()
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg))
        self._reemit_upstream_result()

    def _reemit_upstream_result(self):
        """Re-emit the build-time upstream marker on cache-hit runs.

        When `conan create --build=missing` reuses the cached binary,
        the main recipe build() (and its HMBS_UPSTREAM_TEST_RESULT
        stdout marker) is skipped. The marker JSON shipped under
        share/libcacard/ in the package carries the real meson counts
        from the original build; re-emit it verbatim so every
        test_package run provides upstream evidence. Missing file:
        warn only, never fabricate a pass.
        """
        pkg_folder = ""
        for accessor in ("host", None):
            try:
                if accessor is None:
                    dep = self.dependencies["libcacard"]
                else:
                    dep = getattr(self.dependencies, accessor)["libcacard"]
                pkg_folder = str(dep.package_folder or "")
                if pkg_folder:
                    break
            except Exception:
                continue
        if not pkg_folder:
            self.output.warning(
                "HMBS upstream re-emit: libcacard package folder not found"
            )
            return False
        candidates = [
            os.path.join(
                pkg_folder, "share", "libcacard", "hmbs_upstream_result.json"
            ),
            os.path.join(pkg_folder, "share", "hmbs_upstream_result.json"),
            os.path.join(pkg_folder, "hmbs_upstream_result.json"),
            os.path.join(pkg_folder, "res", "hmbs_upstream_result.json"),
        ]
        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    marker = json.load(handle)
                if not isinstance(marker, dict):
                    raise ValueError("marker is not an object")
                for key in ("status", "framework", "command", "discovered",
                            "executed", "passed", "failed", "skipped"):
                    if key not in marker:
                        raise ValueError(
                            "marker missing key: {}".format(key)
                        )
                self.output.info(
                    "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
                )
                self.output.info(
                    "HMBS upstream re-emitted from package file: "
                    "{}".format(path)
                )
                return True
            except Exception as exc:
                self.output.warning(
                    "HMBS upstream re-emit failed for {}: {}".format(
                        path, exc
                    )
                )
                return False
        self.output.warning(
            "HMBS upstream re-emit: no persisted result file in package "
            "(expected from a fresh build with the updated recipe; "
            "not fabricating evidence)"
        )
        return False

    def _discover_compiler(self, kind):
        # Full copy of the main-recipe probe: profile path when it
        # exists, else CC/CXX env, PATH clang, HNP convention path and
        # the OHOS SDK llvm dir. Returns None when nothing usable is
        # found so the original CMake error is preserved.
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict,
            )
        except Exception:
            conf = {}
        configured = ""
        if isinstance(conf, dict):
            configured = (conf.get(kind) or "").strip()
        if configured and os.path.isfile(configured):
            return configured
        env_name = "CC" if kind == "c" else "CXX"
        env_val = (os.environ.get(env_name) or "").strip()
        if env_val:
            resolved = shutil.which(env_val)
            if resolved:
                return resolved
            if os.path.isfile(env_val):
                return env_val
        bare = "clang" if kind == "c" else "clang++"
        for probe in (bare, bare + "-15"):
            found = shutil.which(probe)
            if found:
                return found
        for candidate in (
            "/data/service/hnp/bin/" + bare,
            "/data/service/hnp/bin/clang",
            "/data/service/hnp/bin/clang++",
        ):
            if os.path.isfile(candidate):
                return candidate
        try:
            import glob
            for pattern in (
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/" + bare,
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang*",
            ):
                for hit in sorted(glob.glob(pattern)):
                    if os.path.isfile(hit):
                        return hit
        except Exception:
            pass
        return configured or None

    def _repair_cmake_toolchain(self):
        # Belt-and-suspenders for the cache_variables pin above: if the
        # profile path was already rendered into conan_toolchain.cmake
        # (or the pin was skipped because discovery failed), replace
        # only entries whose file is missing.
        try:
            toolchain_path = os.path.join(
                self.generators_folder, "conan_toolchain.cmake")
        except Exception:
            return
        if not os.path.isfile(toolchain_path):
            return
        import re
        replacements = {}
        for kind, var in (("c", "CMAKE_C_COMPILER"),
                          ("cpp", "CMAKE_CXX_COMPILER")):
            exe = self._discover_compiler(kind)
            if exe and os.path.isfile(exe):
                replacements[var] = exe
        if not replacements:
            return
        with open(toolchain_path, encoding="utf-8") as handle:
            content = handle.read()
        original = content
        for var, exe in replacements.items():
            def _swap(match):
                current = (match.group(2) or "").strip().strip("\"'")
                if current and os.path.isfile(current):
                    return match.group(0)
                self.output.info(
                    "HMBS compiler repair: {} '{}' -> '{}'".format(
                        var, current, exe))
                return match.group(1) + '"' + exe + '"' + match.group(3)
            content = re.sub(
                r"^(\s*set\s*\(\s*" + var + r"\s+)([^\r\n]*?)(\s*\)[^\r\n]*)$",
                _swap, content, count=1, flags=re.MULTILINE)
        if content != original:
            with open(toolchain_path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _writable_tmp(self):
        # Same source as the main recipe: prefer the HMBS-injected
        # writable TMPDIR/TMP/TEMP, fall back to a build-folder dir.
        for candidate in (
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
        ):
            if candidate and os.path.isdir(candidate):
                tmpdir = candidate
                break
        else:
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        # Same compiler fallback as the main recipe: if the profile
        # clang path is absent on this worker, export a usable CC/CXX
        # so CMake try-compiles do not reuse the stale absolute path.
        for kind, var in (("c", "CC"), ("cpp", "CXX")):
            found = self._discover_compiler(kind)
            if found and os.path.isfile(found):
                env.define(var, found)
                bindir = os.path.dirname(found)
                if bindir and os.path.isdir(bindir):
                    try:
                        env.prepend_path("PATH", bindir)
                    except Exception:
                        pass
        return env

    def _find_ohos_tool(self, name):
        candidates = []
        if name == "binary-sign-tool":
            try:
                conf_val = self.conf.get(
                    "user.ohos:sign_tool", default="", check_type=str
                )
            except Exception:
                conf_val = ""
            if conf_val and conf_val.strip():
                candidates.append(conf_val.strip())
            env_val = (os.environ.get("OHOS_SIGN_TOOL") or "").strip()
            if env_val:
                candidates.append(env_val)
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables",
                default={}, check_type=dict,
            ) or {}
        except Exception:
            compilers = {}
        compiler = ""
        if isinstance(compilers, dict):
            compiler = compilers.get("c", "") or compilers.get("cpp", "")
        compiler_dir = os.path.dirname(compiler) if compiler else ""
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _sign_elf_for_ohos(self, path):
        if self.settings.os != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        readelf = self._find_ohos_tool("llvm-readelf")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                "consumer executable is missing: {}".format(path)
            )
        if not objcopy or not readelf or not signer:
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are required for target "
                "execution (missing: {})".format(
                    ",".join(
                        label for label, tool in (
                            ("llvm-objcopy", objcopy),
                            ("llvm-readelf", readelf),
                            ("binary-sign-tool", signer),
                        ) if not tool
                    )
                )
            )
        self.output.info(
            "HMBS sign tools: objcopy='{}' readelf='{}' signer='{}'".format(
                objcopy, readelf, signer
            )
        )
        clean_path = "{}.codesign-clean".format(path)
        signed_path = "{}.signed".format(path)
        for temporary in (clean_path, signed_path):
            if os.path.exists(temporary):
                os.remove(temporary)
        try:
            self.run(
                "{} --remove-section .codesign {} {}".format(
                    shlex.quote(objcopy),
                    shlex.quote(path),
                    shlex.quote(clean_path),
                )
            )
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer),
                    shlex.quote(clean_path),
                    shlex.quote(signed_path),
                )
            )
            sections = subprocess.run(
                [readelf, "-SW", signed_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    "signed consumer has invalid .codesign count"
                )
            try:
                original_mode = os.stat(path).st_mode & 0o7777
            except OSError:
                original_mode = 0o755
            with open(signed_path, "rb") as handle:
                signed_bytes = handle.read()
            with open(path, "wb") as handle:
                handle.write(signed_bytes)
            target_mode = original_mode | 0o111
            if not (target_mode & 0o100):
                target_mode = 0o755
            self._chmod_if_supported(path, target_mode)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)

    @staticmethod
    def _chmod_if_supported(path, mode):
        # Same as the main recipe (cycle 18): the signer output can
        # lose the exec bit, so always attempt chmod and only tolerate
        # filesystems that refuse the operation.
        try:
            os.chmod(path, mode)
        except OSError as exc:
            import errno
            if exc.errno in (errno.EPERM, errno.EACCES, errno.EROFS,
                             errno.ENOTSUP, errno.EOPNOTSUPP):
                return
            raise
