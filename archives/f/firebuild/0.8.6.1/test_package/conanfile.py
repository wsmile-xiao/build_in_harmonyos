import os
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["firebuild"]
        cpp = dep.cpp_info
        bindir = cpp.bindirs[0] if cpp.bindirs else os.path.join(dep.package_folder, "bin")
        firebuild_bin = os.path.join(bindir, "firebuild")
        libdir = cpp.libdirs[0] if cpp.libdirs else os.path.join(dep.package_folder, "lib")
        so = os.path.join(libdir, "libfirebuild.so")
        cc = os.environ.get("CC", "clang")
        # The shell used by test.c's execl() for running firebuild --version.
        # Defaults to the OHOS system shell; overridable via CONFIG_SHELL.
        test_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Do NOT link -lfirebuild: loading libfirebuild.so triggers the
        # interceptor constructor which segfaults without a supervisor.
        # The test uses fork+exec on the firebuild binary instead.
        self.run(
            f"{cc} -std=gnu99 test.c -o test_probe"
            f" -DTARGET_SO='\"{so}\"'"
            f" -DTARGET_BIN='\"{firebuild_bin}\"'"
            f" -DTEST_SHELL='\"{test_shell}\"'"
            f" -ldl"
        )
        # Sign the test binary so the OHOS kernel allows execution
        self.run(
            "/data/service/hnp/bin/llvm-objcopy"
            " --remove-section .codesign test_probe 2>/dev/null || true"
        )
        self.run(
            "/data/service/hnp/bin/binary-sign-tool sign"
            " -inFile test_probe -outFile test_probe -selfSign 1"
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile + link only")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c ./test_probe", env="conanrun")
