#!/usr/bin/env python3
"""Conan recipe — libgpiod 2.0

Linux GPIO character device interaction library and tools.

Build system: autotools (configure + make).
Products:
  - Library: libgpiod.so / libgpiod.a
  - Tools: gpiodetect, gpioinfo, gpioget, gpioset, gpiomon, gpionotify

OHOS adaptations:
  - config.guess: Add HarmonyOS platform detection
  - config.sub: Add ohos-linux system type support
  - configure: Change umask 077 to 022 (HMDFS E011)
  - tools/tools-common.c: versionsort() compat for musl libc
"""
import os
import re
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgpiodConan(ConanFile):
    name = "libgpiod"
    version = "2.0"
    description = "Linux GPIO character device interaction library and tools"
    license = "LGPL-2.1"
    homepage = "https://git.kernel.org/pub/scm/libs/libgpiod/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # libgpiod is NOT a system same-name library — default dynamic (R26)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Enable CLI tools (gpiodetect, gpioinfo, gpioget, gpioset, gpiomon, gpionotify)
        tc.configure_args.append("--enable-tools")

        env = tc.environment()

        if self.settings.os == "OHOS":
            # TMPDIR: CI sandbox TMPDIR is on HMDFS and blocks writes.
            # clang conftest link step creates temp files in TMPDIR;
            # if unwritable, configure reports "C compiler cannot create
            # executables". Redirect to a writable dir inside build_folder.
            _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
            os.makedirs(_tmp_dir, exist_ok=True)
            env.define("TMPDIR", _tmp_dir)

            # LD_LIBRARY_PATH: OHOS SDK lld dynamically links libxml2.so.16
            # (stripped, no RUNPATH). Without SDK llvm/lib in search path,
            # lld cannot start -> conftest link fails.
            import glob as _glob
            _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if not os.path.isdir(_llvm_lib):
                _cands = sorted(_glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                _llvm_lib = _cands[0] if _cands else ""
            if _llvm_lib:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)

            # Strip -fstack-protector-strong: OHOS injects this into
            # CFLAGS/LDFLAGS. The trivial conftest then links against
            # __stack_chk_guard/__stack_chk_fail symbols that may be
            # missing from the target libc in the cross environment.
            _sp_re = re.compile(r'(?:^|\s)-fstack-protector(?:-\S+)?\b')
            for _var in ("CFLAGS", "LDFLAGS"):
                _val = os.environ.get(_var, "")
                if "-fstack-protector" in _val:
                    _cleaned = _sp_re.sub('', _val).strip()
                    if _cleaned:
                        env.define(_var, _cleaned)
                    else:
                        env.unset(_var)
                    self.output.info(
                        f"Stripped -fstack-protector from {_var} for conftest link")

        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)

        # Ensure TMPDIR is set via os.environ too (buildenv may not propagate
        # in all CI environments — same lesson as bogofilter/abook).
        if self.settings.os == "OHOS":
            _tmp_dir = os.path.join(self.build_folder, ".conan_tmp")
            os.makedirs(_tmp_dir, exist_ok=True)
            os.environ["TMPDIR"] = _tmp_dir

        autotools = Autotools(self)

        # Dump config.log on failure so CI surfaces the real link error
        # instead of just the generic "C compiler cannot create executables".
        try:
            autotools.configure()
        except Exception:
            config_log = os.path.join(self.build_folder, "config.log")
            if not os.path.isfile(config_log):
                config_log = os.path.join(
                    self.build_folder, "build-release", "config.log")
            if os.path.isfile(config_log):
                with open(config_log, "r", encoding="utf-8",
                           errors="ignore") as f:
                    print(f.read(), file=sys.stderr)
            raise

        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gpiod"]
