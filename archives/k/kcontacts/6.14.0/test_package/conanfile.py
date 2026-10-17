#!/usr/bin/env python3
"""Conan test_package for kcontacts 6.14.0."""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KContactsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("kcodecs/6.14.0")
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()

        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_package_folder(folder):
            if not folder:
                return
            for collection, value in (
                (prefixes, os.path.join(folder, "lib", "cmake")),
                (libraries, os.path.join(folder, "lib")),
                (includes, os.path.join(folder, "include")),
            ):
                normalized = value.replace("\\", "/")
                if normalized not in collection:
                    collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                add_package_folder(dep.package_folder)

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            for rel in ("cmake", "modules", "find-modules", "kde-modules"):
                path = os.path.join(ecm_share, rel).replace("\\", "/")
                if rel == "cmake" and path not in prefixes:
                    prefixes.append(path)
                if path not in modules:
                    modules.append(path)

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            f'set(CMAKE_PREFIX_PATH "{";".join(prefixes)};${{CMAKE_PREFIX_PATH}}")',
            f'set(CMAKE_LIBRARY_PATH "{";".join(libraries)};${{CMAKE_LIBRARY_PATH}}")',
            f'set(CMAKE_INCLUDE_PATH "{";".join(includes)};${{CMAKE_INCLUDE_PATH}}")',
            f'set(CMAKE_MODULE_PATH "{";".join(modules)};${{CMAKE_MODULE_PATH}}")',
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            with self._cmake_host_tool_env().vars(self).apply():
                self._run_ohos_cmake_configure()
                self._run_with_ohos_lld_runtime(
                    f"cmake --build {self._quote(self.build_folder)}"
                )
        else:
            cmake.configure()
            cmake.build()

    def _cmake_host_tool_env(self):
        env = Environment()
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        return env

    def _run_ohos_cmake_configure(self):
        os.makedirs(self.build_folder, exist_ok=True)
        cmd = " ".join(
            [
                "cmake",
                '-G "Unix Makefiles"',
                f"-S {self._quote(self.source_folder)}",
                f"-B {self._quote(self.build_folder)}",
                f"-DCMAKE_TOOLCHAIN_FILE={self._quote(os.path.join(self.generators_folder, 'conan_toolchain.cmake'))}",
                '-DCMAKE_POLICY_DEFAULT_CMP0091="NEW"',
                f'-DCMAKE_BUILD_TYPE="{self.settings.build_type}"',
            ]
        )
        self._run_with_ohos_lld_runtime(cmd)

    def _run_with_ohos_lld_runtime(self, command):
        sdk_llvm_lib = self._ohos_sdk_llvm_lib()
        prefix = 'LD_LIBRARY_PATH="{}${{LD_LIBRARY_PATH:+:${{LD_LIBRARY_PATH}}}}" '.format(
            sdk_llvm_lib
        )
        self.run(prefix + command, env="conanbuild")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _configured_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for key in ("c", "cpp"):
            compiler = compilers.get(key)
            if compiler:
                return compiler
        return shutil.which("clang") or shutil.which("cc") or ""

    def _ohos_sdk_llvm_lib(self):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return ""

        candidates = []
        compiler = self._configured_compiler()
        if compiler:
            compiler_parts = shlex.split(str(compiler))
            compiler_exe = compiler_parts[0] if compiler_parts else ""
            if compiler_exe:
                candidates.append(
                    os.path.normpath(os.path.join(os.path.realpath(os.path.dirname(compiler_exe)), os.pardir, "lib"))
                )
            try:
                result = subprocess.run(
                    compiler_parts + ["-print-resource-dir"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
            except OSError as exc:
                raise ConanException(f"Cannot run configured OHOS compiler {compiler}: {exc}") from exc
            if result.returncode != 0:
                raise ConanException(
                    "Cannot query OHOS compiler resource dir with -print-resource-dir: "
                    + result.stderr.strip()
                )
            resource_dir = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
            if resource_dir:
                candidates.append(os.path.normpath(os.path.join(resource_dir, os.pardir, os.pardir)))

        sdk_base = os.environ.get("OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        candidates.extend(
            sorted(glob.glob(os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib")))
        )
        ndk_home = os.environ.get("OHOS_NDK_HOME", "")
        if ndk_home:
            candidates.append(os.path.join(ndk_home, "llvm", "lib"))

        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            llvm_lib = os.path.realpath(os.path.normpath(candidate))
            if llvm_lib in seen:
                continue
            seen.add(llvm_lib)
            if not os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
                continue
            self._probe_ohos_lld(llvm_lib)
            self.output.info(f"Using OHOS SDK llvm/lib for lld runtime: {llvm_lib}")
            return llvm_lib

        raise ConanException(
            "Cannot locate OHOS SDK llvm/lib containing libxml2.so.16 for lld runtime"
        )

    def _probe_ohos_lld(self, sdk_llvm_lib):
        lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
        if not os.path.isfile(lld):
            lld = shutil.which("lld") or os.path.join("/data/service/hnp/bin", "lld")
        if not os.path.isfile(lld):
            raise ConanException("Cannot locate OHOS SDK lld for runtime probe")

        env = os.environ.copy()
        old_ld_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = sdk_llvm_lib + (os.pathsep + old_ld_path if old_ld_path else "")
        try:
            result = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                check=False,
            )
        except OSError as exc:
            raise ConanException(f"Cannot run OHOS lld probe {lld}: {exc}") from exc
        if result.returncode != 0:
            raise ConanException(
                "OHOS lld probe failed with SDK llvm/lib runtime: "
                + (result.stderr.strip() or result.stdout.strip())
            )

    def test(self):
        self._prepare_runtime_links()
        self._bridge_legacy_conan_cache_root()
        env = Environment()
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            env.prepend_path("LD_LIBRARY_PATH", runtime_dir)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("XDG_DATA_DIRS", os.path.join(dep.package_folder, "share"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_kcontacts")
        ohos_test_exe = os.path.join(self.cpp.build.bindirs[0], "test_kcontacts_ohos")
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )
            self.run(test_exe, cwd=self.cpp.build.bindirs[0])
            self.run(ohos_test_exe, cwd=self.cpp.build.bindirs[0])

    def _bridge_legacy_conan_cache_root(self):
        # Temporary platform cache-root bridge. The release machines built and
        # published the dependency packages with the conan cache rooted at
        # ~/.conan2, so their .so files carry absolute DT_NEEDED entries such as
        #   /storage/Users/currentUser/.conan2/p/<phash>/p/lib/libKF6*.so
        # The PR-check workers keep the same cache under ~/.cache/conan2 and
        # musl performs no fallback for slash-qualified NEEDED entries, so the
        # loader fails unless every baked path also exists locally. Until the
        # SONAME full-family fix for the published dependencies lands, recreate
        # each baked prefix as a symlink to the real package folder. This does
        # not touch the test oracle; it only makes the already-published
        # absolute-path NEEDED entries resolvable on machines whose conan root
        # differs. Best-effort: skipped when the path already matches.
        for dep in self.dependencies.values():
            try:
                folder = dep.package_folder if dep else None
                if not folder:
                    continue
                idx = folder.rfind("/p/")
                if idx < 0:
                    continue
                rest = folder[idx + 1:]
                legacy = os.path.expanduser("~/.conan2") + "/" + rest
                if os.path.abspath(legacy) == os.path.abspath(folder):
                    continue
                if os.path.lexists(legacy):
                    continue
                os.makedirs(os.path.dirname(legacy), exist_ok=True)
                os.symlink(folder, legacy)
                self.output.info(f"cache-root bridge created: {legacy}")
            except Exception as exc:
                self.output.warning(
                    f"cache-root bridge skipped for "
                    f"{getattr(dep, 'name', 'dependency')}: {exc}"
                )

    def _prepare_runtime_links(self):
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..", "bin")),
        ]
        for runtime_dir in runtime_dirs:
            os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if not libdir or not os.path.isdir(libdir):
                continue
            for src in glob.glob(os.path.join(libdir, "lib*.so*")):
                for runtime_dir in runtime_dirs:
                    dst = os.path.join(runtime_dir, os.path.basename(src))
                    target = os.path.realpath(src)
                    if os.path.realpath(dst) == target:
                        continue
                    if os.path.lexists(dst):
                        os.unlink(dst)
                    os.symlink(target, dst)
