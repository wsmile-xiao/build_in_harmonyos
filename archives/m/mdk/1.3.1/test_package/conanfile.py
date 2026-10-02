import json
import os
import shutil

from conan import ConanFile


class MdkTestConan(ConanFile):
    """test_package for mdk 1.3.1 - executable verification.

    mdk installs only the mixasm/mixvm binaries (libmix.a is a noinst
    convenience library upstream never installs), so there is no public
    library API to link against.  Instead we verify real binary behaviour:
      - `mixasm --help` prints usage, exits 0
      - `mixvm --help`  prints usage, exits 0
      - `mixasm` assembles the vendored hello.mixal fixture (taken from the
        upstream samples/hello.mixal) into a non-empty .mix object file
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Prefer the HMBS-guaranteed /bin/sh; never use the repo-profile
        # /data/service/hnp/bin/bash when it is the poisoned inaccessible
        # path (configure[139] "inaccessible or not found", Error 127;
        # bwm/0.6.3 + libtiger/0.3.4 precedent). test.sh is POSIX sh.
        def _usable_shell():
            if os.path.isfile("/bin/sh"):
                return "/bin/sh"
            w = shutil.which("sh")
            if w and os.path.isfile(w):
                return w
            for cand in (os.environ.get("SHELL", ""),
                         os.environ.get("CONFIG_SHELL", "")):
                if not cand:
                    continue
                if "hnp/bin/bash" in cand.split()[0]:
                    continue
                if os.path.isfile(cand.split()[0]):
                    return cand
            return "sh"
        bash = _usable_shell()
        command = "{} test.sh".format(bash)
        # hmbs hard gate: the marker must carry the real test_package counts
        # (3 executable checks in test.sh, per MANIFEST.yml).
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 3, "passedCount": 0}
        try:
            self.run(command, env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = 3
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result, ensure_ascii=False))
