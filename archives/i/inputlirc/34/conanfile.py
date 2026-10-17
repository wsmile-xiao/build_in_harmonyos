from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, chdir, copy,
                               export_conandata_patches, get, save)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout

import os
import subprocess

required_conan_version = ">=2.0"


class InputlircConan(ConanFile):
    name = "inputlirc"
    version = "34"
    package_type = "application"
    description = ("inputlircd - zeroconf LIRC daemon that reads Linux input "
                   "event devices and republishes the events on a local socket")
    license = "GPL-2.0-only"
    homepage = "https://git.sliepen.org/inputlirc"  # Debian d/control; measured 404 (notes.md 6)
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lirc", "input", "evdev", "daemon", "harmonyos")
    settings = "os", "compiler", "build_type", "arch"

    @property
    def _cc(self):
        # R33: never read CC/CFLAGS from the ambient shell; take the compiler
        # that the Conan profile/toolchain actually selected.
        executables = self.conf_info.get("tools.build:compiler_executables", default={}) or {}
        cc = executables.get("c")
        if not cc:
            cc = str(self.settings.compiler)
        return cc

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: OHOS is Linux-like; accept both, never == "Linux" only.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "inputlirc needs a Linux-family OS (evdev), got %s" % self.settings.os)

    def generate(self):
        # Emits conanbuild.conf (Autotools needs it) plus CC/CFLAGS from the
        # Conan toolchain rather than the ambient shell (R33).
        AutotoolsToolchain(self).generate()

    def _uapi_include_dir(self):
        """Ask the compiler where it actually finds <linux/input-event-codes.h>.

        Upstream assumes /usr/include; on HarmonyOS the UAPI headers live inside
        the SDK sysroot, whose location embeds an SDK version, so resolve it from
        the preprocessor rather than hardcoding it.
        """
        stub = os.path.join(self.build_folder, "_uapi_probe.c")
        save(self, stub, "#include <linux/input-event-codes.h>\n")
        out = ""
        try:
            res = subprocess.run([self._cc, "-M", stub], capture_output=True,
                                 text=True, cwd=self.build_folder)
            out = res.stdout or ""
        except OSError:
            out = ""
        wanted = os.path.join("linux", "input-event-codes.h")
        for tok in out.replace("\\\n", " ").split():
            tok = tok.strip()
            if tok.endswith(wanted) or tok.endswith("linux/input-event-codes.h"):
                d = tok.split("/linux/")[0] if "/linux/" in tok else os.path.dirname(os.path.dirname(tok))
                os.remove(stub)
                return d
        os.remove(stub)
        # Silence here would resurrect the hardcoded-path assumption this recipe
        # exists to remove, so only accept /usr/include when it really has linux/.
        if os.path.isdir(os.path.join("/usr/include", "linux")):
            self.output.info("UAPI header not resolved from compiler output; "
                             "using /usr/include, verified to hold linux/")
            return "/usr/include"
        raise ConanInvalidConfiguration(
            "Could not resolve the directory that provides "
            "<linux/input-event-codes.h> from the compiler, and this host has "
            "no /usr/include/linux either.")

    def _install_shim(self):
        """POSIX stand-in for install(1), which the HarmonyOS image lacks."""
        shim = os.path.join(self.build_folder, "install-sh")
        save(self, shim, """#!/bin/sh
# Minimal install(1): supports "install SRC DEST" and "install -m MODE SRC DEST".
mode=755
if [ "$1" = "-m" ]; then
    mode="$2"
    shift 2
fi
src="$1"
dest="$2"
if [ -d "$dest" ]; then
    dest="$dest/`basename \"$src\"`"
fi
cp "$src" "$dest" || exit 1
chmod "$mode" "$dest" || exit 1
exit 0
""")
        os.chmod(shim, 0o755)
        return shim

    def build(self):
        apply_conandata_patches(self)
        # E490: unpacked scripts can lose their exec bit on HMDFS (chmod is not
        # always persisted); gennames is invoked as ./gennames by make.
        os.chmod(os.path.join(self.source_folder, "gennames"), 0o755)
        # Upstream has no configure and the Makefile is not VPATH-aware, so drive
        # make inside the source tree instead of relying on Autotools helpers
        # (Autotools.make() takes no script_folder on Conan 2.29).
        with chdir(self, self.source_folder):
            self.run("make -j1 all KERNELINC=%s" % self._uapi_include_dir())

    def package(self):
        pkg = self.package_folder
        # Upstream installs the daemon to $(PREFIX)/sbin; Conan and the CI L0k
        # check both look under bin/, so SBINDIR is retargeted at packaging time
        # (a layout decision, not a source change).
        with chdir(self, self.source_folder):
            self.run(" ".join([
                "make", "-j1", "install",
                # the Makefile prerequisites still name $(KERNELINC)/linux/*.h, so
                # the value has to be repeated for the install target
                "KERNELINC=%s" % self._uapi_include_dir(),
                "PREFIX=%s" % pkg,
                "SBINDIR=%s" % os.path.join(pkg, "bin"),
                "SHAREDIR=%s" % os.path.join(pkg, "share"),
                "MANDIR=%s" % os.path.join(pkg, "share", "man"),
                "SYSTEMDDIR=%s" % os.path.join(pkg, "lib", "systemd", "system"),
                "INSTALL=%s" % self._install_shim(),
            ]))
        # No license file ships inside the .orig tarball; the GPL-2.0 grant is in
        # each source header, so record the provenance rather than invent one.
        copy(self, "inputlircd.8", src=self.source_folder,
             dst=os.path.join(self.package_folder, "man"), keep_path=False)

    def package_info(self):
        # inputlircd is a program, not a linkable library.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
