#!/usr/bin/env python3
"""Conan test_package for kparts 6.18.0.

Consumer-level end-to-end verification (R34: real API usage): builds a
consumer executable against the packaged library and drives the complete
KParts::ReadOnlyPart local-file lifecycle (openUrl -> openFile() -> signals
-> closeUrl) on a real file. The same binary is reused for the DAYU200
device end-to-end evidence.
"""
import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KpartsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        qtbase = self.dependencies.get("qtbase")
        pkg = self.dependencies.get(
            self.tested_reference_str.split("/")[0]
        )
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        if pkg:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pkg.package_folder}/lib/cmake")'
            )
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")'
            )
        # KF6PartsConfig.cmake find_dependency()s KF6KIO/KF6XmlGui/etc;
        # expose every dependency's cmake dirs too.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _runtime_env(self):
        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self._all_dependencies()
                if p.package_folder
            ],
        )
        env.define("QT_QPA_PLATFORM", "offscreen")
        # CI workers run inside the OHOS sandbox whose LD_LIBRARY_PATH
        # contains an incompatible libc++_shared.so; prepend /system/lib64 so
        # the loader resolves the compatible one first (kconfig/kio 6.26.0
        # precedent, same fix as the main recipe).
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                "/ohos/native/llvm/lib",
            ):
                if os.path.isdir(llvm_lib):
                    env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return env

    def build(self):
        # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
        # SDK's llvm/lib directory; CI workers may not export it via
        # LD_LIBRARY_PATH. Must not clobber the conanbuild env on other hosts.
        env = Environment()
        llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
            "/ohos/native/llvm/lib"
        )
        if os.path.isdir(llvm_lib):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    # --- runtime closure for the OHOS musl loader -------------------------
    # Same preparation as the main recipe: the published KF6 packages carry
    # absolute DT_NEEDED paths baked on the publishing worker and relative
    # paths such as ../../bin/libKF6ConfigCore.so, which musl resolves
    # against the process CWD (LD_LIBRARY_PATH does not apply). Symlinks are
    # used because OHOS verifies the code signature of ELF files, so the
    # target must stay byte-identical.
    def _all_dependencies(self):
        result = []
        seen = set()

        def walk(dep):
            if dep is None:
                return
            key = f"{dep.ref.name}/{dep.ref.version}" if dep.ref else str(id(dep))
            if key in seen:
                return
            seen.add(key)
            result.append(dep)
            for sub in dep.dependencies.values():
                walk(sub)

        for dep in self.dependencies.values():
            walk(dep)
        return result

    def _dependency_libraries(self):
        libs = {}
        for dep in self._all_dependencies():
            if not dep or not dep.package_folder:
                continue
            for libdir in ("lib", "lib64"):
                directory = os.path.join(dep.package_folder, libdir)
                if not os.path.isdir(directory):
                    continue
                for name in sorted(os.listdir(directory)):
                    path = os.path.join(directory, name)
                    if ".so" in name and os.path.isfile(path):
                        libs.setdefault(name, path)
        return libs

    def _test_working_dirs(self, root):
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) == "Testing":
                dirnames[:] = []
                continue
            if "CTestTestfile.cmake" in filenames:
                found.append(dirpath)
            if dirpath[len(root):].count(os.sep) >= 4:
                dirnames[:] = []
        return found

    def _prepare_runtime_closure(self):
        libs = self._dependency_libraries()
        if not libs:
            return 0
        cwd_dirs = self._test_working_dirs(self.build_folder)
        cwd_dirs.append(self.build_folder)
        cwd_dirs.append(self.recipe_folder)
        needed = set()
        for path in libs.values():
            try:
                with open(path, "rb") as handle:
                    blob = handle.read()
            except OSError:
                continue
            for match in re.findall(
                rb"[/.][A-Za-z0-9_+./-]*\.so(?:\.\d+)*", blob
            ):
                name = match.decode("utf-8", "ignore")
                if name.startswith(("/", "./", "../")):
                    needed.add(name)
        linked = 0
        for entry in sorted(needed):
            real = libs.get(os.path.basename(entry))
            if not real:
                continue
            targets = (
                [entry]
                if entry.startswith("/")
                else [
                    os.path.normpath(os.path.join(cwd, entry))
                    for cwd in cwd_dirs
                ]
            )
            for target in targets:
                if os.path.lexists(target):
                    continue
                try:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    os.symlink(real, target)
                    linked += 1
                except OSError:
                    pass
        return linked

    def test(self):
        linked = self._prepare_runtime_closure()
        self.output.info(f"runtime closure: {linked} symlink(s) created")
        with self._runtime_env().vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            # L0d: run the test binary explicitly as well (the CTest wrapper
            # above is not detected as a self.run() call).
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kparts"),
                env="conanrun",
                cwd=self.build_folder,
            )
