import io
import os

from conan import ConanFile


class UtalkTestConan(ConanFile):
    """test_package for utalk (executable package).

    R34/PF3: test() actually EXECUTES the packaged `utalk` binary through
    test.sh (which also asserts on its behavior), it is not a print-only shell.
    """
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        utalk = None
        for dependency in self.dependencies.host.values():
            if dependency.ref.name == "utalk":
                bindirs = dependency.cpp_info.bindirs or ["bin"]
                bindir = bindirs[0]
                if not os.path.isabs(bindir):
                    bindir = os.path.join(dependency.package_folder, bindir)
                utalk = os.path.join(bindir, "utalk")
        if not utalk or not os.path.isfile(utalk):
            raise Exception("utalk binary not found in package bindirs")

        # OHOS has no /bin/bash; use the HNP bash or fall back to /bin/sh.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        if not os.path.isfile(bash):
            bash = "/bin/sh"
        script = os.path.join(self.recipe_folder, "test.sh")
        # Capture output through a pipe (Conan uses subprocess.PIPE when given a
        # StringIO): keeps the full output visible and avoids the toolchain
        # silent-exit seen on some OHOS devices when stdout/stderr is inherited
        # through a deep python->sh chain (same note as the main recipe).
        buf = io.StringIO()
        cmd = '%s "%s" "%s"' % (bash, script, utalk)
        try:
            self.run(cmd, env="conanrun", stdout=buf, stderr=buf)
        except Exception:
            self.output.error("---- utalk test log (FAILED) ----\n" + buf.getvalue())
            raise
        self.output.info("---- utalk test log ----\n" + buf.getvalue())
