#!/usr/bin/env python3

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class OfhttpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualBuildEnv/VirtualRunEnv: the CI test stage does not inherit the
    # profile's [buildenv], so the platform tool directory
    # (/data/service/hnp/bin) would be missing from PATH here.
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder

        # The deliverable of this recipe is the ofhttp executable, so resolve the
        # whole package folder from the dependency instead of hard-coding paths.
        # That is also what makes the gate's destructive reverse check (L1e,
        # which moves the package's bin/ away) able to prove the test really
        # consumes the packaged artifact. Every assertion lives in
        # test_ofhttp.py so there is a single source of truth; this recipe only
        # decides whether the runtime half may run at all.
        assert os.path.isdir(package_folder), f"package folder not found: {package_folder}"

        driver = os.path.join(self.recipe_folder, "test_ofhttp.py")
        # can_run() is false when the build host cannot execute the target (e.g.
        # cross-building OHOS from x86_64). The driver then verifies the
        # packaged artifacts and says so explicitly instead of claiming a
        # runtime pass it never performed.
        can_execute = can_run(self)
        self.output.info("can_run=%s; runtime checks %s"
                         % (can_execute, "enabled" if can_execute else "skipped"))

        env = ["conanrun", "conanbuild"]
        self.run(f'"{sys.executable}" "{driver}" "{package_folder}" --self-test', env=env)
        # --no-run instead of an env var: self.run(env=...) takes *environment
        # script names*, not KEY=VALUE, so a "KEY=VALUE" entry there is silently
        # ignored and the runtime half would run (and fail) anyway.
        tail = "" if can_execute else " --no-run"
        self.run(f'"{sys.executable}" "{driver}" "{package_folder}"{tail}', env=env)
