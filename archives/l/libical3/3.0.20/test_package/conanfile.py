import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class Libical3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
            tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"
        tc.generate()
        self._write_cmake_paths()

    def _dep_folder(self, name):
        for dep in self.dependencies.values():
            if dep.ref and dep.ref.name == name and dep.package_folder:
                return dep.package_folder
        return None

    def _write_cmake_paths(self):
        """test 的 find_package(LibIcal) 依赖 conan 生成的 CMakeDeps
        目录；glib 系走 PkgConfig（PkgConfigDeps 只生成单一
        glib-2.0.pc，gobject-2.0 需包内原生 .pc）——复制 glib 包的
        .pc 并修正 prefix（与主配方 pc-fix 同法）。
        """
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        glib = self._dep_folder("glib")
        if glib:
            pc_fix = os.path.join(self.generators_folder, "pc-fix")
            os.makedirs(pc_fix, exist_ok=True)
            pcdir = os.path.join(glib, "lib", "pkgconfig")
            if os.path.isdir(pcdir):
                for pc_name in ("glib-2.0.pc", "gobject-2.0.pc"):
                    src = os.path.join(pcdir, pc_name)
                    if not os.path.isfile(src):
                        continue
                    with open(src, "r", encoding="utf-8") as fh:
                        text = fh.read()
                    text = text.replace(
                        "prefix=/", f"prefix={glib}", 1)
                    # Requires(.private) 剥 proxy-libintl / 置空 private
                    out = []
                    for line in text.splitlines():
                        stripped = line.strip()
                        if stripped.startswith("Requires.private:"):
                            out.append("Requires.private:")
                            continue
                        if stripped.startswith("Requires:") and \
                                "proxy-libintl" in stripped:
                            out.append("Requires:")
                            continue
                        out.append(line)
                    with open(os.path.join(pc_fix, pc_name), "w",
                              encoding="utf-8") as fh:
                        fh.write("\n".join(out) + "\n")
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            package_folder = dep.package_folder.replace("\\", "/")
            lines.extend([
                f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")',
            ])
        lines.extend([
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ])
        with open(os.path.join(self.generators_folder,
                               "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # PKG_CONFIG_PATH 进程内注入（glib-2.0/gobject-2.0 .pc 解析）
        env = Environment()
        glib = self._dep_folder("glib")
        if glib:
            env.prepend_path("PKG_CONFIG_PATH",
                             os.path.join(self.generators_folder, "pc-fix"))
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        self._prepare_runtime_links()
        if self.settings.os == "OHOS":
            self._sign_runtime_elfs()
        env = Environment()
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..",
                                          "bin")),
        ]
        runtime_var = "PATH" if self.settings.os == "Windows" \
            else "LD_LIBRARY_PATH"
        for runtime_dir in runtime_dirs:
            env.prepend_path(runtime_var, runtime_dir)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(runtime_var,
                                 os.path.join(dep.package_folder, "bin"))
                env.prepend_path(runtime_var,
                                 os.path.join(dep.package_folder, "lib"))
        ctest = self._ctest_executable()
        with env.vars(self).apply():
            self.run(
                '{} --test-dir "{}" --output-on-failure '
                '--no-tests=error'.format(
                    self._quote(ctest), self.build_folder))
            self.run(os.path.join(self.cpp.build.bindirs[0],
                                  "test_libical3"), env=None)

    def _ctest_executable(self):
        ctest = os.environ.get("CTEST_EXECUTABLE") or shutil.which("ctest")
        if ctest:
            return ctest
        cmake_program = self.conf.get("tools.cmake:cmake_program")
        if cmake_program:
            candidate = os.path.join(os.path.dirname(cmake_program),
                                     "ctest.exe")
            if os.path.isfile(candidate):
                return candidate
            candidate = os.path.join(os.path.dirname(cmake_program), "ctest")
            if os.path.isfile(candidate):
                return candidate
        return "ctest"

    def _prepare_runtime_links(self):
        """被测包相对 soname（./libical.so 等）需与测试可执行同目录。
        同时 glib/libxml2（shared）与被测包 so 复制到运行目录。
        """
        runtime_dirs = [
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..",
                                          "bin")),
        ]
        for runtime_dir in runtime_dirs:
            os.makedirs(runtime_dir, exist_ok=True)
        for dep in self.dependencies.values():
            package_folder = dep.package_folder
            if not package_folder:
                continue
            candidates = []
            for libdir, pattern in (
                (os.path.join(package_folder, "bin"), "*.dll"),
                (os.path.join(package_folder, "lib"), "lib*.so*"),
            ):
                if os.path.isdir(libdir):
                    candidates.extend(glob.glob(os.path.join(libdir,
                                                             pattern)))
            for src in candidates:
                for runtime_dir in runtime_dirs:
                    dst = os.path.join(runtime_dir,
                                       os.path.basename(src))
                    if os.path.exists(dst):
                        continue
                    shutil.copy2(src, dst)

    def _sign_runtime_elfs(self):
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS llvm-objcopy and binary-sign-tool are required "
                "for ELF signing")
        paths = {os.path.join(self.cpp.build.bindirs[0], "test_libical3")}
        for root in (
            self.cpp.build.bindirs[0],
            os.path.normpath(os.path.join(self.build_folder, "..", "..",
                                          "bin")),
        ):
            for name in glob.glob(os.path.join(root, "lib*.so*")):
                paths.add(name)
        for path in sorted(paths):
            if os.path.islink(path) or not os.path.isfile(path) \
                    or not self._is_elf(path):
                continue
            self.run(
                f"{self._quote(objcopy)} --remove-section .codesign "
                f"{self._quote(path)} 2>/dev/null || true")
            self.run(
                f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                f"-outFile {self._quote(path)} -selfSign 1")

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"

    @staticmethod
    def _quote(value):
        return '"' + value.replace('"', '\\"') + '"'
