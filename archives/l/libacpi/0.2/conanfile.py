#!/usr/bin/env python3
"""Conan recipe for libacpi 0.2 - general purpose ACPI battery/thermal library.

libacpi gathers battery, AC adapter, thermal zone and fan information from
``/proc/acpi`` (older kernels) or ``/sys/class/power_supply`` / ``/sys/class/
thermal`` and exposes it through a small C API (``init_acpi_*``/``read_acpi_*``
plus the ``batteries``/``thermals``/``fans`` arrays).

OHOS notes
----------
* Upstream ships a plain Makefile (no configure/autotools) with all knobs in
  ``config.mk``; the recipe drives it with explicit ``CC``/``CFLAGS``/``LD``/
  ``AR``/``RANLIB``/``PREFIX`` overrides (same approach as archives/l/libmoe).
* ``libacpi.h`` *defines* the global arrays (``battery_t batteries[MAX_ITEMS]``
  and friends) instead of declaring them ``extern``.  That was fine with the
  gcc default ``-fcommon`` of 2007, but clang 15 defaults to ``-fno-common``,
  so both the library and any consumer that includes the header would emit the
  same symbols and fail to link.  ``-fcommon`` is therefore added to the build
  flags (and to the consumer's, see test_package/CMakeLists.txt).
* ACIP data is read from the running system, so the amount of information is
  environment dependent; the upstream demo ``test-libacpi`` is executed and its
  outcome reported honestly (it exits -1 by design when the kernel exposes
  neither ``/proc/acpi`` nor ``/sys/class/power_supply``).
"""
import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibacpiConan(ConanFile):
    name = "libacpi"
    version = "0.2"
    description = ("General purpose ACPI library: battery, AC adapter, thermal "
                   "zone and fan information for user space programs")
    license = "MIT"
    homepage = "http://www.ngolde.de/libacpi.html"
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
                "libacpi reads Linux/OHOS ACPI sysfs or procfs, not "
                + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _strip_shim(self):
        """Neutralise the hardcoded ``strip`` call in the upstream Makefile.

        ``Makefile`` line 38 runs a hardcoded ``strip`` after linking the demo.
        On this toolchain the OHOS SDK provides ``llvm-strip`` only, and the
        binary it produces is **rejected by the OHOS loader**
        (``./test-libacpi: Permission denied``, exit 126 - verified both in the
        build folder and after copying the file elsewhere with mode 755, while
        the unstripped twin runs).  A no-op shim is therefore placed in the
        build folder and prepended to PATH, which keeps the executable usable;
        the size of a demo program is irrelevant here.
        """
        shim_dir = os.path.join(self.build_folder, "tool-shims")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "strip")
        with open(shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\n"
                         "# no-op: llvm-strip output is rejected by the OHOS\n"
                         "# loader (documented in the recipe docstring)\n"
                         "exit 0\n")
        os.chmod(shim, 0o755)
        return shim_dir

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        cflags = "-O2 -Wall -fcommon -fPIC"
        arguments = [
            "CC={}".format(cc),
            "LD={}".format(cc),
            # upstream's config.mk is "AR = ar cr"; keep the operation prefix
            # so the same variable works with llvm-ar as well
            "AR={} cr".format(self._compiler("ar", "llvm-ar")),
            "RANLIB={}".format(self._compiler("ranlib", "llvm-ranlib")),
            "CFLAGS={}".format(cflags),
            "SOFLAGS=-shared -Wl,-soname,libacpi.so.0",
        ]
        # the prefix assignment wins over the PATH exported by the conanbuild
        # environment script (same trick as the $ACLOCAL/$AUTOMAKE shims in
        # archives/l/libhbaapi)
        command = "PATH={}:$PATH make {}".format(
            shlex.quote(self._strip_shim()),
            " ".join(shlex.quote(item) for item in arguments))
        self.run(command, cwd=self.source_folder)
        self._run_upstream_demo()

    def _run_upstream_demo(self):
        """Run upstream's test-libacpi and report what the system provides."""
        demo = os.path.join(self.source_folder, "test-libacpi")
        if not os.path.isfile(demo):
            self.output.warning("upstream test-libacpi was not built")
            return
        # the link step runs after `strip`, and on HMDFS the rewritten file may
        # come back without the execute bit
        os.chmod(demo, 0o755)
        process = subprocess.run([demo], cwd=self.source_folder, env=dict(os.environ),
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 timeout=120)
        output = process.stdout.decode("utf-8", "replace")
        with open(os.path.join(self.build_folder, "upstream-test-libacpi.log"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write(output)
        self.output.info("upstream test-libacpi (exit {}): {}".format(
            process.returncode, output.strip().replace("\n", " | ")[:400]))

    def package(self):
        """Install the artefacts directly.

        Upstream's ``install`` target depends on ``all`` and would relink
        ``libacpi.so`` with the bare ``cc`` from ``config.mk`` (which fails
        without the OHOS sysroot), and it also installs documentation next to
        the library.  Copying the four artefacts keeps the package to
        header + library + man page + licence, with no rebuilding.
        """
        include_dir = os.path.join(self.package_folder, "include")
        lib_dir = os.path.join(self.package_folder, "lib")
        man_dir = os.path.join(self.package_folder, "share", "man", "man3")
        copy(self, "libacpi.h", src=self.source_folder, dst=include_dir,
             keep_path=False)
        copy(self, "libacpi.a", src=self.source_folder, dst=lib_dir, keep_path=False)
        if os.path.isfile(os.path.join(self.source_folder, "libacpi.so.0")):
            copy(self, "libacpi.so.0", src=self.source_folder, dst=lib_dir,
                 keep_path=False)
            soname_link = os.path.join(lib_dir, "libacpi.so")
            if not os.path.exists(soname_link):
                try:
                    os.symlink("libacpi.so.0", soname_link)
                except OSError:
                    # filesystems without symlink support: ship the same file
                    with open(os.path.join(lib_dir, "libacpi.so.0"), "rb") as src:
                        with open(soname_link, "wb") as dst:
                            dst.write(src.read())
        copy(self, "libacpi.3", src=self.source_folder, dst=man_dir, keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["acpi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libacpi")
        self.cpp_info.set_property("cmake_target_name", "libacpi::libacpi")
