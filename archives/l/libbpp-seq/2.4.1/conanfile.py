#!/usr/bin/env python3
"""Conan recipe — libbpp-seq 2.4.1 (CMake).

Bio++ Sequence library for phylogenetic sequence analysis.
Upstream builds both bpp-seq-static and bpp-seq-shared targets (OUTPUT_NAME
bpp-seq, SOVERSION 12) plus 7 ctest unit tests linked against the shared lib.
This recipe builds and runs the full upstream ctest suite in build() before
packaging, and keeps the upstream bpp-seq-config.cmake package files so
downstream Bio++ modules (bpp-phyl, bpp-popgen) keep working via
find_package(bpp-seq CONFIG).

Dependency note: upstream bpp-seq 2.4.1 requires bpp-core 2.4.1
(find_package(bpp-core 4.0.0 REQUIRED)). libbpp-core/2.4.1 is not yet
published to the ohpcd remote, so declaring a Conan requires() would fail
graph resolution (L0i/R36) and block preflight/CI before compilation starts.
To keep this PR single-package (PF1) and buildable, this recipe vendors
bpp-core 2.4.1 sources (conandata.yml `bpp_core` entry), builds them first
into a private prefix inside the build folder, and points bpp-seq at that
prefix via CMAKE_PREFIX_PATH. Both libraries and both CMake package configs
(bpp-seq-config.cmake + bpp-core-config.cmake) are merged into this package
so downstream find_package() semantics are preserved until libbpp-core is
published separately.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibbppSeqConan(ConanFile):
    name = "libbpp-seq"
    version = "2.4.1"
    description = "Bio++ Sequence library for phylogenetic sequence analysis"
    license = "CECILL-2.1"
    homepage = "https://github.com/BioPP/bpp-seq"
    url = "https://github.com/BioPP/bpp-seq"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
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

    # No requirements(): bpp-core 2.4.1 is vendored from source (see
    # conandata.yml `bpp_core` + _build_bundled_bpp_core). libbpp-core/2.4.1
    # is not in the ohpcd remote; a requires() would fail L0i/R36 graph
    # resolution before the build even starts.

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["bpp_core"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "bpp-core-src"),
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.shared
        ) or bool(self.options.get_safe("fPIC", True))
        # Upstream registers 7 unit tests under test/ via BUILD_TESTING.
        tc.cache_variables["BUILD_TESTING"] = True
        # Upstream declares cmake_minimum_required(VERSION 2.8.11); allow
        # modern CMake (>=4) to configure it in compatibility mode.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Vendored bpp-core prefix (built in build() before configure).
        # The directory does not exist at generate() time yet; CMake only
        # reads it during build()/configure(), by then it is installed.
        core_prefix = os.path.join(self.build_folder, "bpp-core-prefix")
        tc.cache_variables["CMAKE_PREFIX_PATH"] = core_prefix.replace("\\", "/")
        # Shipped shared libs live side by side in package lib/; $ORIGIN lets
        # the installed libbpp-seq.so find its sibling libbpp-core.so where
        # the loader honors RUNPATH (LD_LIBRARY_PATH remains the primary
        # mechanism in test_package).
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        self._build_bundled_bpp_core()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._dump_elf_info(os.path.join(self.build_folder, "src", "libbpp-seq.so"), "build-tree libbpp-seq")
        self._run_upstream_tests()

    def _cmake_bin(self):
        """Resolve the cmake executable across CI and HMBS preflight hosts.

        Raw subprocess.run() does not inherit Conan's aggregated buildenv
        (conanbuild.sh); the CI worker base PATH carries neither cmake nor
        curl (PR #10479 build #48961: FileNotFoundError 'cmake'). Order
        follows the rapidjson/pam-u2f precedent: HMBS conf, HMBS env, PATH,
        then the absolute HNP tool directories shared by CI and preflight.
        """
        try:
            conf_path = self.conf.get("user.hmbs:cmake_path", default=None, check_type=str)
        except Exception:
            conf_path = None
        for cand in (conf_path, os.environ.get("HMBS_CMAKE"), os.environ.get("CMAKE")):
            if cand and os.path.isfile(cand):
                return cand
        found = shutil.which("cmake")
        if found:
            return found
        for cand in (
            "/data/service/hnp/bin/cmake",
            "/storage/Users/currentUser/usr/local/bin/cmake",
            "/usr/local/bin/cmake",
            "/usr/bin/cmake",
        ):
            if os.path.isfile(cand):
                return cand
        self.output.warning("cmake not found via conf/env/PATH/HNP fallbacks; trying bare 'cmake'")
        return "cmake"

    def _ctest_bin(self):
        """Resolve ctest alongside the cmake above (they ship together)."""
        cmake_bin = self._cmake_bin()
        if cmake_bin and os.path.dirname(cmake_bin):
            sibling = os.path.join(os.path.dirname(cmake_bin), "ctest")
            if os.path.isfile(sibling):
                return sibling
        found = shutil.which("ctest")
        if found:
            return found
        for cand in (
            "/data/service/hnp/bin/ctest",
            "/storage/Users/currentUser/usr/local/bin/ctest",
            "/usr/local/bin/ctest",
            "/usr/bin/ctest",
        ):
            if os.path.isfile(cand):
                return cand
        self.output.warning("ctest not found via cmake sibling/PATH/HNP fallbacks; trying bare 'ctest'")
        return "ctest"

    def _build_bundled_bpp_core(self):
        """Configure/build/install vendored bpp-core 2.4.1 into a private prefix."""
        core_src = os.path.join(self.source_folder, "bpp-core-src")
        core_build = os.path.join(self.build_folder, "bpp-core-build")
        core_prefix = os.path.join(self.build_folder, "bpp-core-prefix")
        if not os.path.isdir(core_src):
            raise RuntimeError("vendored bpp-core sources missing: %s" % core_src)
        os.makedirs(core_build, exist_ok=True)
        os.makedirs(core_prefix, exist_ok=True)
        # Toolchain generated by generate() above.
        candidates = [
            os.path.join(self.generators_folder, "conan_toolchain.cmake"),
            os.path.join(self.build_folder, "conan_toolchain.cmake"),
            os.path.join(self.build_folder, "build", "conan_toolchain.cmake"),
        ]
        toolchain = next((p for p in candidates if os.path.isfile(p)), candidates[0])
        cmake_bin = self._cmake_bin()
        self.output.info("vendored bpp-core cmake binary: %s" % cmake_bin)
        build_type = str(self.settings.build_type)
        pic = bool(self.options.shared) or bool(self.options.get_safe("fPIC", True))
        configure_cmd = [
            cmake_bin,
            "-S", core_src,
            "-B", core_build,
            "-DCMAKE_TOOLCHAIN_FILE=" + toolchain,
            "-DCMAKE_INSTALL_PREFIX=" + core_prefix,
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DCMAKE_INSTALL_RPATH=$ORIGIN",
            "-DBUILD_TESTING=OFF",
            "-DCMAKE_BUILD_TYPE=" + build_type,
            "-DCMAKE_POSITION_INDEPENDENT_CODE=" + ("ON" if pic else "OFF"),
        ]
        self.output.info("vendored bpp-core configure: " + " ".join(configure_cmd))
        proc = subprocess.run(
            configure_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
        )
        self.output.info((proc.stdout or "")[-3000:])
        if proc.returncode != 0:
            raise RuntimeError("vendored bpp-core configure failed")
        build_cmd = [cmake_bin, "--build", core_build, "--parallel", "1"]
        self.output.info("vendored bpp-core build: " + " ".join(build_cmd))
        proc = subprocess.run(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
        )
        self.output.info((proc.stdout or "")[-3000:])
        if proc.returncode != 0:
            raise RuntimeError("vendored bpp-core build failed")
        install_cmd = [cmake_bin, "--install", core_build]
        self.output.info("vendored bpp-core install: " + " ".join(install_cmd))
        proc = subprocess.run(
            install_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
        )
        self.output.info((proc.stdout or "")[-2000:])
        if proc.returncode != 0:
            raise RuntimeError("vendored bpp-core install failed")
        self._dump_elf_info(os.path.join(core_prefix, "lib", "libbpp-core.so"), "vendored libbpp-core")
        # Sanity: the config file bpp-seq will find must exist.
        cfg = os.path.join(core_prefix, "lib", "cmake", "bpp-core", "bpp-core-config.cmake")
        cfg_alt = os.path.join(core_prefix, "lib64", "cmake", "bpp-core", "bpp-core-config.cmake")
        if not (os.path.isfile(cfg) or os.path.isfile(cfg_alt)):
            self.output.warning("vendored bpp-core config not found at %s" % cfg)
        return core_prefix

    def _dump_elf_info(self, path, tag):
        """Best-effort readelf -d dump to diagnose OHOS loader failures.

        Prints SONAME/DT_NEEDED/RUNPATH of a built .so into the log so the
        next preflight shows ground truth. Never fails the build.
        """
        try:
            import shutil
            if not path or not os.path.isfile(path):
                self.output.info("elf-info [%s]: not found: %s" % (tag, path))
                return
            tool = (
                shutil.which("readelf")
                or shutil.which("llvm-readelf")
                or shutil.which("eu-readelf")
            )
            if tool is None:
                for base in (
                    os.path.dirname(os.environ.get("HMBS_CMAKE", "")),
                    "/data/service/hnp/bin",
                    "/usr/bin",
                ):
                    for name in ("readelf", "llvm-readelf"):
                        cand = os.path.join(base, name) if base else ""
                        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                            tool = cand
                            break
                    if tool is not None:
                        break
            if tool is None:
                self.output.info("elf-info [%s]: no readelf tool found" % tag)
                return
            proc = subprocess.run(
                [tool, "-d", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            out = proc.stdout or ""
            interesting = [
                line for line in out.splitlines()
                if any(k in line for k in ("SONAME", "NEEDED", "RPATH", "RUNPATH"))
            ]
            self.output.info(
                "elf-info [%s] via %s:\n%s" % (tag, tool, "\n".join(interesting[-20:]) or out[-1500:])
            )
        except Exception as exc:
            self.output.info("elf-info [%s]: skipped (%s)" % (tag, exc))

    def _ctest_lib_paths(self):
        """Collect absolute dirs holding build-tree shared libs for OHOS loader.

        Upstream tests link against bpp-seq-shared (build-tree src/) which
        itself needs the vendored bpp-core shared lib (bpp-core-prefix/).
        The OHOS/musl loader does not resolve build-tree RUNPATH entries
        here ("Error loading shared library ../src/libbpp-seq.so",
        "../bpp-core-prefix/lib/libbpp-core.so"), so ctest must run with
        LD_LIBRARY_PATH covering those absolute directories.
        """
        lib_dirs = []
        core_prefix = os.path.join(self.build_folder, "bpp-core-prefix")
        for d in (
            os.path.join(core_prefix, "lib"),
            os.path.join(core_prefix, "lib64"),
            os.path.join(self.build_folder, "src"),
            os.path.join(self.build_folder, "bpp-core-build", "src"),
        ):
            if os.path.isdir(d) and d not in lib_dirs:
                lib_dirs.append(d)
        try:
            for root, _dirs, files in os.walk(self.build_folder):
                if any(f.startswith("libbpp-") and ".so" in f for f in files):
                    if root not in lib_dirs:
                        lib_dirs.append(root)
                    if len(lib_dirs) > 20:
                        break
        except Exception:
            pass
        return lib_dirs

    def _run_upstream_tests(self):
        """Run the 7 upstream ctest cases and emit the HMBS evidence marker.

        The result is also persisted to build_folder/upstream_test_result.json
        so package() can ship it under res/ and test_package can re-emit it.
        This keeps the evidence visible even when conan reuses a cached
        package and skips build().
        """
        # 7 test .cpp files in test/ at v2.4.1 (audited via GitHub API):
        # test_alignment_scores, test_alphabets, test_bowker,
        # test_containers, test_io, test_sequences, test_walker.
        discovered = 7
        if not can_run(self):
            self.output.info("cross-building: 7 upstream ctest cases compiled but cannot run")
            upstream = {
                "status": "skipped",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": discovered,
                "reason": "cross-building: can_run() is false",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
            try:
                with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8", newline="\n") as fh:
                    json.dump(upstream, fh, ensure_ascii=False, indent=2)
                    fh.write("\n")
            except Exception as exc:
                self.output.warning("cannot persist upstream result: %s" % exc)
            return upstream
        # Resolve ctest to an absolute binary the same way as cmake: bare
        # subprocess calls do not inherit Conan's aggregated buildenv, and
        # the CI worker base PATH has no ctest (same class of failure as
        # build #48961's missing cmake). No shell features are used below,
        # so ctest runs directly instead of via a shell wrapper.
        ctest_bin = self._ctest_bin()
        self.output.info("ctest binary: %s" % ctest_bin)
        # The musl loader ignores build-tree RUNPATH here, so export absolute
        # LD_LIBRARY_PATH entries for bpp-seq-shared + vendored bpp-core.
        lib_dirs = self._ctest_lib_paths()
        self.output.info("ctest lib dirs: %s" % (":".join(lib_dirs) if lib_dirs else "<none>"))
        env = dict(os.environ)
        if lib_dirs:
            old_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(lib_dirs) + (":" + old_ld if old_ld else "")
        cmd = "ctest --output-on-failure"
        try:
            proc = subprocess.run(
                [ctest_bin, "--output-on-failure"],
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
                env=env,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("ctest binary not found: %s (%s)" % (ctest_bin, exc))
        output = proc.stdout or ""
        self.output.info(output[-4000:])
        executed = 0
        passed = 0
        failed = 0
        # CTest summary: "100% tests passed, 0 tests failed out of 7"
        m = re.search(r"(\d+)% tests passed,\s*(\d+) tests failed out of (\d+)", output)
        if m is not None:
            total = int(m.group(3))
            failed = int(m.group(2))
            executed = total
            passed = total - failed
        else:
            # Fallback: count per-test "Passed" lines.
            passed = len(re.findall(r"\.\.\.\s*Passed", output))
            failed = len(re.findall(r"\.\.\.\s*(?:Failed|Timeout)", output))
            executed = passed + failed
        if executed == 0:
            raise RuntimeError("upstream ctest produced no test results")
        status = "passed" if proc.returncode == 0 and failed == 0 and executed == discovered else "failed"
        upstream = {
            "status": status,
            "framework": "ctest",
            "command": cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        try:
            with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8", newline="\n") as fh:
                json.dump(upstream, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
        except Exception as exc:
            self.output.warning("cannot persist upstream result: %s" % exc)
        if status != "passed":
            raise RuntimeError("upstream ctest failed: executed=%d passed=%d failed=%d" % (executed, passed, failed))
        return upstream

    def package(self):
        copy(self, "COPYING.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Keep the vendored bpp-core license alongside.
        core_src = os.path.join(self.source_folder, "bpp-core-src")
        if os.path.isdir(core_src):
            copy(self, "COPYING*", src=core_src, dst=os.path.join(self.package_folder, "licenses"))
            copy(self, "LICENSE*", src=core_src, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Merge the vendored bpp-core install (libs/headers/cmake configs)
        # into this package so find_package(bpp-core) keeps working.
        core_prefix = os.path.join(self.build_folder, "bpp-core-prefix")
        if os.path.isdir(core_prefix):
            copy(self, "*", src=core_prefix, dst=self.package_folder)
        # Conan semantics: shared=False must not ship broken .so files.
        # Upstream always installs both static+shared, but the installed
        # libbpp-seq.so carries a slash-containing DT_NEEDED
        # ("../bpp-core-prefix/lib/libbpp-core.so") that the OHOS/musl loader
        # resolves literally (RUNPATH/LD_LIBRARY_PATH ignored), so any
        # consumer resolving to the shared object fails at startup. Prune the
        # unrequested variant so downstream can only pick the working one.
        import glob
        for libdir in (os.path.join(self.package_folder, "lib"),
                       os.path.join(self.package_folder, "lib64")):
            if not os.path.isdir(libdir):
                continue
            if not self.options.shared:
                for pat in ("*.so", "*.so.*"):
                    for victim in glob.glob(os.path.join(libdir, pat)):
                        try:
                            if os.path.islink(victim) or os.path.isfile(victim):
                                os.remove(victim)
                                self.output.info("package: pruned %s (shared=False)" % victim)
                        except Exception as exc:
                            self.output.warning("package: cannot prune %s (%s)" % (victim, exc))
            else:
                for pat in ("*.a",):
                    for victim in glob.glob(os.path.join(libdir, pat)):
                        try:
                            if os.path.isfile(victim):
                                os.remove(victim)
                                self.output.info("package: pruned %s (shared=True)" % victim)
                        except Exception as exc:
                            self.output.warning("package: cannot prune %s (%s)" % (victim, exc))
        self._dump_elf_info(os.path.join(self.package_folder, "lib", "libbpp-seq.so"), "installed libbpp-seq")
        self._dump_elf_info(os.path.join(self.package_folder, "lib", "libbpp-core.so"), "installed libbpp-core")
        # Ship the upstream ctest evidence so test_package can re-emit it on
        # cache hits (build() is skipped then, libcanard pattern).
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        # Both archives are installed (upstream always builds static+shared
        # pair); consumers need bpp-seq first, then its bpp-core dependency.
        self.cpp_info.libs = ["bpp-seq", "bpp-core"]
        # Keep Conan's generated config under the libbpp-seq name so it does
        # not shadow the upstream bpp-seq-config.cmake (needed by bpp-phyl).
        self.cpp_info.set_property("cmake_file_name", "libbpp-seq")
        self.cpp_info.set_property("cmake_target_name", "libbpp-seq::libbpp-seq")
        self.cpp_info.set_property("pkg_config_name", "libbpp-seq")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
