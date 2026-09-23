#!/usr/bin/env python3
"""Conan recipe — gusb 0.4.9 (libgusb, Meson).

GObject wrapper for libusb1: asynchronous control/bulk/interrupt USB
transfers with mainloop integration. Used by colord for USB device
detection (hard dependency: `gusb = dependency('gusb', ...)`).

OHOS adaptation notes:
- Dependencies: gio-2.0/glib-2.0 (glib package), libusb-1.0, json-glib-1.0.
- Self-tests (gusb-self-test / gusb-umockdev-test) need usb.ids (hwdata)
  and umockdev, which are unavailable on OHOS -> -Dtests=false
  -Dumockdev=disabled.
- vapi/docs/introspection are desktop niceties; introspection is kept
  OFF here because gobject-introspection adds cross-build complexity and
  colord only needs the C library + pkg-config file.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class GusbConan(ConanFile):
    name = "gusb"
    version = "0.4.9"
    description = "GObject wrapper for libusb1"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/hughsie/libgusb"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("glib/2.84.0.1")
        self.requires("libusb/1.0.27")
        self.requires("json-glib/1.10.6")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def _inject_meson_binaries(self):
        """Inject ar/ranlib/pkg-config into conan_meson_native.ini."""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_lines = []
            for line in content.splitlines(True):
                new_lines.append(line)
                if line.strip() == "[binaries]":
                    if ar and "\nar =" not in content:
                        new_lines.append("ar = '%s'\n" % ar)
                    if rl and "\nranlib =" not in content:
                        new_lines.append("ranlib = '%s'\n" % rl)
                    if pkg_config and "\npkg-config =" not in content:
                        new_lines.append("pkg-config = '%s'\n" % pkg_config)
            new_content = "".join(new_lines)
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["tests"] = "false"
        tc.project_options["umockdev"] = "disabled"
        tc.project_options["vapi"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["introspection"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        if not shutil.which("meson"):
            self.run("python3 -m pip install --user meson")
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """OHOS ELF codesign (binary-sign-tool), same as libusb/glib recipes."""
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"], check=True)
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "gusb")
        self.cpp_info.set_property("pkg_config_name", "gusb")

        gusb = self.cpp_info.components["gusb"]
        gusb.set_property("cmake_target_name", "gusb::gusb")
        gusb.set_property("pkg_config_name", "gusb")
        gusb.libs = ["gusb"]
        gusb.includedirs = ["include/gusb-1"]
        gusb.libdirs = ["lib"]
        gusb.requires = ["glib::glib", "libusb::libusb", "json-glib::json-glib"]
