#!/usr/bin/env python3
"""Conan recipe for input-utils 1.3 (kraxel input tools).

Userspace utilities for the Linux input subsystem: lsinput, input-events,
input-kbd, input-send, input-recv and emulate-key.  Pure GNUmakefile build,
no library artifact — installs command line tools plus generated lircd.conf.
"""
import os
import shutil
import subprocess

from conan.tools.env import Environment

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

required_tools = ["lsinput", "input-events", "input-kbd", "input-send",
                  "input-recv", "emulate-key"]


class InputUtilsConan(ConanFile):
    name = "input-utils"
    version = "1.3"
    description = "kraxel input utilities: lsinput, input-events, input-kbd, input-send/recv, emulate-key"
    license = "GPL-2.0-only"
    homepage = "https://www.kraxel.org/releases/input/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # no options: tools-only package, nothing to toggle

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform allow-list must include OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"input-utils supports Linux and OHOS, not {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compilers come from the Conan toolchain env, never bare ${CC}
        # R9: -j1, never -j$(nproc)
        # name.sh/lirc.sh read /usr/include/linux/*.h by default; on OHOS
        # point them at the SDK sysroot uapi headers via their env hooks.
        # Pure env-var contract: the sysroot is supplied only via
        # OHOS_SDK_SYSROOT (or OHOS_SDK_NATIVE), never via profile [conf]
        # user.ohos:sysroot, so this recipe carries no profile dependency
        # and no hardcoded device-private paths.
        sysroot = os.environ.get("OHOS_SDK_SYSROOT", "")
        if not sysroot:
            # Probe the OHOS SDK sysroot next to the toolchain (layout used
            # on HarmonyOS PC devices: <sdk>/native/sysroot/usr/include).
            sdk_root = os.environ.get("OHOS_SDK_NATIVE", "")
            if sdk_root and os.path.isdir(
                    os.path.join(sdk_root, "sysroot", "usr", "include")):
                sysroot = os.path.join(sdk_root, "sysroot")
        if not sysroot:
            # Third-level fallback: official CI environments do not export
            # OHOS_SDK_SYSROOT / OHOS_SDK_NATIVE, so ask the compiler that
            # the profile declares.  Query the whole conf key (not a :c
            # subkey, which may not exist) and never fail if the toolchain
            # did not declare compiler executables.
            compilers = self.conf.get("tools.build:compiler_executables")
            cc = compilers.get("c", "") if isinstance(compilers, dict) else ""
            if not cc:
                cc = shutil.which("clang") or shutil.which("cc") or ""
            if cc:
                probe = self._probe_sysroot_via_cc(cc)
                if probe:
                    sysroot = probe
                    self.output.info(
                        f"OHOS sysroot auto-detected via {cc}: {sysroot}")
                else:
                    self.output.info(
                        f"OHOS_SDK_SYSROOT unset and sysroot probe via "
                        f"{cc} failed; relying on name.sh upstream "
                        "default lookup")
            else:
                self.output.info(
                    "OHOS_SDK_SYSROOT unset and no compiler found; "
                    "relying on name.sh upstream default lookup")
        # No hardcoded device-private paths: the recipe is self-contained
        # and only consumes OHOS_SDK_SYSROOT / OHOS_SDK_NATIVE supplied by
        # the profile [buildenv] or the invoking shell, or a sysroot
        # reported by the profile compiler itself.
        codes = os.path.join(
            sysroot, "usr", "include", "linux", "input-event-codes.h") if sysroot else ""
        env = {}
        if sysroot and codes and os.path.isfile(codes):
            env["OHOS_INPUT_CODES"] = codes
            bus = os.path.join(sysroot, "usr", "include", "linux",
                               "input.h")
            if os.path.isfile(bus):
                env["OHOS_INPUT_BUS_CODES"] = bus
        elif sysroot:
            self.output.info(
                f"sysroot {sysroot} lacks linux/input-event-codes.h; "
                "relying on name.sh upstream default lookup")

        build_env = Environment()
        for key, value in env.items():
            build_env.define(key, value)
        with build_env.vars(self).apply():
            self.run("make -j1", cwd=self.source_folder)

    @staticmethod
    def _probe_sysroot_via_cc(cc):
        """Ask the compiler for its sysroot; returns "" if undetectable.

        Preferred: `<cc> -print-sysroot`.  clang < 16 lacks that flag, so
        fall back to deriving the sysroot from the compiler's resource
        include directory (`<cc> -print-file-name=include` walks up the
        tree to a sibling `sysroot` whose uapi headers this build actually
        consumes).  No hardcoded paths anywhere.
        """
        try:
            r = subprocess.run([cc, "-print-sysroot"], capture_output=True,
                               text=True, timeout=60)
            cand = r.stdout.strip()
            if r.returncode == 0 and cand and os.path.isdir(cand):
                return cand
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            r = subprocess.run([cc, "-print-file-name=include"],
                               capture_output=True, text=True, timeout=60)
            inc = r.stdout.strip()
            if r.returncode != 0 or not inc or not os.path.isdir(inc):
                return ""
            d = os.path.dirname(os.path.abspath(inc))
            for _ in range(8):
                cand = os.path.join(d, "sysroot")
                if os.path.isfile(os.path.join(
                        cand, "usr", "include", "linux",
                        "input-event-codes.h")):
                    return cand
                parent = os.path.dirname(d)
                if parent == d:
                    return ""
                d = parent
        except (OSError, subprocess.SubprocessError):
            return ""
        return ""

    def package(self):
        # Upstream install uses install(1) which is absent on OHOS devices;
        # package the same file set with Conan copy() instead (R33-adjacent:
        # no host tool assumptions in packaging).
        src = self.source_folder
        copy(self, "lsinput", src, os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "input-events", src,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "input-kbd", src, os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "input-send", src, os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "input-recv", src, os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "emulate-key", src,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "lircd.conf", src,
             os.path.join(self.package_folder, "share", "input-utils"),
             keep_path=False)
        copy(self, "*.man", os.path.join(src),
             os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)
        copy(self, "COPYING", src,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # R38: shipped executables declared via software-level commands.json
