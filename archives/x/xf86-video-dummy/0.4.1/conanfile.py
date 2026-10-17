#!/usr/bin/env python3
"""Conan recipe for xf86-video-dummy 0.4.1 — X.Org dummy video driver.

This driver produces a loadable shared module (dummy_drv.so) for the X.Org
server. It creates a virtual framebuffer with no physical output, useful for
headless X server testing.

Build approach: direct compilation (bypasses autotools to avoid automake/libtool
dependency in CI). Downloads xorg-server source to extract SDK headers at build
time since xorg-server is not available as a conan package.
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Xf86VideoDummyConan(ConanFile):
    name = "xf86-video-dummy"
    version = "0.4.1"
    description = "X.Org dummy video driver — virtual framebuffer for headless X server"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/driver/xf86-video-dummy"
    url = ""

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xf86-video-dummy supports Linux and OHOS, not {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xorgproto/2025.1")
        self.requires("pixman/0.46.4")

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # ── 1. Download xorg-server source for SDK headers ──
        # URL/sha256 live in conandata.yml under sources["xorg-server-21.1.15"]
        # so CI pre-download and mirror-fallback handling applies to it too.
        sdk_src = os.path.join(self.build_folder, "xorg-server-src")
        get(
            self,
            **self.conan_data["sources"]["xorg-server-21.1.15"],
            strip_root=True,
            destination=sdk_src,
        )

        # ── 2. Set up SDK include directory ──
        sdk_include = os.path.join(self.build_folder, "sdk-include")
        os.makedirs(sdk_include, exist_ok=True)

        # Copy headers from xorg-server source directories that are part of the SDK
        sdk_dirs = [
            "include",
            "dix",
            "os",
            "mi",
            "fb",
            "render",
            "Xext",
            "Xi",
            "composite",
            "randr",
            "xfixes",
            "damageext",
            "present",
            "exa",
            "miext",
            "hw/xfree86",
        ]
        for rel_dir in sdk_dirs:
            abs_dir = os.path.join(sdk_src, rel_dir)
            if os.path.isdir(abs_dir):
                for root, dirs, files in os.walk(abs_dir):
                    for f in files:
                        if f.endswith(".h") and not f.endswith(".h.in"):
                            src = os.path.join(root, f)
                            dst = os.path.join(sdk_include, f)
                            if not os.path.exists(dst):
                                shutil.copy2(src, dst)

        # ── 3. Create xorg-server.h ──
        self._write_xorg_server_h(sdk_include)

        # ── 4. Create pciaccess.h stub ──
        self._write_pciaccess_h(sdk_include)

        # ── 5. Copy pixman.h from pixman dependency ──
        # Also collect all dependency include dirs for compilation
        dep_include_dirs = []
        for dep_name in ["pixman", "xorgproto"]:
            dep = self.dependencies.get(dep_name)
            if dep and dep.cpp_info.includedirs:
                for inc in dep.cpp_info.includedirs:
                    inc_path = str(inc)
                    dep_include_dirs.append(inc_path)
                    self.output.info(f"Dependency {dep_name} include: {inc_path}")
                    # Also check for pixman-1 subdirectory
                    pixman_subdir = os.path.join(inc_path, "pixman-1")
                    if os.path.isdir(pixman_subdir):
                        for f in os.listdir(pixman_subdir):
                            if f.endswith(".h"):
                                dst = os.path.join(sdk_include, f)
                                if not os.path.exists(dst):
                                    shutil.copy2(
                                        os.path.join(pixman_subdir, f),
                                        dst,
                                    )
                        self.output.info(f"Copied pixman headers from {pixman_subdir}")
                    # Also copy pixman.h directly if it exists
                    pixman_h = os.path.join(inc_path, "pixman.h")
                    if os.path.isfile(pixman_h) and not os.path.exists(os.path.join(sdk_include, "pixman.h")):
                        shutil.copy2(pixman_h, os.path.join(sdk_include, "pixman.h"))

        # ── 6. Create config.h (minimal, for PACKAGE_VERSION macros) ──
        config_h = os.path.join(self.source_folder, "config.h")
        Path(config_h).write_text(
            '#include "xorg-server.h"\n'
            "#define PACKAGE_VERSION_MAJOR 0\n"
            "#define PACKAGE_VERSION_MINOR 4\n"
            "#define PACKAGE_VERSION_PATCHLEVEL 1\n"
            "#define PACKAGE_STRING \"xf86-video-dummy 0.4.1\"\n",
            encoding="utf-8",
        )

        # ── 7. Collect include paths ──
        include_dirs = [sdk_include, self.source_folder] + dep_include_dirs

        # ── 8. Get compiler from conan configuration ──
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c") or "clang"

        # ── 9. Compile source files ──
        src_dir = os.path.join(self.source_folder, "src")
        obj_files = []
        for src_file in ["dummy_driver.c", "dummy_cursor.c"]:
            obj_file = os.path.join(self.build_folder, src_file.replace(".c", ".o"))
            cmd = [cc, "-fPIC", "-O2", "-shared"]
            for inc in include_dirs:
                cmd.extend(["-I", inc])
            cmd.extend([
                "-DHAVE_CONFIG_H",
                "-c", os.path.join(src_dir, src_file),
                "-o", obj_file,
            ])
            self.output.info(f"Compiling {src_file}...")
            self.run(" ".join(f'"{a}"' if " " in a else a for a in cmd), env="conanbuild")
            obj_files.append(obj_file)

        # ── 10. Link into dummy_drv.so ──
        out_dir = os.path.join(self.build_folder, "output")
        os.makedirs(out_dir, exist_ok=True)
        output_so = os.path.join(out_dir, "dummy_drv.so")
        link_cmd = [cc, "-shared", "-Wl,-soname,dummy_drv.so"] + obj_files + ["-o", output_so]
        self.output.info("Linking dummy_drv.so...")
        self.run(" ".join(f'"{a}"' if " " in a else a for a in link_cmd), env="conanbuild")

    def package(self):
        out_dir = os.path.join(self.build_folder, "output")
        copy(self, "dummy_drv.so", src=out_dir,
             dst=os.path.join(self.package_folder, "lib", "xorg", "modules", "drivers"))
        # Copy license
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/xorg/modules/drivers"]
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "xf86-video-dummy")
        self.cpp_info.set_property("cmake_target_name", "xf86-video-dummy::dummy_drv")

    # ── Helpers ──

    def _write_xorg_server_h(self, sdk_dir):
        """Write xorg-server.h based on xorg-server 21.1.15 configuration."""
        content = '''/* xorg-server.h — generated for OHOS aarch64, based on xorg-server 21.1.15 */
#ifndef _XORG_SERVER_H_
#define _XORG_SERVER_H_

#define BIGREQS
#define COMPILEDDEFAULTFONTPATH "/usr/share/fonts"
#define COMPOSITE
#define DPMSExtension
#define DRI3
#define HAS_SHM
#define HAVE_REALLOCARRAY 1
#define HAVE_STRCASECMP 1
#define HAVE_STRCASESTR 1
#define HAVE_STRNCASECMP 1
#define HAVE_STRNDUP 1
#define MITSHM
#define PANORAMIX
#define PRESENT
#define RANDR
#define RENDER
#define RES
#define SCREENSAVER
#define SHAPE
#define TCPCONN
#define XCMISC
#define XF86BIGFONT
#define XF86VIDMODE
#define XINERAMA
#define XINPUT
#define XKB_DFLT_RULES "evdev"
#define DRI2
#define XORGSERVER
#define XORG_VERSION_CURRENT 12101015
#define XvExtension
#define XSYNC
#define XTEST
#define XV
#define XVENDORNAME "The X.Org Foundation"
#define __VENDORDWEBSUPPORT__ "https://www.x.org/wiki/"
#define XCONFIGFILE "xorg.conf"
#define __XSERVERNAME__ "Xorg"
#define XFree86LOADER 1
#define XSERVER_LIBPCIACCESS 1
#define FONT_PATH_ELEMENT_NAME_CONST 1
#define X_BYTE_ORDER 1234

#endif /* _XORG_SERVER_H_ */
'''
        Path(os.path.join(sdk_dir, "xorg-server.h")).write_text(content, encoding="utf-8")

    def _write_pciaccess_h(self, sdk_dir):
        """Write minimal pciaccess.h stub (dummy driver doesn't access PCI hardware)."""
        content = '''/* Minimal pciaccess.h stub for OHOS aarch64 */
#ifndef PCIACCESS_H
#define PCIACCESS_H
#include <stdint.h>
struct pci_device {
    uint16_t vendor_id, device_id, subvendor_id, subdevice_id;
    uint8_t revision, prog_if, subclass, class;
    uint32_t domain;
    uint8_t bus, dev, func, irq;
};
struct pci_id_match {
    uint32_t vendor_id, device_id, subvendor_id, subdevice_id;
    uint32_t device_class, device_class_mask;
};
struct pci_device_iterator;
struct pci_device_iterator *pci_slot_match_iterator_create(const struct pci_id_match *);
void pci_iterator_destroy(struct pci_device_iterator *);
struct pci_device *pci_device_next(struct pci_device_iterator *);
int pci_device_cfg_read(struct pci_device *, void *, int, int, int *);
int pci_device_cfg_write(struct pci_device *, const void *, int, int, int *);
int pci_device_probe(struct pci_device *);
#endif /* PCIACCESS_H */
'''
        Path(os.path.join(sdk_dir, "pciaccess.h")).write_text(content, encoding="utf-8")
