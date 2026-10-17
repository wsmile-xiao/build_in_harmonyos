import os
import shlex

from conan import ConanFile


class RunawkTestConan(ConanFile):
    """Consumer test for the runawk executable package."""

    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Build an explicit run environment by inlining the variables into the
        # command instead of activating the generated conanrun.sh: on this
        # sandbox conan's deactivate hook shells out to the broken Electron
        # "safe-bin" shims (dangling /bin/bash interpreter), which aborts the
        # test phase with "Error 126" even though every assertion already
        # passed.  We seed PATH/AWKPATH directly and drop the safe-bin directory
        # so the consumer script uses a working `rm`.
        tested = self.dependencies[self.tested_reference_str]
        mawk = self.dependencies["mawk"]
        bindirs = list(tested.cpp_info.bindirs) + list(mawk.cpp_info.bindirs)

        ambient = os.environ.get("PATH", "/usr/bin:/bin")
        clean = os.pathsep.join(p for p in ambient.split(os.pathsep)
                                if p and "safe-bin" not in p)
        awkpath = os.path.join(tested.package_folder, "share", "runawk")
        path = os.pathsep.join(bindirs + [clean])

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        cmd = (f"export PATH={shlex.quote(path)}; "
               f"export AWKPATH={shlex.quote(awkpath)}; "
               f"export LC_ALL=C; "
               f"{bash} test.sh")
        self.run(cmd)
