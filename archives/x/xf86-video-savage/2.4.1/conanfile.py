#!/usr/bin/env python3
"""Conan recipe for xf86-video-savage 2.4.1 — S3 Savage X.Org video driver.

This driver is an X.Org video driver module (savage_drv.so) that is loaded
by the X server at runtime as a shared library module.

Build approach:
  The driver is built with its own Autotools build system. The configure
  script requires the xorg-server SDK via pkg-config (xorg-server.pc),
  which is not available as a Conan package. Following the approach used
  by xf86-video-fbdev in this repository, the SDK headers are set up from
  the official xorg-server 21.1.15 source tarball during the build step
  and a matching xorg-server.pc is generated in a private build folder.

  With the real upstream xorg-server headers the driver compiles with its
  full feature set: EXA acceleration, hardware cursor, I2C/DDC, shadow
  framebuffer and the complete VBE/BIOS code path (VBE symbols resolve
  against the X server's int10 module at runtime — on non-x86 hosts the
  server's upstream stub int10 implementation simply reports no VBE, the
  driver guards every VBE call behind a pVbe != NULL check, as designed
  upstream). No source-level platform stubs are used.

  XAA is auto-disabled by configure (xorg-server 21.x no longer ships
  xaa.h; the driver guards all XAA code with HAVE_XAA_H). DRI is
  explicitly disabled (DRI1 was removed from xorg-server and needs
  savage kernel DRM which does not exist on OpenHarmony).

  pixman, xorgproto and libpciaccess are provided via Conan requirements.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Xf86VideoSavageConan(ConanFile):
    name = "xf86-video-savage"
    version = "2.4.1"
    description = "S3 Savage video driver for the X.Org X Server"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/driver/xf86-video-savage"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # X.Org driver module loaded by the server at runtime (shared module)
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xf86-video-savage supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("pixman/0.46.4.3")
        self.requires("xorgproto/2025.1")
        self.requires("libpciaccess/0.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # DRI1 was removed from xorg-server 21.x and requires the savage
        # kernel DRM module (not available on OpenHarmony). XAA is skipped:
        # configure auto-detects the missing xaa.h and disables it.
        tc.configure_args.append("--disable-dri")
        tc.generate()

    def _setup_xorg_sdk(self):
        """Set up the xorg-server driver SDK (headers + pkg-config files).

        The xorg-server is not available as a Conan package, so its SDK
        headers are taken from the official source tarball (same approach
        as xf86-video-fbdev). Everything is placed inside the private
        build folder — nothing is written to shared system paths.
        """
        sdk_dir = os.path.join(self.build_folder, "xorg-sdk")
        sdk_include = os.path.join(sdk_dir, "include", "xorg")
        os.makedirs(sdk_include, exist_ok=True)

        # 1. Fetch xorg-server sources
        xorg_data = self.conan_data["xorg_server"]
        xorg_src = os.path.join(self.build_folder, "xorg-server-src")
        get(self, url=xorg_data["url"], sha256=xorg_data["sha256"],
            strip_root=True, destination=xorg_src)

        # 2. Collect the driver SDK headers (same layout the server installs
        #    into sdkdir=/usr/include/xorg). Directories cover the standard
        #    SDK set used by fbdev plus the ones this driver additionally
        #    pulls in: exa, hw/xfree86/int10 (vbe.h/xf86int10.h),
        #    hw/xfree86/modes (xf86Modes.h), hw/xfree86/os-support/bus
        #    (xf86Pci.h).
        header_dirs = [
            "include", "fb", "mi", "Xext", "composite", "randr", "render",
            "Xi", "os", "dix", "damageext", "dbe", "xfixes", "xkb", "present",
            "exa",
            "hw/xfree86", "hw/xfree86/common", "hw/xfree86/os-support",
            "hw/xfree86/os-support/bus", "hw/xfree86/ddc", "hw/xfree86/fbdevhw",
            "hw/xfree86/int10", "hw/xfree86/i2c", "hw/xfree86/modes",
            "hw/xfree86/parser",
            "hw/xfree86/ramdac", "hw/xfree86/shadowfb", "hw/xfree86/vgahw",
            "hw/xfree86/xkb",
            "miext/shadow", "miext/damage", "miext/sync",
        ]
        for d in header_dirs:
            full_dir = os.path.join(xorg_src, d)
            if not os.path.isdir(full_dir):
                continue
            for fname in os.listdir(full_dir):
                if fname.endswith(".h"):
                    dst = os.path.join(sdk_include, fname)
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.copy2(os.path.join(full_dir, fname), dst)

        # 3. Generate xorg-server.h — the configuration header every driver
        #    must include first (servermd.h enforces this). It carries the
        #    extension/feature defines that XORG_DRIVER_CHECK_EXT probes in
        #    configure. ABI version macros come from the real
        #    hw/xfree86/common/xf86Module.h copied above.
        xorg_server_h = os.path.join(sdk_include, "xorg-server.h")
        with open(xorg_server_h, "w") as f:
            f.write('''/*
 * xorg-server.h — SDK configuration header for xorg-server 21.1.15
 * Generated by the xf86-video-savage Conan recipe for aarch64-linux-ohos.
 */
#ifndef _XORG_SERVER_H_
#define _XORG_SERVER_H_

#define XORG_VERSION_CURRENT 210115000

/* Extensions enabled in this server build (probed by driver configure) */
#define RANDR 1
#define RENDER 1
#define XV 1
#define XvExtension 1
#define DPMSExtension 1
#define COMPOSITE 1
#define XINPUT 1
#define DAMAGE 1
#define XFIXES 1
#define PANORAMIX 1
#define RES 1
#define SCREENSAVER 1
#define XSYNC 1
#define XTEST 1
#define XCMISC 1
#define BIGREQS 1
#define SHAPE 1
#define XFreeXDGA 1

/* The server uses libpciaccess for PCI access (mandatory since 1.13) */
#define XSERVER_LIBPCIACCESS 1

/* Bus/platform support */
#define XSERVER_PLATFORM_BUS 1

/* Byte order: aarch64 is little-endian */
#define X_BYTE_ORDER 1234
#define X_LITTLE_ENDIAN 1234
#define X_BIG_ENDIAN 4321

/* Loadable XFree86 server (unconditional in upstream xorg-server.h) */
#define XFree86LOADER 1

#endif /* _XORG_SERVER_H_ */
''')

        # 4. Locate the conan dependency packages
        pixman_pkg = self.dependencies["pixman"].package_folder
        pciaccess_pkg = self.dependencies["libpciaccess"].package_folder

        # 5. Generate pkg-config files in the private SDK prefix
        pkgconfig_dir = os.path.join(sdk_dir, "lib", "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)

        # 5a. xorg-server.pc — mirrors xorg-server.pc.in from the tarball.
        #     Cflags also exposes the conan libpciaccess headers, matching
        #     what /usr/include/pciaccess.h provides in a distro build.
        with open(os.path.join(pkgconfig_dir, "xorg-server.pc"), "w") as f:
            f.write(f"""prefix={sdk_dir}
