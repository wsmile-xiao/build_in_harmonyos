#!/usr/bin/env python3
"""Conan test_package for usbmuxd 1.0.8 (daemon-type tool package).

usbmuxd is a daemon: the deliverables are the sbin/usbmuxd daemon binary
and the bin/iproxy port-forwarding tool. Upstream 1.0.8 registers no test
suite (N=0: no tests/ directory, no add_test(), no make check target in
the 2012-era CMake build). Consumer verification (kfourinline #11104
pattern for tool-type packages):

  1. usbmuxd -h prints its usage banner and exits 0 (ELF load + getopt
     parsing + libc/printf all exercised before any socket/USB work)
  2. iproxy with no args prints its LOCAL_TCP_PORT DEVICE_TCP_PORT usage
     line and exits 0 (proves the libusbmuxd-2.0 client library link and
     the in-tree sock_stuff helpers)
  3. consumer C program links libusbmuxd and asserts the client-API
     error paths: without a running usbmuxd daemon, get_device_list()
     and connect() return negative error codes (no crash), and
     device_list_free(NULL) is safe (libusbmuxd 2.0.2 test_package
     precedent for the API-level assertions)

Runtime environment: the daemon links libusb-1.0.so.0 from the libusb
package (LD_LIBRARY_PATH via VirtualRunEnv + libusb dependency declared
here so the run env collects it).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class UsbmuxdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # the usbmuxd daemon DT_NEEDED libusb-1.0.so.0 (libusb package);
        # declare it so VirtualRunEnv collects its libdir into the run env
        self.requires("libusb/1.0.27")
        # the consumer program links libusbmuxd directly
        self.requires("libusbmuxd/2.0.2")
        self.requires("libplist/2.7.0", override=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("cannot run on this host, skipping execution")
            return
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg = self.dependencies["usbmuxd"]
        daemon = os.path.join(pkg.package_folder, "sbin", "usbmuxd")
        iproxy = os.path.join(pkg.package_folder, "bin", "iproxy")
        if not os.path.isfile(daemon):
            raise ConanException(f"usbmuxd daemon not found: {daemon}")
        if not os.path.isfile(iproxy):
            raise ConanException(f"iproxy tool not found: {iproxy}")
        testprog = os.path.join(
            self.cpp.build.bindirs[0], "usbmuxd_consumer_test")

        # OHOS: freshly built executables need a refreshed .codesign
        # section to be executable (kfourinline 26.04.0 precedent)
        if str(self.settings.os) == "OHOS":
            self._sign(daemon)
            self._sign(iproxy)

        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        script = os.path.join(self.source_folder, "test.sh")
        env = Environment()
        env.define("TESTPROG_OUT", os.path.join(self.build_folder, "t.out"))
        # R34: test() must actually run the packaged binaries
        self.run(
            f'{shlex.quote(shell)} {shlex.quote(script)} '
            f'{shlex.quote(daemon)} {shlex.quote(iproxy)} '
            f'{shlex.quote(testprog)}',
            cwd=self.build_folder, env="conanrun")
        self.output.info("usbmuxd runtime smoke passed")

    def _sign(self, path):
        import subprocess
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=True)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                        "-selfSign", "1"], check=True)
