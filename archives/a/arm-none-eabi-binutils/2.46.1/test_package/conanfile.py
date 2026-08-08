import os
import shutil

from conan import ConanFile


class ArmnoneeabibinutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Resolve the shell to run the smoke tests. Prefer CONFIG_SHELL if set,
        # then a bash/sh discoverable on PATH. Never fall back to a
        # machine-specific absolute path; fail explicitly if no shell exists.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or shutil.which("sh")
        if not bash:
            raise RuntimeError(
                "No usable shell found: CONFIG_SHELL is unset and neither "
                "'bash' nor 'sh' is discoverable on PATH."
            )
        # Smoke test: verify core tools exist and report version.
        # R34: the test MUST genuinely depend on the tested package, so the
        # tools are executed via their absolute path inside the package's own
        # bin/ directory. Resolving bare command names from PATH is not enough:
        # a system-wide copy of the same tools (e.g. preinstalled cross
        # toolchains) would let the test pass even if the package artifacts are
        # missing, which the CI L1e destructive negative test detects as a
        # fake test. Fail explicitly when the package bin/ or any tool is
        # absent.
        pkg = self.dependencies["arm-none-eabi-binutils"]
        bindir = os.path.join(pkg.package_folder, "bin")
        if not os.path.isdir(bindir):
            raise RuntimeError(
                "B20-FIX: package bin/ directory missing: %s" % bindir
            )
        tools = ["arm-none-eabi-objdump", "arm-none-eabi-objcopy",
                  "arm-none-eabi-ld", "arm-none-eabi-as",
                  "arm-none-eabi-ar", "arm-none-eabi-nm",
                  "arm-none-eabi-strip", "arm-none-eabi-size"]
        for tool in tools:
            exe = os.path.join(bindir, tool)
            if not os.path.isfile(exe):
                raise RuntimeError(
                    "B20-FIX: %s missing from package bin/: %s" % (tool, exe)
                )
            self.run(f"{bash} -c '{exe} --version'", env="conanrun")
