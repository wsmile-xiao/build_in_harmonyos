#!/usr/bin/env python3
"""Conan recipe for libpwm 1.0-rc2 - drive Linux PWM devices from userspace.

libpwm wraps the PWM character device ABI (/dev/pwmchipN) and the sysfs ABI
(/sys/class/pwm) behind one API: open a chip, get a PWM line, round/get/set a
waveform (period, duty length, duty offset).  It also ships the pwmset,
pwmround and pwmtestperf example programs.

OHOS notes
----------
* Upstream ships a **pre-generated** autotools build (``configure`` from
  autoconf 2.72, ``Makefile.in``, libtool macros in ``m4/``), so the recipe
  never runs autoreconf - the same situation as archives/l/libirman.
* ``configure`` contains ``umask 077 && mktemp -d`` (E011): on HMDFS the
  resulting directory cannot be used by config.status, so build() relaxes it to
  ``umask 022`` in place.
* ``config.guess`` cannot probe HMDFS (E007), so the triplet is passed with
  ``--build``/``--host``; the bundled config.sub (GNU config 2024) is taught
  ``linux-ohos`` by a two hunk patch when it does not accept the triplet.
* The three example programs are executed with ``--help``/without arguments as
  upstream evidence; there is no PWM chip in the sandbox, so waveform work is
  reported as an environment limitation.
"""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibpwmConan(ConanFile):
    name = "libpwm"
    version = "1.0"
    description = ("Userspace library to drive Linux PWM devices: chip open, "
                   "waveform round/get/set over the character device or sysfs ABI")
    license = "LGPL-2.1-only"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/ukleinek/libpwm.git"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libpwm drives Linux/OHOS PWM devices, not " + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        arch = str(self.settings.arch)
        cpu = "aarch64" if arch in ("armv8", "aarch64") else arch
        triplet = "{}-unknown-linux-ohos".format(cpu)
        toolchain.configure_args.extend([
            "--build={}".format(triplet),
            "--host={}".format(triplet),
        ])
        toolchain.generate()

    def _relax_configure_umask(self):
        """E011: HMDFS cannot use the 0700 directory config.status creates."""
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8", errors="surrogateescape") as handle:
            content = handle.read()
        if "umask 077" in content:
            with open(configure, "w", encoding="utf-8",
                      errors="surrogateescape") as handle:
                handle.write(content.replace("umask 077", "umask 022"))

    def build(self):
        apply_conandata_patches(self)
        self._relax_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_programs()

    def _run_upstream_programs(self):
        """Run the example programs; no PWM chip exists in the sandbox."""
        if str(self.settings.os) != "OHOS":
            return
        log = os.path.join(self.build_folder, "upstream-programs.log")
        results = []
        for program, args in (("pwmround", []), ("pwmset", []), ("pwmtestperf", [])):
            binary = os.path.join(self.build_folder, program)
            if not os.path.isfile(binary):
                continue
            process = subprocess.run([binary] + args, cwd=self.build_folder,
                                     env=dict(os.environ), stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, timeout=60)
            output = process.stdout.decode("utf-8", "replace").strip()
            results.append("===== {} (exit {})\n{}".format(
                program, process.returncode, output[:1500]))
        with open(log, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n\n".join(results))
        self.output.info("upstream programs: " + " | ".join(
            line for line in "\n".join(results).splitlines() if "exit" in line))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        import glob
        for archive in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(archive)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["pwm"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libpwm")
        self.cpp_info.set_property("cmake_target_name", "libpwm::libpwm")
        self.cpp_info.set_property("pkg_config_name", "libpwm")
