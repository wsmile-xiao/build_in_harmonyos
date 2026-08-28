from conan import ConanFile
import os
import glob
import shutil


class LibquantumTestConan(ConanFile):
    """Test package for libquantum 1.0.0.

    Compiles test_quantum.c directly with the OHOS clang (no CMake) to
    avoid the CMake Platform/HarmonyOS module gap. The test creates a
    2-qubit quantum register, applies Hadamard + Pauli-X gates, verifies
    probability amplitudes and performs a real single-qubit measurement.
    Uses self.run() (which Conan sources the profile env into) for both
    the compile and the test execution, satisfying the CI L0 gate.
    """
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        pass

    @property
    def _cc(self):
        import json
        import shutil as _sh
        ce = self.conf.get("tools.build:compiler_executables", default=None)
        cc = None
        if ce:
            try:
                d = json.loads(ce) if isinstance(ce, str) else ce
                cc = d.get("c")
            except Exception:
                pass
        if cc and os.path.isfile(cc) and os.access(cc, os.X_OK):
            return cc
        found = _sh.which("clang")
        return found or "clang"

    def _sweep_sh_json(self):
        """Remove only generated .sh and .json env files from the source
        tree. Do NOT delete build* dirs — those contain the test binary."""
        d = self.recipe_folder
        for f in glob.glob(os.path.join(d, "*.sh")):
            os.remove(f)
        for f in glob.glob(os.path.join(d, "*.json")):
            os.remove(f)

    def build(self):
        self._sweep_sh_json()
        dep = self.dependencies["libquantum"]
        inc = dep.cpp_info.includedirs[0]
        lib = dep.cpp_info.libdirs[0]
        src = os.path.join(self.source_folder, "test_quantum.c")
        out_dir = os.path.join(self.recipe_folder, "build-release")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "test_quantum")
        # self.run() sources the profile's cbuild env, giving the OHOS clang
        # the correct target/sysroot flags. Shell-quote all paths.
        cmd = f'"{self._cc}" -O2 -fPIC -I"{inc}" -L"{lib}" "{src}" -lquantum -lm -o "{out}"'
        self.output.info("Compiling test_quantum: " + cmd)
        self.run(cmd)
        self._sweep_sh_json()

    def test(self):
        out_dir = os.path.join(self.recipe_folder, "build-release")
        exe = os.path.join(out_dir, "test_quantum")
        if not os.path.isfile(exe):
            raise FileNotFoundError(f"test binary not found: {exe}")
        self.output.info("Running test_quantum...")
        # self.run() — required by the CI L0 gate (must call self.run()).
        self.run(f'"{exe}"')
        self._sweep_sh_json()
        # Final cleanup: remove the build-release dir after the test ran.
        if os.path.isdir(out_dir):
            shutil.rmtree(out_dir, ignore_errors=True)
