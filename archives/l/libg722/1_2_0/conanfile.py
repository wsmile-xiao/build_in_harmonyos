#!/usr/bin/env python3
"""Conan recipe — libg722 1_2_0 (CMake).

ITU G.722 wideband speech codec (bit-exact 64/56/48 kbps implementation).
Upstream builds both a shared (g722) and a static (g722_static, output
name g722) library and registers two CTest cases (TestDynamic/TestStatic)
that run scripts/do-test.sh against test_data/ fixtures.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches


class Libg722Conan(ConanFile):
    name = "libg722"
    version = "1_2_0"
    description = "ITU G.722 wideband speech codec library (64/56/48 kbps)"
    license = "Unlicense"
    homepage = "https://github.com/sippy/libg722"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libg722 supports Linux and OHOS only, not %s" % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build both upstream library variants so the full upstream CTest
        # suite (TestDynamic + TestStatic) always runs regardless of the
        # consumer's shared option. Both artifacts are packaged.
        tc.variables["ENABLE_SHARED_LIB"] = "ON"
        tc.variables["ENABLE_STATIC_LIB"] = "ON"
        # TestDynamic links the just-built shared lib in the build tree. The
        # Conan/OHOS toolchain must not strip its build-tree RPATH (some
        # cross toolchains ship BUILD_WITH_INSTALL_RPATH=ON with an empty
        # install RPATH, leaving test binaries with no way to find the fresh
        # .so). Bake the absolute build-tree lib dirs into the binaries'
        # build RPATH so the loader finds them with no runtime env needed.
        # Test binaries are throwaway (never packaged/installed), so an
        # absolute build-path RPATH is safe here.
        rpath_dirs = [
            self.build_folder,
            os.path.join(self.build_folder, "Release"),
        ]
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = "OFF"
        tc.variables["CMAKE_BUILD_RPATH"] = ";".join(
            d.replace("\\", "/") for d in rpath_dirs
        )
        # Upstream exports plain C symbols with no visibility attributes; if
        # the cross toolchain defaults to hidden visibility the shared lib
        # would lose every g722_* symbol (static linking is unaffected,
        # which matches TestStatic passing while TestDynamic reports
        # "symbol not found"). Pin default visibility for this recipe.
        tc.variables["CMAKE_C_VISIBILITY_PRESET"] = "default"
        tc.generate()

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_ctest()

    def _ensure_writable_tmp(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def _run_upstream_ctest(self):
        # Upstream registers exactly 2 CTest cases (TestDynamic/TestStatic).
        # Run them for real and emit the HMBS machine-evidence marker.
        # do-test.sh needs `openssl` (sha256) and `diff`; both are part of
        # the HMBS/CI base environment.
        # TestDynamic links the just-built libg722.so in the build tree. The
        # Conan/OHOS toolchain does not guarantee a build-tree RPATH, so the
        # musl loader on the device may resolve a stale/absent libg722.so
        # and report "symbol not found" for every g722_* symbol while the
        # static test passes. Prepend every build-tree dir containing
        # libg722.so* to LD_LIBRARY_PATH so ctest exercises the fresh lib.
        discovered = 2
        cmd = "ctest --output-on-failure"
        lib_dirs = []
        try:
            for root, _dirs, files in os.walk(self.build_folder):
                if any(n == "libg722.so" or n.startswith("libg722.so.") for n in files):
                    lib_dirs.append(root)
        except OSError:
            lib_dirs = []
        for cand in (self.build_folder, os.path.join(self.build_folder, "Release")):
            if os.path.isdir(cand) and cand not in lib_dirs:
                lib_dirs.append(cand)
        test_env = dict(os.environ)
        if lib_dirs:
            prev = test_env.get("LD_LIBRARY_PATH", "")
            test_env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs) + (os.pathsep + prev if prev else "")
        try:
            proc = subprocess.run(
                ["ctest", "--output-on-failure"],
                cwd=self.build_folder,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=900,
            )
            output = proc.stdout or ""
            rc = proc.returncode
        except Exception as exc:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": cmd,
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "ctest harness could not run: %r" % (exc,),
            }
            self._emit_upstream(marker)
            raise ConanException("libg722 upstream ctest failed to run: %s" % exc)

        self.output.info(output[-4000:])
        passed = output.count("Passed")
        failed = output.count("Failed")
        # CTest summary looks like "50% tests passed, 1 tests failed out of 2"
        # (or "100% tests passed, 0 tests failed out of 2" on success); the
        # leading percent is not a count, so derive passed = total - failed.
        m = re.search(
            r"(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)",
            output,
            re.IGNORECASE | re.DOTALL,
        )
        if m:
            failed_n = int(m.group(1))
            total = int(m.group(2))
            passed_n = total - failed_n
        else:
            m = re.search(
                r"(\d+)\s+tests?\s+passed.*?(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)",
                output,
                re.IGNORECASE | re.DOTALL,
            )
            if m:
                total = int(m.group(3))
                passed_n = int(m.group(1))
                failed_n = int(m.group(2))
            else:
                m2 = re.search(r"tests\s+passed\s*,\s*0\s+tests\s+failed\s+out\s+of\s+(\d+)", output)
                if m2:
                    total = int(m2.group(1))
                    passed_n = total
                    failed_n = 0
                else:
                    total = discovered
                    passed_n = passed if rc == 0 else 0
                    failed_n = failed if rc != 0 else 0

        executed = passed_n + failed_n
        if rc == 0 and failed_n == 0 and passed_n == discovered and executed == discovered:
            marker = {
                "status": "passed",
                "framework": "ctest",
                "command": cmd,
                "discovered": discovered,
                "executed": executed,
                "passed": passed_n,
                "failed": 0,
                "skipped": 0,
            }
        elif rc == 0 and passed_n == 0:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": cmd,
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "exit 0 but no ctest Passed lines in output",
            }
        else:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": cmd,
                "discovered": discovered,
                "executed": executed,
                "passed": passed_n,
                "failed": failed_n,
                "skipped": max(0, discovered - executed),
            }
        self._emit_upstream(marker)
        if marker["status"] != "passed":
            raise ConanException(
                "libg722 upstream ctest failed: rc=%s passed=%s/%s"
                % (rc, passed_n, discovered)
            )

    def _emit_upstream(self, marker):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(marker, handle, ensure_ascii=False)
        except OSError:
            pass

    def package(self):
        cmake = CMake(self)
        cmake.install()
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "r",
                encoding="utf-8",
            ) as handle:
                marker = json.load(handle)
        except (OSError, ValueError):
            marker = None
        if isinstance(marker, dict) and marker.get("discovered"):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            with open(
                os.path.join(res_dir, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(marker, handle, ensure_ascii=False)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["g722"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libg722")
        self.cpp_info.set_property("cmake_target_name", "libg722::g722")