exec_prefix=${{prefix}}
libdir=${{prefix}}/lib
includedir=${{prefix}}/include
datarootdir=${{prefix}}/share
moduledir=${{libdir}}/xorg/modules
sdkdir=${{includedir}}/xorg
sysconfigdir=${{datarootdir}}/X11/xorg.conf.d

abi_ansic=0.4
abi_videodrv=25.2
abi_xinput=24.4
abi_extension=10.0

Name: xorg-server
Description: Modular X.Org X Server (driver SDK)
Version: 21.1.15
Requires.private: pixman-1 xproto fontsproto randrproto renderproto videoproto xextproto
Cflags: -I${{sdkdir}} -I{pciaccess_pkg}/include
Libs: -L${{libdir}}
""")

        # 5b. pixman-1.pc — the file shipped inside the conan package has a
        #     placeholder prefix, so a corrected one is generated here.
        with open(os.path.join(pkgconfig_dir, "pixman-1.pc"), "w") as f:
            f.write(f"""prefix={pixman_pkg}
includedir=${{prefix}}/include
libdir=${{prefix}}/lib

Name: Pixman
Description: The pixman library (version 1)
Version: 0.46.4
Libs: -L${{libdir}} -lpixman-1
Cflags: -I${{includedir}}/pixman-1
""")

        # 5c. pciaccess.pc — same placeholder-prefix situation; the driver
        #     only needs its headers (symbols resolve against the X server
        #     at runtime), so zlib is not pulled into Requires here.
        with open(os.path.join(pkgconfig_dir, "pciaccess.pc"), "w") as f:
            f.write(f"""prefix={pciaccess_pkg}
includedir=${{prefix}}/include
libdir=${{prefix}}/lib

Name: pciaccess
Description: Library providing generic access to the PCI bus and devices
Version: 0.19
Libs: -L${{libdir}} -lpciaccess
Cflags: -I${{includedir}}
""")

        return sdk_dir

    def build(self):
        apply_conandata_patches(self)

        sdk_dir = self._setup_xorg_sdk()

        # Wire pkg-config to the private SDK + the conan-provided proto pc
        # files. Everything the driver configure probes (xorg-server, xproto,
        # fontsproto, randrproto, renderproto, videoproto, xextproto,
        # pixman-1, pciaccess) resolves from these directories.
        xorgproto_pc = os.path.join(
            self.dependencies["xorgproto"].package_folder, "share", "pkgconfig")
        os.environ["PKG_CONFIG_PATH"] = ":".join([
            os.path.join(sdk_dir, "lib", "pkgconfig"),
            xorgproto_pc,
        ])

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["savage_drv"]
        self.cpp_info.libdirs = ["lib/xorg/modules/drivers"]
        self.cpp_info.includedirs = []
