import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class NtopngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The ntopng daemon opens ports/interfaces and needs a data dir; a full
        # run requires root + live interfaces. Minimal smoke = version banner
        # (aligns with upstream `make test` -> test_version target).
        # The binary links libc++_shared.so from the OHOS system image; the
        # conanrun env only carries the recipe-level deps, so surface
        # /system/lib64 (and every dependency lib dir) explicitly. Same
        # pattern as the kgoldrunner 26.04.0 / audiocd 26.04.3 tests.
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib):
                    env.prepend_path("LD_LIBRARY_PATH", lib)
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            self.run("sh test_version.sh", env="conanrun")
