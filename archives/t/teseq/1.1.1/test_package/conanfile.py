import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TeseqTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        """Exercise the packaged teseq/reseq binaries as a consumer would.

        No compile-time API exists for this package (it ships command-line
        tools), so the assertions run the installed binaries through Conan's
        run environment: ``self.run`` with the generated
        ``conanrun`` environment, which prepends the package bindir to PATH.
        """
        if not can_run(self):
            self.output.info(
                "Cross build: teseq consumer tests require the OHOS target; "
                "run them on the HarmonyOS PC device."
            )
            return

        bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        teseq = os.path.join(bindir, "teseq")
        reseq = os.path.join(bindir, "reseq")
        self.output.info(f"Running teseq consumer assertions against {teseq}")

        # --- 1. The shipped executables exist and are the packaged ones ----
        self.run(f'test -x "{teseq}"', env="conanrun")
        self.run(f'test -x "{reseq}"', env="conanrun")

        # --- 2. --version reports the packaged version ---------------------
        self.run(f'"{teseq}" --version | grep -F "GNU teseq 1.1.1"',
                 env="conanrun")

        # --- 3. --help is a working CLI surface ---------------------------
        # teseq and reseq both expose the timing-file option as --timings
        # (there is no --describe/--timing flag upstream).
        self.run(f'"{teseq}" --help | grep -F -- "--timings"', env="conanrun")
        self.run(f'"{reseq}" --help | grep -F -- "--timings"', env="conanrun")

        # --- 4. Real transformation: escape sequence to readable text ------
        # printf builds a CSI sequence (ESC [ 1 m = bold) plus plain text;
        # teseq must render it as a documented function name.
        self.run(
            'printf "\\033[1mBOLD\\033[0m\\n" > input.bin',
            env="conanrun")
        self.run(f'"{teseq}" input.bin > decoded.txt', env="conanrun")
        self.run('grep -F "SGR" decoded.txt', env="conanrun")
        self.run('grep -F "BOLD" decoded.txt', env="conanrun")

        # --- 5. Round trip: reseq inverts teseq ----------------------------
        # reseq takes INPUT OUTPUT (it requires two file arguments; the
        # upstream tests/run-tests harness invokes it the same way).
        self.run(f'"{reseq}" decoded.txt roundtrip.bin', env="conanrun")
        self.run('cmp input.bin roundtrip.bin', env="conanrun")

        # --- 6. The bug fix that motivated 1.1.1 ---------------------------
        # Upstream NEWS: 1.1.1 fixed teseq spinning forever emitting \xFF on
        # input like '\033!!\177'.  The exit must be prompt and clean.
        self.run(
            'printf "\\033!!\\177" > edge.bin',
            env="conanrun")
        self.run(f'"{teseq}" edge.bin > /dev/null', env="conanrun")
