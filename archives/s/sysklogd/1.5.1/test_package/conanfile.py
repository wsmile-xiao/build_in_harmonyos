import os
import shutil

from conan import ConanFile

# Absolute fallback for the C compiler: the OHOS clang does not sit on the
# default PATH for every invocation mode (see also the profile
# ci/conan/profiles/ohos-aarch64 tools.build:compiler_executables entry).
_CLANG_FALLBACK = "/data/service/hnp/bin/clang"


# The end-to-end check binds an AF_UNIX SOCK_DGRAM socket, so its scratch tree
# has to sit on a filesystem whose driver lets bind(2) through.  Measured on
# the device with a two-line probe (socket/bind/chmod):
#   /storage/Users/currentUser/... (HMDFS)  -> bind: Operation not permitted
#   /data/storage/el2/base (per-app tmpfs)  -> bind ok, chmod(0666) ok
#   /dev/shm                                -> bind: Permission denied
# Putting the scratch tree on tmpfs is the same conclusion archives/a/acpid
# reaches in _choose_build_root() for its build tree.  If tmpfs is somehow not
# there, fall back to the Conan build folder: the round trip then fails loudly
# instead of being skipped, which is the honest outcome.
_TMPFS_SCRATCH = "/data/storage/el2/base"


def _scratch_dir(build_folder):
    if os.path.isdir(_TMPFS_SCRATCH) and os.access(_TMPFS_SCRATCH, os.W_OK | os.X_OK):
        return os.path.join(_TMPFS_SCRATCH, "sysklogd-test-%d" % os.getpid())
    return os.path.join(build_folder, "sysklogd-test-work")


class SysklogdTestConan(ConanFile):
    """test_package for sysklogd 1.5.1.

    sysklogd installs two *daemons* and no library, so there is no API to
    link against.  The consumer surface this package actually publishes is
      * the documented command line of syslogd(8) / klogd(8), and
      * the AF_UNIX SOCK_DGRAM log socket syslogd serves.
    test_runner.sh therefore compiles test_consumer.c (a real consumer
    program, not a file existence probe), drives a live syslogd on a private
    socket, and asserts the record comes back out of the configured log file.
    The klogd kernel-log read needs CAP_SYSLOG and is reported honestly as a
    skip when the test user lacks it.
    """

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "clang"
        if not shutil.which(cc) and os.path.isfile(_CLANG_FALLBACK):
            cc = _CLANG_FALLBACK
        return cc

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        sbin = os.path.join(dep.package_folder, "sbin")
        work = _scratch_dir(self.build_folder)
        script = os.path.join(self.recipe_folder, "test_runner.sh")

        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries, so drive the
        # checks through bash (same workaround as archives/a/acpid/2.0.34).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # Non-zero exit from the assertion driver raises here and fails the
        # test -- the assertions, not the harness, decide the verdict.
        self.run(
            f'"{bash}" "{script}" "{sbin}" "{self._cc()}" "{work}"',
            env="conanrun",
        )
