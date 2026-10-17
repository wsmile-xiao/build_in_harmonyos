import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class ErofsUtilsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_utility(self, package_folder, name):
        """Locate an EROFS utility in bin/ or sbin/."""
        for bindir in ("bin", "sbin"):
            candidate = os.path.join(package_folder, bindir, name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def test(self):
        if not can_run(self):
            return

        package_folder = self.dependencies["erofs-utils"].package_folder

        # --- Functional integration test: mkfs → fsck ---
        # The package's configure disables many features (--disable-ublk
        # --disable-s3 --disable-oci etc.), so dump.erofs/mount.erofs may not
        # be built. Only the two core binaries mkfs.erofs and fsck.erofs are
        # guaranteed to exist.
        mkfs = self._find_utility(package_folder, "mkfs.erofs")
        fsck = self._find_utility(package_folder, "fsck.erofs")
        if not mkfs:
            raise AssertionError("mkfs.erofs not found in package bin/ or sbin/")
        if not fsck:
            raise AssertionError("fsck.erofs not found in package bin/ or sbin/")

        tmpdir = tempfile.mkdtemp(prefix="erofs-test-")
        try:
            # Create a small test directory with a file in it.
            srcdir = os.path.join(tmpdir, "src")
            os.makedirs(os.path.join(srcdir, "subdir", "deep"))
            with open(os.path.join(srcdir, "hello.txt"), "w") as f:
                f.write("Hello EROFS!\n")
            with open(os.path.join(srcdir, "subdir", "another.txt"), "w") as f:
                f.write("Nested file.\n")
            with open(os.path.join(srcdir, "subdir", "deep", "nested.txt"), "w") as f:
                f.write("Deeply nested.\n")

            image = os.path.join(tmpdir, "test.erofs")

            # mkfs.erofs: create an EROFS image from the source directory.
            # -x-1 disables xattrs (OHOS has no selinux/xattr support).
            self.run(
                f'"{mkfs}" -d2 -x-1 "{image}" "{srcdir}"',
                env="conanrun",
            )
            if not os.path.isfile(image):
                raise AssertionError("mkfs.erofs did not produce an image file")

            # fsck.erofs: verify the image integrity (exit 0 = no errors).
            # self.run raises ConanException on non-zero exit, so reaching here
            # means fsck succeeded.
            self.run(
                f'"{fsck}" "{image}"',
                env="conanrun",
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
