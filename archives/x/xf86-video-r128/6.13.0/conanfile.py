#!/usr/bin/env python3
"""Conan recipe — xf86-video-r128 6.13.0 (ATI Rage 128 X.Org video driver)

Build system: autotools (configure + make)
License: MIT
Homepage: https://xorg.freedesktop.org/

The driver compiles against the xorg-server SDK (sdkdir headers +
xorg-server.pc). xorg-server is not published on the Conan registry
(only a prebuilt Xvfb binary exists as a cmd-pkg), so build() downloads
the official xorg-server 21.1.15 source release, extracts the SDK
headers flat into a build-folder-private prefix (R49/E524) and generates
the pkg-config metadata. xorgproto, pixman and libpciaccess are regular
Conan requirements from the registry.

Configure options: --disable-dri --disable-exa (the OHOS xorg-server
does not provide DRI/EXA). HELP2MAN/MAKEINFO are neutralized to avoid
build-time tool dependencies.

Build output: r128_drv.so (loadable driver module) installed to
lib/xorg/modules/drivers/.

Patches:
  0001-config.guess.patch - HMDFS fix + HarmonyOS platform detection
  0002-config.sub.patch   - harmonyos* case pattern
  0003-configure.patch    - HMDFS umask 077 fix
  0004-src-r128_driver.c.patch - #ifdef __OHOS__ skip Int10 BIOS reading
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# xorg-server SDK source (headers only; not published as a Conan package).
# www.x.org serves the same files as xorg.freedesktop.org (301 redirect);
# public x.org mirrors do not carry recent xserver releases, so both
# canonical hostnames are listed for DNS-level redundancy.
XORG_SERVER_VERSION = "21.1.15"
XORG_SERVER_SHA256 = "841c82901282902725762df03adbbcd68153d4cdfb0d61df0cfd73ad677ae089"
XORG_SERVER_URLS = [
    "https://xorg.freedesktop.org/archive/individual/xserver/xorg-server-21.1.15.tar.xz",
    "https://www.x.org/archive/individual/xserver/xorg-server-21.1.15.tar.xz",
]

# Source directories that make up the xorg-server SDK headers. The real
# xorg-server installs these flat into $(sdkdir), so drivers include
# them without a path prefix (e.g. #include "xf86str.h").
SDK_SOURCE_DIRS = [
    "hw/xfree86", "include", "Xext", "mi", "os", "present",
    "randr", "render", "composite", "damageext", "fb", "dbe",
    "Xi", "miext",
]


class Xf86VideoR128Conan(ConanFile):
    name = "xf86-video-r128"
    version = "6.13.0"
    description = "ATI Rage 128 video driver for X.Org"
    license = "MIT"
    homepage = "https://xorg.freedesktop.org/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Protocol headers, rendering library and PCI bus access are
        # published on the ohpcd registry.
        self.requires("xorgproto/2025.1")
        self.requires("pixman/0.46.4.3")
        self.requires("libpciaccess/0.19")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dri")
        tc.configure_args.append("--disable-exa")
        tc.configure_args.append("SED=sed")
        tc.configure_args.append("HELP2MAN=/bin/true")
        tc.configure_args.append("MAKEINFO=/bin/true")
        tc.generate()
        PkgConfigDeps(self).generate()

    def _download_xorg_server_source(self):
        """Download the official xorg-server release with mirror fallback."""
        src_dir = os.path.join(self.build_folder, "xorg-server-src")
        done_marker = os.path.join(src_dir, "configure.ac")
        if os.path.exists(done_marker):
            return src_dir
        last_error = None
        for url in XORG_SERVER_URLS:
            try:
                get(self, url, sha256=XORG_SERVER_SHA256,
                    destination=src_dir, strip_root=True)
                self.output.info(f"Downloaded xorg-server {XORG_SERVER_VERSION} from {url}")
                return src_dir
            except Exception as e:
                last_error = e
                self.output.warning(f"Failed to download xorg-server source from {url}: {e}")
        raise ConanException(
            f"Could not download xorg-server {XORG_SERVER_VERSION} from any "
            f"mirror: {last_error}")

    def _extract_sdk_headers(self, src_dir, sdkdir):
        """Copy SDK headers flat into sdkdir, mirroring the real
        xorg-server SDK install layout ($(sdkdir) is flat)."""
        os.makedirs(sdkdir, exist_ok=True)
        count = 0
        for rel_dir in SDK_SOURCE_DIRS:
            abs_dir = os.path.join(src_dir, rel_dir)
            if not os.path.isdir(abs_dir):
                continue
            for root, _dirs, files in os.walk(abs_dir):
                for fn in files:
                    if not fn.endswith(".h"):
                        continue
                    dst = os.path.join(sdkdir, fn)
                    if os.path.exists(dst):
                        # No basename collisions expected in the SDK set;
                        # first copy wins to stay deterministic.
                        continue
                    shutil.copy2(os.path.join(root, fn), dst)
                    count += 1
        self.output.info(f"Extracted {count} xorg-server SDK headers into {sdkdir}")
        if count == 0:
            raise ConanException("xorg-server SDK header extraction produced no files")

    def _write_sdk_config_headers(self, sdkdir):
        """Generate the headers that xorg-server's configure normally
        generates for external module builds."""
        xorg_server_h = os.path.join(sdkdir, "xorg-server.h")
        if not os.path.exists(xorg_server_h):
            with open(xorg_server_h, "w") as fh:
                fh.write(
                    "/* Minimal xorg-server.h for external driver modules.\n"
                    " * Generated by conanfile.py; mirrors include/xorg-server.h.in. */\n"
                    "#ifndef _XORG_SERVER_H_\n"
                    "#define _XORG_SERVER_H_\n"
                    '#include "dix-config.h"\n'
                    "#define XORG_VERSION_CURRENT ((21 * 10000000) + (1 * 100000) + (15 * 1000))\n"
                    "#define XSERVER_VERSION_MAJOR 21\n"
                    "#define XSERVER_VERSION_MINOR 1\n"
                    "#define XSERVER_VERSION_PATCH 15\n"
                    '#define __XSERVERNAME__ "Xorg"\n'
                    "#define XV 1\n"
                    "#endif\n")

        xorg_config_h = os.path.join(sdkdir, "xorg-config.h")
        if not os.path.exists(xorg_config_h):
            with open(xorg_config_h, "w") as fh:
                fh.write(
                    "/* Minimal xorg-config.h for external driver modules.\n"
                    " * Generated by conanfile.py; mirrors include/xorg-config.h.in. */\n"
                    "#ifndef _XORG_CONFIG_H_\n"
                    "#define _XORG_CONFIG_H_\n"
                    "#include <dix-config.h>\n"
                    "#include <xkb-config.h>\n"
                    "#define XORGSERVER 1\n"
                    "#define XORG_VERSION_CURRENT ((21 * 10000000) + (1 * 100000) + (15 * 1000))\n"
                    "#define _XSERVER64 1\n"
                    "#define XSERVER_LIBPCIACCESS 1\n"
                    "#define XSERVER_PLATFORM_BUS 1\n"
                    "#define DEFAULT_MODULE_PATH \"/lib/xorg/modules\"\n"
                    "#define DEFAULT_LIBRARY_PATH \"/lib\"\n"
                    "#endif\n")

        xkb_config_h = os.path.join(sdkdir, "xkb-config.h")
        if not os.path.exists(xkb_config_h):
            with open(xkb_config_h, "w") as fh:
                fh.write(
                    "/* Minimal xkb-config.h for external driver modules. */\n"
                    "#ifndef _XKB_CONFIG_H_\n"
                    "#define _XKB_CONFIG_H_\n"
                    "#define XKB_BASE_DIRECTORY \"/share/X11/xkb\"\n"
                    "#define XKB_BIN_DIRECTORY \"/bin\"\n"
                    "#define XKM_OUTPUT_DIR \"/lib/xorg\"\n"
                    "#endif\n")

        dix_config_h = os.path.join(sdkdir, "dix-config.h")
        if not os.path.exists(dix_config_h):
            with open(dix_config_h, "w") as fh:
                fh.write(
                    "/* Minimal dix-config.h for external driver modules.\n"
                    " * Generated by conanfile.py; mirrors include/dix-config.h.in\n"
                    " * for an aarch64 OHOS build with libpciaccess. */\n"
                    "#ifndef _DIX_CONFIG_H_\n"
                    "#define _DIX_CONFIG_H_\n\n"
                    "#define XSERVER_VERSION_MAJOR 21\n"
                    "#define XSERVER_VERSION_MINOR 1\n"
                    "#define XSERVER_VERSION_PATCH 15\n"
                    "#define XSERVER_LIBPCIACCESS 1\n"
                    "#define XFree86Server 1\n"
                    "#define XSERVER_PLATFORM_BUS 1\n"
                    "#define COMPOSITE 1\n"
                    "#define DAMAGE 1\n"
                    "#define MITSHM 1\n"
                    "#define RANDR 1\n"
                    "#define RENDER 1\n"
                    "#define XFIXES 1\n"
                    "#define XKB 1\n"
                    "#define XFree86LOADER 0\n"
                    "#define WITHIN_XSERVER 1\n"
                    "#define XV 1\n"
                    "#define DGA 0\n"
                    "#define XF86VIDMODE 0\n"
                    "#define SCREENSAVER 0\n"
                    "#define RES 0\n"
                    "#define DPMSExtension 1\n"
                    "#define PANORAMIX 0\n"
                    "#define XRECORD 1\n"
                    "#define XINPUT 1\n"
                    "#define XTEST 1\n"
                    "#define DBE 1\n"
                    "#define PRESENT 1\n"
                    "#define DRI2 0\n"
                    "#define DRI3 0\n"
                    "#define GLXEXT 0\n"
                    "#define _XSERVER64 1\n"
                    "#define X_BYTE_ORDER __BYTE_ORDER__\n"
                    "#define HAVE_DLFCN_H 1\n"
                    "#define HAVE_SYS_TYPES_H 1\n"
                    "#define HAVE_SYS_MMAN_H 1\n"
                    "#define HAVE_STDBOOL_H 1\n"
                    "#define HAVE_STDLIB_H 1\n"
                    "#define HAVE_STRING_H 1\n"
                    "#define HAVE_INTTYPES_H 1\n"
                    "#define HAVE_STDINT_H 1\n"
                    "#define HAVE_UNISTD_H 1\n"
                    "#define HAVE_FNMATCH_H 1\n"
                    "#define HAVE_PTHREAD_H 1\n"
                    "#define HAVE_ENDIAN_H 1\n"
                    "#define HAVE_POLL_H 1\n"
                    "#define HAVE_GETOPT_LONG 1\n"
                    "#define HAVE_GETTIMEOFDAY 1\n"
                    "#define HAVE_CLOCK_GETTIME 1\n"
                    "#define HAVE_SHM 1\n"
                    "#define HAVE_MMAP 1\n"
                    "#define HAVE_FFS 1\n"
                    "#define HAVE_STRCASECMP 1\n"
                    "#define HAVE_STRNDUP 1\n"
                    "#define HAVE_VASPRINTF 1\n"
                    "#define HAVE_VSNPRINTF 1\n"
                    "#define HAVE_SNPRINTF 1\n"
                    "#define HAVE_MEMALIGN 1\n"
                    "#define HAVE_SIGACTION 1\n"
                    "#define HAVE_FLOCK 1\n"
                    "#define HAVE_REGEX_H 1\n"
                    "#define HAVE_SOCKET 1\n"
                    "#define MODULEDIR \"/lib/xorg/modules\"\n"
                    "#define DEFAULT_LIBRARY_PATH \"/lib\"\n"
                    "#endif\n")

    def _write_xorg_server_pc(self, sdkdir):
        """Write xorg-server.pc next to the PkgConfigDeps output so a
        single PKG_CONFIG_PATH entry covers everything."""
        pc_path = os.path.join(self.generators_folder, "xorg-server.pc")
        with open(pc_path, "w") as fh:
            fh.write(
                "sdkdir=" + sdkdir + "\n"
                "\n"
                "Name: xorg-server\n"
                "Description: Modular X.Org X server (SDK headers; runtime "
                "ships as the ohpcd xorg-server cmd-pkg)\n"
                "Version: " + XORG_SERVER_VERSION + "\n"
                "Requires: pixman-1\n"
                "Cflags: -I${sdkdir}\n")

    def _alias_pciaccess_pc(self):
        """PkgConfigDeps names the file after the Conan package
        (libpciaccess.pc); upstream configure probes 'pciaccess'."""
        src = os.path.join(self.generators_folder, "libpciaccess.pc")
        dst = os.path.join(self.generators_folder, "pciaccess.pc")
        if os.path.exists(src) and not os.path.exists(dst):
            with open(src, "r") as fh:
                content = fh.read()
            content = content.replace("Name: libpciaccess", "Name: pciaccess")
            with open(dst, "w") as fh:
                fh.write(content)
            self.output.info("Created pciaccess.pc alias for libpciaccess.pc")

    def _setup_pkg_config_path(self):
        """Make pkg-config see both the generator output (xorg-server.pc,
        pciaccess.pc, pixman-1.pc, ...) and the proto .pc files shipped
        inside the xorgproto package."""
        paths = [self.generators_folder]
        proto_pc_dir = os.path.join(
            self.dependencies["xorgproto"].package_folder, "share", "pkgconfig")
        if os.path.isdir(proto_pc_dir):
            paths.append(proto_pc_dir)
        existing = os.environ.get("PKG_CONFIG_PATH", "")
        if existing:
            paths.append(existing)
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(paths)

    def _prepare_xorg_server_sdk(self):
        sdk_prefix = os.path.join(self.build_folder, "xorg-sdk")
        sdkdir = os.path.join(sdk_prefix, "include", "xorg")
        marker = os.path.join(self.generators_folder, "xorg-server.pc")
        if os.path.exists(marker) and os.path.isdir(sdkdir):
            return  # already prepared
        src_dir = self._download_xorg_server_source()
        self._extract_sdk_headers(src_dir, sdkdir)
        self._write_sdk_config_headers(sdkdir)
        self._write_xorg_server_pc(sdkdir)
        self._alias_pciaccess_pc()

    def build(self):
        self._prepare_xorg_server_sdk()
        self._setup_pkg_config_path()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["r128_drv"]
        self.cpp_info.libdirs = ["lib/xorg/modules/drivers"]
