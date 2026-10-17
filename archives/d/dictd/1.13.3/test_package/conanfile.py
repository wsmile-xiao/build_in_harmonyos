import hashlib
import os
import shutil

from conan import ConanFile


class DictdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    # Smoke test for the dictd package (no sockets, no daemon); the actual
    # assertions live in test.sh: dict/dictd --version, a dictzip ->
    # dictunzip round-trip with byte comparison, and a dictfmt-built
    # dictionary answered by dictd through the upstream-supported
    # `--stdin2stdout` pipe mode.

    _ohos_data_root = "/data/storage/el2/base"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        if self.settings.os == "OHOS":
            # HMDFS cannot serve bash's getcwd() (EACCES walking the parent
            # dirs), so the test must not run with an HMDFS cwd, and bash must
            # not start with a stale PWD either (its startup then calls
            # getcwd() and dies).  Copy test.sh to a tmpfs workdir under
            # /data/storage/el2/base (same approach as the dictd recipe
            # build()), then `export PWD=<workdir>` before entering it: bash
            # sees PWD already matching its cwd, skips getcwd entirely and
            # runs the script.
            key = hashlib.sha256(
                os.path.abspath(self.source_folder).encode("utf-8")
            ).hexdigest()[:12]
            work = os.path.join(
                self._ohos_data_root, f".conan-test-dictd-{key}"
            )
            if os.path.isdir(work):
                shutil.rmtree(work)
            os.makedirs(work)
            script = "test.sh"
            for folder in (self.build_folder, self.source_folder):
                candidate = os.path.join(folder or "", script)
                if folder and os.path.isfile(candidate):
                    shutil.copy2(candidate, os.path.join(work, script))
                    break
            else:
                raise FileNotFoundError(f"{script} not found in test package")
            self.run(
                f"export PWD='{work}' && cd '{work}' && {config_shell} {script}",
                env="conanrun",
            )
        else:
            self.run(
                f"cd '{self.build_folder}' && {config_shell} test.sh",
                env="conanrun",
            )
