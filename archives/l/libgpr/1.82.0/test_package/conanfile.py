from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        abseil = self.dependencies["abseil-cpp"]
        tc = CMakeToolchain(self)
        pkg = self.dependencies["libgpr"]
        tc.variables["LIBGPR_LIB_DIR"] = os.path.join(
            pkg.package_folder, "lib").replace("\\", "/")
        tc.variables["LIBGPR_INC_DIR"] = os.path.join(
            pkg.package_folder, "include").replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _sdk_lib_dir(conanfile):
        """Directory holding libc++_shared.so / libunwind.so for OHOS."""
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"
            "/llvm/lib/aarch64-linux-ohos",
        ]
        try:
            import json
            execs = conanfile.conf.get("tools.build:compiler_executables")
            if isinstance(execs, str):
                execs = json.loads(execs)
            cc = (execs or {}).get("c") or (execs or {}).get("cpp") or ""
            if cc:
                llvm = os.path.dirname(os.path.dirname(cc))
                candidates.append(os.path.join(llvm, "lib", "aarch64-linux-ohos"))
        except Exception:
            pass
        for cand in candidates:
            if os.path.isdir(cand):
                return cand
        return ""

    def test(self):
        if can_run(self):
            env = Environment()
            sdk_lib = self._sdk_lib_dir(self)
            if sdk_lib:
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            with env.vars(self).apply():
                self.run("ctest --output-on-failure --no-tests=error",
                         cwd=self.build_folder, env="conanrun")