#!/usr/bin/env python3
"""Conan recipe for mbr 1.2.2 (replacement Master Boot Record) — HarmonyOS PC.

mbr is a Debian-native package: the historic author page
(chiark.greenend.org.uk/~neilt/mbr) is stale and the maintained source lives in
the Debian pool, which is what this recipe consumes.

The upstream build is unusual. The MBR itself is 8086 assembly (as86 dialect);
it is assembled into a raw 512-byte image, converted into a C array with
`xxd -i` and linked into the aarch64 host program `install-mbr`. Two
build-machine tools are therefore needed while compiling and both are pulled in
with tool_requires so the build is self-contained:

  * as86 / ld86  -> dev86/0.16.21
  * xxd          -> xxd/9.1.0

patches/0001 rewrites the intermediate-file suffix of the preprocessor rule
(.s86 -> .i86). Upstream assumes `.S86` and `.s86` are two distinct files, which
is false on case-insensitive filesystems (HMDFS on HarmonyOS PC): make's
existence check on the intermediate `mbr.s86` is satisfied by the source file
`mbr.S86`, so the `%.s86: %.S86` recipe never runs and as86 is handed the
unprocessed source, reporting 87 "unbound label" errors. The suffix change
leaves the produced images byte-identical and only removes the collision.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MbrConan(ConanFile):
    name = "mbr"
    version = "1.2.2"
    description = "Replacement master boot record for IBM PC compatible computers (install-mbr)"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/mbr"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os must be checked against both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def build_requirements(self):
        # Resolved with the build profile; CI passes the same profile for
        # -pr:h and -pr:b, matching the other recipes in this repository.
        self.tool_requires("dev86/0.16.21")  # as86 / ld86
        self.tool_requires("xxd/9.1.0")      # xxd -i (raw image -> C array)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # R33: CC/CFLAGS come from the Conan toolchain, not from shell variables.
        # VirtualBuildEnv puts the tool_requires' bindirs (as86, xxd) on the
        # build PATH used by build().
        AutotoolsToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)

        # E011 (knowledge/graph/E011.kv): configure creates its config.status
        # scratch dir with `umask 077 && mktemp -d ./confXXXXXX`.  On HMDFS
        # the UID mapping (dir owner 20001006 vs process UID) makes the
        # resulting 0700/setgid dir unwritable for the current process, so
        # awk cannot create subs1.awk inside it — deterministic on CI
        # workers (#66398, #66687, #66710; all retries with a relaxed
        # process umask failed because mktemp's dir mode is enforced by the
        # FS, not the caller's umask alone).  Root fix: neutralise the umask
        # inside configure itself before it runs.
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            with open(configure, "r", errors="replace") as fh:
                text = fh.read()
            patched = text.replace("(umask 077 && mktemp",
                                   "(umask 022 && mktemp")
            patched = patched.replace("(umask 077 && mkdir",
                                      "(umask 022 && mkdir")
            if patched != text:
                with open(configure, "w") as fh:
                    fh.write(patched)
                os.chmod(configure, 0o755)
                self.output.info(
                    "E011: relaxed configure's umask 077 -> 022 for the "
                    "config.status scratch dir (HMDFS UID mapping)")

        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: parallel make trips the HMDFS jobserver fifo (EPERM)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
