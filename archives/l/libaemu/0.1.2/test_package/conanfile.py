#!/usr/bin/env python3
"""Conan test_package for libaemu/0.1.2.

Consumer links libaemu::libaemu and exercises the real aemu-base API
(StringFormat family). test() runs the binary, parses the deterministic
TEST_PACKAGE_SUMMARY trailer line, and emits HMBS_TEST_PACKAGE_RESULT.
It also re-emits the upstream ctest evidence carried by the main recipe
when available.
"""
import glob
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout


class LibaemuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "CMakeLists.txt", "test_libaemu.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ohos_toolchain(self):
        try:
            ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                               default=[], check_type=list)
        except Exception:
            ut = []
        candidates = list(ut) if isinstance(ut, list) else ([ut] if ut else [])
        for env_key, suffix in (("OHOS_NDK_HOME", "build/cmake/ohos.toolchain.cmake"),
                                ("OHOS_SDK_HOME", "ohos/native/build/cmake/ohos.toolchain.cmake")):
            ndk = os.environ.get(env_key, "")
            if ndk:
                candidates.append(os.path.join(ndk, suffix))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        home = os.path.expanduser("~")
        for base in ("/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk",
                     os.path.join(home, ".harmonybrew/Cellar/ohos-sdk")):
            patterns.append(os.path.join(base, "*/native/build/cmake/ohos.toolchain.cmake"))
        for pat in patterns:
            try:
                found = sorted(glob.glob(pat))
            except Exception:
                continue
            if found:
                return found[-1]
        raise ConanInvalidConfiguration("Cannot find ohos.toolchain.cmake for test_package")

    def generate(self):
        # No CMakeToolchain: the consumer must build with the same SDK
        # toolchain as the library, otherwise host headers mismatch.
        # CMakeDeps is still required: test CMakeLists calls
        # find_package(libaemu REQUIRED), whose libaemu-config.cmake is
        # emitted by CMakeDeps into the generators folder. Without it the
        # configure dies with 'By not providing \"Findlibaemu.cmake\"'
        # (this round's test-package failure). linux template precedent:
        # generators = CMakeDeps + CMakeToolchain.
        from conan.tools.cmake import CMakeDeps
        if str(self.settings.os) == "OHOS":
            try:
                CMakeDeps(self).generate()
            except Exception as e:
                self.output.warning("HMBS diag test CMakeDeps failed: %s" % e)
            try:
                tc = self._ohos_toolchain()
                self.output.info("HMBS diag test ohos.toolchain: %s" % tc)
            except Exception as e:
                self.output.warning("HMBS diag test toolchain lookup: %s" % e)
        else:
            from conan.tools.cmake import CMakeToolchain
            CMakeToolchain(self).generate()
            CMakeDeps(self).generate()

    def _hmbs_wrapper_toolchain(self, sdk_toolchain):
        # Round-14: mirror of the main recipe wrapper (include SDK first,
        # then string(APPEND) -stdlib so it survives FORCE-sets).
        bdir = os.path.join(self.build_folder, "build-ohos")
        try:
            os.makedirs(bdir, exist_ok=True)
        except Exception:
            pass
        wrapper = os.path.join(bdir, "hmbs-aemu-test-ohos-tc.cmake")
        content = (
            '# HMBS wrapper toolchain for libaemu test_package (round-14)\n'
            'include("%s")\n'
            'string(APPEND CMAKE_CXX_FLAGS " -stdlib=libc++")\n'
            'string(APPEND CMAKE_EXE_LINKER_FLAGS " -stdlib=libc++")\n'
            'string(APPEND CMAKE_SHARED_LINKER_FLAGS " -stdlib=libc++")\n'
            'string(APPEND CMAKE_MODULE_LINKER_FLAGS " -stdlib=libc++")\n'
            % sdk_toolchain.replace("\\", "/")
        )
        # test_package must resolve the libaemu-config.cmake emitted by
        # CMakeDeps into the generators folder, but the SDK toolchain sets
        # CMAKE_FIND_ROOT_PATH_MODE_*=ONLY which masks CMAKE_PREFIX_PATH
        # (kxl/1.2.4 + flameshot precedent). Force BOTH after the include so
        # find_package(libaemu) locates the Conan config. A -D on the
        # command line cannot override the SDK toolchain (synfig
        # precedent), hence set() here.
        content += (
            'set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)\n'
            'set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY BOTH)\n'
            'set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)\n'
        )
        try:
            _gen = getattr(self, "generators_folder", "") or ""
            if _gen:
                _esc = _gen.replace("\\", "/")
                content += (
                    'list(APPEND CMAKE_PREFIX_PATH "%s")\n'
                    'list(APPEND CMAKE_FIND_ROOT_PATH "%s")\n' % (_esc, _esc)
                )
        except Exception:
            pass
        try:
            old = ""
            if os.path.isfile(wrapper):
                with open(wrapper, "r", encoding="utf-8",
                          errors="replace") as f:
                    old = f.read()
            if old != content:
                with open(wrapper, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception as e:
            self.output.warning("HMBS diag test wrapper write failed: %s" % e)
        return wrapper

    def build(self):
        if str(self.settings.os) == "OHOS":
            sdk_tc = self._ohos_toolchain()
            toolchain = self._hmbs_wrapper_toolchain(sdk_tc)
            # Round-13: same safe-append as the main recipe (xqilla
            # extra_cxxflags equivalent); never via -D FLAGS (round-11).
            try:
                cxxf = os.environ.get("CXXFLAGS", "")
                if "-stdlib=libc++" not in cxxf:
                    os.environ["CXXFLAGS"] = (cxxf + " -stdlib=libc++").strip()
                ldf = os.environ.get("LDFLAGS", "")
                if "-stdlib=libc++" not in ldf:
                    os.environ["LDFLAGS"] = (ldf + " -stdlib=libc++").strip()
            except Exception as e:
                self.output.warning("HMBS diag test stdlib env failed: %s" % e)
            bdir = os.path.join(self.build_folder, "build-ohos")
            _gen_prefix = (getattr(self, "generators_folder", "") or "").replace("\\", "/")
            _prefix_def = (' "-DCMAKE_PREFIX_PATH=%s"' % _gen_prefix) if _gen_prefix else ""
            self.run('cmake -B "%s" -S "%s" -DCMAKE_TOOLCHAIN_FILE="%s" '
                     '"-DOHOS_ARCH=arm64-v8a" "-DCMAKE_BUILD_TYPE=%s" '
                     '"-DCMAKE_CXX_STANDARD=17" '
                     '"-DCMAKE_CXX_STANDARD_REQUIRED=ON"%s'
                     % (bdir, self.source_folder, toolchain, self.settings.build_type,
                        _prefix_def))
            self.run('cmake --build "%s"' % bdir)
        else:
            from conan.tools.cmake import CMake
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _find_test_binary(self):
        cands = [
            os.path.join(self.build_folder, "build-ohos", "test_libaemu"),
            os.path.join(self.build_folder, "test_libaemu"),
        ]
        try:
            for d in self.cpp.build.bindirs:
                cands.append(os.path.join(d, "test_libaemu"))
        except Exception:
            pass
        for c in cands:
            if os.path.isfile(c):
                return c
        return cands[0]

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer compiled and linked")
            return
        test_bin = self._find_test_binary()
        proc = subprocess.run(
            [test_bin],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            check=False,
        )
        out = proc.stdout or ""
        for line in out.splitlines()[-20:]:
            self.output.info("[test_package] %s" % line)
        m = re.search(
            r"TEST_PACKAGE_SUMMARY:\s*passed=(\d+)\s+failed=(\d+)\s+total=(\d+)",
            out,
        )
        if not m:
            raise ConanException(
                "test_libaemu produced no TEST_PACKAGE_SUMMARY line"
            )
        passed = int(m.group(1))
        failed = int(m.group(2))
        total = int(m.group(3))
        if passed < 0 or failed < 0 or total < 0 or passed + failed != total:
            raise ConanException(
                "test_libaemu summary identities violated "
                "(passed=%d failed=%d total=%d)" % (passed, failed, total)
            )
        ok = proc.returncode == 0 and failed == 0 and total > 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_libaemu",
            "discovered": total,
            "passedCount": passed,
        }
        print(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False),
            flush=True,
        )
        if not ok:
            raise ConanException(
                "test_libaemu failed: passed=%d failed=%d total=%d"
                % (passed, failed, total)
            )
