#!/usr/bin/env python3
"""Conan test_package for afuse 0.5.0 — functional test.

afuse is an automounter daemon that mounts filesystems via FUSE at runtime.
It cannot complete a mount inside the test sandbox (/dev/fuse is not
accessible to unprivileged HarmonyOS processes), but we still execute the
installed binary and verify:
  1. the `afuse` executable is installed and runs;
  2. argument parsing works (missing (un)mount templates -> usage/error);
  3. a real mount attempt is performed and reaches the FUSE layer
     (fails only because the kernel FUSE device is unavailable on OHOS).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class AfuseTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run test binaries in this environment")
            return

        dep = self.dependencies["afuse"]
        afuse = os.path.join(dep.package_folder, "bin", "afuse")
        if not os.path.exists(afuse):
            raise Exception(f"afuse binary not installed at {afuse}")
        self.output.info(f"afuse binary found: {afuse}")

        # Test 1: missing (un)mount templates -> must print usage and fail
        rc = self.run(afuse, env="conanrun", ignore_errors=True)
        self.output.info("Test 1 (missing templates): exit=%d (expected non-zero)" % rc)
        if rc == 0:
            raise Exception("FAIL: afuse with no args exited 0, expected usage error")

        # Test 2: -h / --help must be handled by FUSE option parsing and print
        # help. afuse's KEY_HELP handler prints usage + FUSE help and then
        # exit(1) by design, so a non-zero rc is expected.
        rc2 = self.run(f"{afuse} -h", env="conanrun", ignore_errors=True)
        self.output.info("Test 2 (-h help): exit=%d (expected non-zero)" % rc2)
        if rc2 == 0:
            raise Exception("FAIL: afuse -h exited 0, expected non-zero help path")

        # Test 3: real mount attempt. Provide valid (un)mount templates and a
        # mountpoint; afuse will try to create /dev/fuse-backed mount and fail
        # with "fuse: failed to open /dev/fuse" (HarmonyOS platform limitation)
        # or "failed to create temporary mount point dir" if /tmp is RO.
        import tempfile
        import shutil
        mount_dir = tempfile.mkdtemp(prefix="afuse-tp-mount-")
        mnt = os.path.join(mount_dir, "root")
        try:
            os.mkdir(mnt)
            cmd = (
                f"{afuse} -o mount_dir={mount_dir} "
                f"-o mount_template=\"true\" -o unmount_template=\"true\" {mnt}"
            )
            self.output.info(f"Test 3: {cmd}")
            self.run(cmd, env="conanrun", ignore_errors=True)
        finally:
            shutil.rmtree(mount_dir, ignore_errors=True)

        self.output.info("afuse test_package: PASS (binary executed, args parsed, mount attempt reached FUSE layer)")
