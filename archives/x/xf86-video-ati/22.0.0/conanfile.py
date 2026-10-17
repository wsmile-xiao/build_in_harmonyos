#!/usr/bin/env python3
"""Conan recipe — xf86-video-ati 22.0.0 (Autotools).

X.Org video driver for ATI/Radeon hardware.  The package builds two libtool
modules installed to lib/xorg/modules/drivers/:

    ati_drv.so    legacy ATI wrapper driver (module data: atiModuleData)
    radeon_drv.so Radeon KMS driver (module data: radeonModuleData)

The modules are dlopen'ed by the X.Org server at runtime and resolve their
xorg-server symbols from the server process, so they are not link libraries
for consumers (cpp_info.libs stays empty; libdirs points at the module
directory).

Source: the official freedesktop.org release tarball, which ships all
pre-generated autotools files — only three small portability patches are
needed (HarmonyOS triplet in config.guess/config.sub, HMDFS umask fix in
configure).  The build runs the shipped ./configure directly; no
autoconf/automake is required.

xorg-server SDK (build-time, in-recipe generation — see _setup_xorg_sdk):
  Every X.Org DDX driver compiles against the xorg-server SDK headers and
  queries xorg-server.pc.  xorg-server is not yet published to the conan
  registry (R36 dependency gap, tracked in notes.md), so this recipe
  generates the SDK from the official xorg-server 21.1.15 release tarball at
  build time (same approach as the merged xf86-video-fbdev recipe):
    1. run the tarball's own autotools ./configure with every DDX disabled
       (only pixman + the xorgproto protocol .pc files + a SHA1 provider are
       needed — all published) so config.status generates the REAL SDK
       config headers (xorg-server.h, dix-config.h, ...);
    2. copy the SDK header set (the exact install_data list from the
       xorg-server meson.build files) into <build_folder>/xorg-sdk;
    3. complete the generated xorg-server.h with the XORG-DDX defines that
       the autotools build only emits when the Xorg DDX is enabled
       (XORG_VERSION_CURRENT, XSERVER_LIBPCIACCESS, ... — the values meson
       sets for an Xorg build);
    4. synthesize xorg-server.pc pointing at that sdkdir.
  Nothing from the xorg-server tarball is packaged; when a real
  xorg-server conan package is published this can switch back to a plain
  self.requires().

OHOS notes:
  - glamor is disabled (--disable-glamor): it hard-requires pkg-config
    module "gbm" (mesa), which does not exist on HarmonyOS PC.  glamor is an
    optional GL acceleration path; the EXA/KMS code paths of the driver are
    unaffected.  With glamor off, every gbm symbol reference in the driver
    source is compiled out (USE_GLAMOR); the sole remaining <gbm.h> include
    in radeon_dri3.c (needed for the DRI3 path, kept enabled) is satisfied
    by a documented stub header written into the sdkdir — no gbm code is
    linked.
  - libudev support is auto-detected and gracefully disabled (no libudev
    recipe on OHOS).
  - conan's libdrm package merges all component libraries (drm_amdgpu,
    drm_radeon, ...) into one libdrm.pc, but upstream configure checks the
    pkg-config module "libdrm_radeon" (LIBDRM_RADEON_CFLAGS/LIBS).  generate()
    therefore synthesizes a libdrm_radeon.pc next to the PkgConfigDeps files;
    the same is done for "pciaccess" (conan package name is libpciaccess).
  - the xorg-server 21.1.15 configure has an unconditional "xfont2"
    requirement in REQUIRED_LIBS; a metadata-only xfont2.pc stub satisfies
    the pkg-config resolution for the SDK configure run (xfont2 headers are
    never used by a DDX driver SDK and nothing is built against them).
  - the OHOS clang does not read stdin implicitly (plain `clang -E` fails
    with "no input files"), which breaks the xorg-server configure's
    XORG_PROG_RAWCPP stdin probes; a small `cpp` wrapper (clang -E -x c -)
    is written into the build folder and prepended to PATH for the SDK
    configure run.
  - the X server SDK headers (compiler.h) do #include <pixman.h>, so
    pixman's include path is injected into CFLAGS explicitly (it is also
    carried transitively via xorg-server.pc's Requires.private).
  - config.status (generated during configure) embeds the same umask 077
    temp-dir logic that breaks on HMDFS; build() patches it in place after
    configure and re-runs it if it failed (E011, same handling as abook).
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, apply_conandata_patches, export_conandata_patches, load, save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# Xorg-server version whose SDK is generated (official release tarball,
# pinned by sha256 in conandata.yml).  ABI_VIDEODRV 25.2 — same video
# driver ABI as 21.1.14 originally requested by this recipe.
XORG_SERVER_VERSION = "21.1.15"

# ABI versions from xorg-server's hw/xfree86/common/xf86Module.h (static
# #defines; shown by the pinned 21.1.15 tarball).
XORG_ABI_ANSIC = "0.4"
XORG_ABI_VIDEODRV = "25.2"
XORG_ABI_XINPUT = "24.4"
XORG_ABI_EXTENSION = "10.0"

# SDK header set installed by the xorg-server build into sdkdir
# (include/xorg), flattened to basenames exactly like meson's install_data.
# Extracted from every `install_data(... install_dir: xorgsdkdir)` rule in
# the pinned xorg-server 21.1.15 tarball, including the conditional list
# appends for enabled features (Xv: xf86xv/xvpriv/xvmc + xvdix/xvmcext,
# XACE, Xinerama, MIT-SHM).  Excluded, matching the SDK configure flags:
# glamor.h (glamor disabled), vndserver.h/glx_extinit.h/glxvndabi.h (glx
# disabled), dgaproc.h (dga disabled).
XORG_SDK_HEADERS = (
    "Xext/geext.h",
    "Xext/geint.h",
    "Xext/panoramiX.h",
    "Xext/panoramiXsrv.h",
    "Xext/shmint.h",
    "Xext/syncsdk.h",
    "Xext/xace.h",
    "Xext/xacestr.h",
    "Xext/xvdix.h",
    "Xext/xvmcext.h",
    "composite/compositeext.h",
    "dbe/dbestruct.h",
    "dri3/dri3.h",
    "exa/exa.h",
    "fb/fb.h",
    "fb/fboverlay.h",
    "fb/fbpict.h",
    "fb/fbrop.h",
    "fb/wfbrename.h",
    "hw/xfree86/common/compiler.h",
    "hw/xfree86/common/xaarop.h",
    "hw/xfree86/common/xf86.h",
    "hw/xfree86/common/xf86MatchDrivers.h",
    "hw/xfree86/common/xf86Module.h",
    "hw/xfree86/common/xf86Opt.h",
    "hw/xfree86/common/xf86Optionstr.h",
    "hw/xfree86/common/xf86PciInfo.h",
    "hw/xfree86/common/xf86Priv.h",
    "hw/xfree86/common/xf86Privstr.h",
    "hw/xfree86/common/xf86VGAarbiter.h",
    "hw/xfree86/common/xf86Xinput.h",
    "hw/xfree86/common/xf86cmap.h",
    "hw/xfree86/common/xf86fbman.h",
    "hw/xfree86/common/xf86platformBus.h",
    "hw/xfree86/common/xf86sbusBus.h",
    "hw/xfree86/common/xf86str.h",
    "hw/xfree86/common/xf86xv.h",
    "hw/xfree86/common/xf86xvmc.h",
    "hw/xfree86/common/xf86xvpriv.h",
    "hw/xfree86/common/xisb.h",
    "hw/xfree86/common/xorgVersion.h",
    "hw/xfree86/ddc/edid.h",
    "hw/xfree86/ddc/xf86DDC.h",
    "hw/xfree86/dri/dri.h",
    "hw/xfree86/dri/dristruct.h",
    "hw/xfree86/dri/sarea.h",
    "hw/xfree86/dri2/dri2.h",
    "hw/xfree86/drivers/inputtest/xf86-input-inputtest-protocol.h",
    "hw/xfree86/fbdevhw/fbdevhw.h",
    "hw/xfree86/i2c/i2c_def.h",
    "hw/xfree86/i2c/xf86i2c.h",
    "hw/xfree86/int10/vbe.h",
    "hw/xfree86/int10/vbeModes.h",
    "hw/xfree86/int10/xf86int10.h",
    "hw/xfree86/modes/xf86Crtc.h",
    "hw/xfree86/modes/xf86Modes.h",
    "hw/xfree86/modes/xf86RandR12.h",
    "hw/xfree86/os-support/bus/xf86Pci.h",
    "hw/xfree86/os-support/bus/xf86Sbus.h",
    "hw/xfree86/os-support/xf86_OSlib.h",
    "hw/xfree86/os-support/xf86_OSproc.h",
    "hw/xfree86/parser/xf86Optrec.h",
    "hw/xfree86/parser/xf86Parser.h",
    "hw/xfree86/ramdac/xf86Cursor.h",
    "hw/xfree86/shadowfb/shadowfb.h",
    "hw/xfree86/vgahw/vgaHW.h",
    "include/XIstubs.h",
    "include/Xprintf.h",
    "include/callback.h",
    "include/client.h",
    "include/closestr.h",
    "include/closure.h",
    "include/colormap.h",
    "include/colormapst.h",
    "include/cursor.h",
    "include/cursorstr.h",
    "include/displaymode.h",
    "include/dix.h",
    "include/dixaccess.h",
    "include/dixevents.h",
    "include/dixfont.h",
    "include/dixfontstr.h",
    "include/dixgrabs.h",
    "include/dixstruct.h",
    "include/events.h",
    "include/exevents.h",
    "include/extension.h",
    "include/extinit.h",
    "include/extnsionst.h",
    "include/fourcc.h",
    "include/gc.h",
    "include/gcstruct.h",
    "include/globals.h",
    "include/hotplug.h",
    "include/input.h",
    "include/inputstr.h",
    "include/list.h",
    "include/misc.h",
    "include/miscstruct.h",
    "include/nonsdk_extinit.h",
    "include/opaque.h",
    "include/optionstr.h",
    "include/os.h",
    "include/pixmap.h",
    "include/pixmapstr.h",
    "include/privates.h",
    "include/property.h",
    "include/propertyst.h",
    "include/ptrveloc.h",
    "include/region.h",
    "include/regionstr.h",
    "include/registry.h",
    "include/resource.h",
    "include/rgb.h",
    "include/screenint.h",
    "include/scrnintstr.h",
    "include/selection.h",
    "include/servermd.h",
    "include/validate.h",
    "include/window.h",
    "include/windowstr.h",
    "include/xkbfile.h",
    "include/xkbrules.h",
    "include/xkbsrv.h",
    "include/xkbstr.h",
    "include/xserver-properties.h",
    "include/xserver_poll.h",
    "mi/mi.h",
    "mi/micmap.h",
    "mi/micoord.h",
    "mi/migc.h",
    "mi/miline.h",
    "mi/mioverlay.h",
    "mi/mipointer.h",
    "mi/mipointrst.h",
    "mi/mistruct.h",
    "mi/mizerarc.h",
    "miext/damage/damage.h",
    "miext/damage/damagestr.h",
    "miext/shadow/shadow.h",
    "miext/sync/misync.h",
    "miext/sync/misyncfd.h",
    "miext/sync/misyncshm.h",
    "miext/sync/misyncstr.h",
    "present/present.h",
    "present/presentext.h",
    "randr/randrstr.h",
    "randr/rrtransform.h",
    "render/glyphstr.h",
    "render/mipict.h",
    "render/picture.h",
    "render/picturestr.h",
)

# The generated xorg-server.h needs these defines completed for an SDK that
# targets the Xorg DDX: the autotools configure only AC_DEFINEs them inside
# the "XORG enabled" section, while meson sets them for the SDK regardless
# (include/meson.build: conf_data.set('XORG_VERSION_CURRENT', release), ...
# xorg_data for the xorg DDX).  Values match the pinned 21.1.15 tarball.
XORG_SERVER_H_DEFINES = {
    "/* #undef XORGSERVER */":
        "#define XORGSERVER 1",
    "/* #undef XORG_VERSION_CURRENT */":
        "#define XORG_VERSION_CURRENT ((10000000) + (21 * 100000) "
        "+ (1 * 1000) + 15)",
    "/* #undef XSERVER_LIBPCIACCESS */":
        "#define XSERVER_LIBPCIACCESS 1",
    "/* #undef XCONFIGFILE */":
        '#define XCONFIGFILE "xorg.conf"',
    "/* #undef __XSERVERNAME__ */":
        '#define __XSERVERNAME__ "Xorg"',
}


class Xf86VideoAtiConan(ConanFile):
    name = "xf86-video-ati"
    version = "22.0.0"
    description = "X.Org video driver for ATI/Radeon graphics hardware"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/driver/xf86-video-ati"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # --- direct driver dependencies (link/run time) ---
        # DRM userspace library (>= 2.4.89).  2.4.133 is the published
        # registry version; the driver links libdrm + libdrm_radeon.
        self.requires("libdrm/2.4.133")
        # PCI bus access library (configure: pciaccess >= 0.8.0)
        self.requires("libpciaccess/0.19")
        # Pixel machinery — the X server SDK headers (compiler.h) include
        # <pixman.h>, so the include path must be available at build time
        self.requires("pixman/0.46.4.3")
        # X.Org protocol headers (xproto, fontsproto, xf86driproto,
        # randrproto, renderproto, videoproto, xextproto, dri2proto, ...)
        self.requires("xorgproto/2025.1")
        # --- xorg-server SDK configure inputs (build time only; see
        # _setup_xorg_sdk — nothing from these packages is linked into or
        # packaged with the driver modules) ---
        # unconditional REQUIRED_LIBS/REQUIRED_MODULES entries of the
        # xorg-server configure (XSERVERCFLAGS/XSERVERLIBS check)
        self.requires("xtrans/1.6.0")
        self.requires("libxau/1.0.11")
        self.requires("libxkbfile/1.1.3")
        self.requires("libxshmfence/1.3.3")
        # SHA1 implementation for the xorg-server configure
        # (--with-sha1=libnettle; Xauth support of the server, build-time
        # link test only)
        self.requires("nettle/3.10.2.1")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xf86-video-ati is only supported on Linux/OHOS, "
                "not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------
    # xorg-server SDK generation
    # ------------------------------------------------------------------

    def _sdk_dir(self):
        return os.path.join(self.build_folder, "xorg-sdk")

    def _patch_xserver_platform_files(self, xsrc):
        """HarmonyOS triplet + HMDFS umask fixes for the xorg-server tree
        (same edits as the driver's own patches 0001-0003, applied in-recipe
        because the xorg-server tarball is a transient build input)."""
        # E007: config.guess — uname -s returns HarmonyOS
        cg_path = os.path.join(xsrc, "config.guess")
        cg = load(self, cg_path)
        if "HarmonyOS" not in cg:
            anchor = ("case "
                      "$UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:"
                      "$UNAME_VERSION in\n")
            block = anchor + (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)          MACHINE=i686 ;;\n"
                "\t    *)             MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n"
                "\n"
            )
            if anchor not in cg:
                raise ConanInvalidConfiguration(
                    "config.guess anchor not found in xorg-server tarball")
            save(self, cg_path, cg.replace(anchor, block, 1))

        # E007: config.sub — ohos-linux triplet + ohos* OS family +
        # linux-ohos kernel-OS combination
        cs_path = os.path.join(xsrc, "config.sub")
        cs = load(self, cs_path)
        if "ohos" not in cs:
            a1 = ("\t\t\tbasic_machine=$field1-unknown\n"
                  "\t\t\tbasic_os=linux-android\n"
                  "\t\t\t;;")
            n1 = (a1 +
                  "\n\tohos-linux)\n"
                  "\t\t\tbasic_machine=$field1-unknown\n"
                  "\t\t\tbasic_os=linux-ohos\n"
                  "\t\t\t;;")
            a2 = "gnu* | android* | bsd*"
            n2 = "gnu* | android* | ohos* | bsd*"
            a3 = "| linux-musl* | linux-relibc*"
            n3 = "| linux-musl* | linux-ohos* | linux-relibc*"
            for old, new in ((a1, n1), (a2, n2), (a3, n3)):
                if old not in cs:
                    raise ConanInvalidConfiguration(
                        "config.sub anchor not found in xorg-server tarball")
                cs = cs.replace(old, new, 1)
            save(self, cs_path, cs)

        # E011: configure — the umask 077 temp dir is unwritable on HMDFS
        cf_path = os.path.join(xsrc, "configure")
        cf = load(self, cf_path)
        cf = cf.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(mktemp -d "./confXXXXXX") 2>/dev/null`')
        cf = cf.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
        save(self, cf_path, cf)

    def _write_cpp_wrapper(self, tools_dir):
        """`cpp` wrapper: OHOS clang does not read stdin implicitly, which
        breaks the XORG_PROG_RAWCPP probes of the xorg-server configure
        (`${RAWCPP} < conftest.c`)."""
        save(self, os.path.join(tools_dir, "cpp"),
             "#!/bin/sh\n"
             "# cpp wrapper for OHOS clang: plain 'clang -E' refuses to\n"
             "# read stdin ('no input files'); add an explicit '-' input\n"
             "# so stdin redirections work.\n"
             "exec \"${CC:-clang}\" -E -x c - \"$@\"\n")
        os.chmod(os.path.join(tools_dir, "cpp"), 0o755)

    def _setup_xorg_sdk(self):
        """Generate the xorg-server SDK (headers + xorg-server.pc value
        targets) from the official tarball, in the build folder."""
        xdata = self.conan_data["xorg_server"]
        xsrc = os.path.join(self.build_folder, "xorg-server-src")
        xbuild = os.path.join(self.build_folder, "xorg-server-build")
        tools_dir = os.path.join(self.build_folder, "ohos-tools")
        sdk_inc = os.path.join(self._sdk_dir(), "include", "xorg")

        get(self, url=xdata["url"], sha256=xdata["sha256"],
            strip_root=True, destination=xsrc)
        self._patch_xserver_platform_files(xsrc)
        self._write_cpp_wrapper(tools_dir)
        os.makedirs(xbuild, exist_ok=True)

        # SHA1 link test of AC_CHECK_LIB needs the nettle library path.
        nettle = self.dependencies["nettle"]
        nettle_lib = os.path.join(nettle.package_folder,
                                  nettle.cpp_info.libdirs[0])
        # The `cpp` wrapper must be found by AC_PATH_TOOL(RAWCPP, [cpp]).
        env_prefix = 'PATH="{}:$PATH" LDFLAGS="$LDFLAGS -L{}"'.format(
            tools_dir, nettle_lib)
        configure_cmd = (
            'cd "{xbuild}" && {env} "{xsrc}/configure" '
            '--prefix="{prefix}" '
            # every DDX disabled: no libxfont2/xkbcomp/xorg build needed,
            # only the config-header generation of config.status
            '--disable-xorg --disable-xvfb --disable-xnest '
            '--disable-xwin --disable-xephyr --disable-kdrive '
            # no GL stack on OHOS; DRI1 was removed upstream in the 21.1
            # series (deprecated hw/xfree86/dri still honours --disable-dri)
            '--disable-glx --disable-dri '
            '--disable-libunwind '
            # SHA1 provider for the Xauth check (see requirements())
            '--with-sha1=libnettle'
        ).format(xbuild=xbuild, env=env_prefix, xsrc=xsrc,
                 prefix=os.path.join(self.build_folder, "xorg-sdk-prefix"))
        self.run(configure_cmd, env="conanbuild")

        # E011 defensive fix: config.status embeds the same umask pattern;
        # if configure could not complete its config.status run on HMDFS,
        # patch and re-run it (same handling as the driver build below).
        gen_hdr = os.path.join(xbuild, "include", "xorg-server.h")
        if not os.path.exists(gen_hdr):
            self._fix_config_status(xbuild)
            self.run('cd "{}" && bash config.status'.format(xbuild),
                     env="conanbuild")
        if not os.path.exists(gen_hdr):
            raise ConanInvalidConfiguration(
                "xorg-server SDK configure did not generate xorg-server.h")

        # Assemble the SDK: static header set (meson install_data list,
        # flattened to basenames) + the generated xorg-server.h with the
        # XORG-DDX defines completed.
        os.makedirs(sdk_inc, exist_ok=True)
        for rel in XORG_SDK_HEADERS:
            shutil.copy2(os.path.join(xsrc, rel),
                         os.path.join(sdk_inc, os.path.basename(rel)))
        xsh = load(self, gen_hdr)
        for old, new in XORG_SERVER_H_DEFINES.items():
            if old not in xsh:
                raise ConanInvalidConfiguration(
                    "xorg-server.h template marker missing: " + old)
            xsh = xsh.replace(old, new)
        save(self, os.path.join(sdk_inc, "xorg-server.h"), xsh)

        # gbm.h stub: radeon_dri3.c unconditionally includes <gbm.h> when
        # dri3.h is present; with glamor disabled no gbm symbol is
        # referenced or linked (all uses are USE_GLAMOR-guarded).
        save(self, os.path.join(sdk_inc, "gbm.h"),
             "/*\n"
             " * Minimal gbm.h build stub for platforms without mesa's\n"
             " * gbm.  xf86-video-ati's radeon_dri3.c includes <gbm.h>\n"
             " * when the xorg-server SDK provides dri3.h (HAVE_DRI3_H);\n"
             " * every gbm API call in the driver is guarded by\n"
             " * USE_GLAMOR, which is disabled here, so no gbm symbol is\n"
             " * referenced or linked — the include is the only use.\n"
             " */\n"
             "#ifndef _GBM_STUB_H_\n"
             "#define _GBM_STUB_H_\n"
             "\n"
             "struct gbm_device;\n"
             "struct gbm_bo;\n"
             "\n"
             "#endif\n")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # glamor acceleration needs pkg-config "gbm" (mesa) — unavailable on
        # OHOS; disabling it keeps the EXA/KMS paths and avoids the hard
        # configure failure.
        tc.configure_args.append("--disable-glamor")
        # Driver modules are always shared objects; no static archives.
        tc.configure_args.append("--disable-static")
        # The X server SDK headers #include <pixman.h>; pixman's include
        # path is not carried by any pkg-config module the driver queries.
        pixman = self.dependencies["pixman"]
        for incdir in pixman.cpp_info.includedirs:
            if not os.path.isabs(incdir):
                incdir = os.path.join(pixman.package_folder, incdir)
            if os.path.isdir(incdir):
                tc.extra_cflags.append("-I" + incdir)
        tc.generate()

        # pkg-config modules for the conan dependencies (libdrm, pciaccess,
        # pixman-1; xorgproto additionally exposes its shipped share/pkgconfig
        # .pc files through the build environment)
        PkgConfigDeps(self).generate()

        # conan's libdrm package exports a single merged libdrm.pc, but
        # upstream configure requires the "libdrm_radeon" pkg-config module
        # (used for LIBDRM_RADEON_CFLAGS / radeon_drv_la_LIBADD).  Synthesize
        # the component .pc with the package's real paths.
        libdrm = self.dependencies["libdrm"]
        libdir = os.path.join(libdrm.package_folder, "lib")
        includedir = os.path.join(libdrm.package_folder, "include")
        pc_content = (
            "libdir={}\n"
            "includedir={}\n"
            "\n"
            "Name: libdrm_radeon\n"
            "Description: Userspace interface to kernel DRM services for "
            "radeon (conan libdrm package)\n"
            "Version: {}\n"
            "Libs: -L\"${{libdir}}\" -ldrm_radeon -ldrm -pthread\n"
            "Cflags: -I\"${{includedir}}\" -I\"${{includedir}}/libdrm\" -pthread\n"
        ).format(libdir, includedir, libdrm.ref.version)
        save(self, os.path.join(self.generators_folder, "libdrm_radeon.pc"),
             pc_content)

        # upstream configure queries the "pciaccess" module; the conan
        # package is named libpciaccess (PkgConfigDeps writes
        # libpciaccess.pc).  Alias with the package's real paths.
        pci = self.dependencies["libpciaccess"]
        save(self, os.path.join(self.generators_folder, "pciaccess.pc"),
             "prefix={}\n"
             "libdir=${{prefix}}/lib\n"
             "includedir=${{prefix}}/include\n"
             "\n"
             "Name: pciaccess\n"
             "Description: Generic PCI access library "
             "(alias of conan libpciaccess)\n"
             "Version: {}\n"
             "Libs: -L\"${{libdir}}\" -lpciaccess\n"
             "Cflags: -I\"${{includedir}}\"\n".format(pci.package_folder,
                                                      pci.ref.version))

        # xorg-server.pc for the in-recipe generated SDK (see
        # _setup_xorg_sdk).  Field values mirror what the meson build
        # writes for an Xorg server (sdkdir pointing at the assembled SDK,
        # module ABI versions from xf86Module.h of the pinned tarball).
        sdk = self._sdk_dir()
        save(self, os.path.join(self.generators_folder, "xorg-server.pc"),
             "prefix={sdk}\n"
             "exec_prefix=${{prefix}}\n"
             "libdir=${{exec_prefix}}/lib\n"
             "includedir=${{prefix}}/include\n"
             "datarootdir=${{prefix}}/share\n"
             "moduledir=${{libdir}}/xorg/modules\n"
             "sdkdir=${{includedir}}/xorg\n"
             "sysconfigdir=${{datarootdir}}/X11/xorg.conf.d\n"
             "\n"
             "abi_ansic={abi_ansic}\n"
             "abi_videodrv={abi_videodrv}\n"
             "abi_xinput={abi_xinput}\n"
             "abi_extension={abi_extension}\n"
             "\n"
             "Name: xorg-server\n"
             "Description: Modular X.Org X Server "
             "(SDK headers generated from the {ver} release tarball)\n"
             "Version: {ver}\n"
             "Requires.private: pixman-1 >= 0.27.2\n"
             "Cflags: -I${{sdkdir}} -fvisibility=hidden\n"
             "Libs:\n".format(sdk=sdk, abi_ansic=XORG_ABI_ANSIC,
                              abi_videodrv=XORG_ABI_VIDEODRV,
                              abi_xinput=XORG_ABI_XINPUT,
                              abi_extension=XORG_ABI_EXTENSION,
                              ver=XORG_SERVER_VERSION))

        # The xorg-server 21.1.15 configure lists "xfont2" unconditionally
        # in REQUIRED_LIBS; a DDX driver SDK never uses xfont2 headers and
        # nothing is built against them — this metadata-only pc satisfies
        # the pkg-config resolution of the SDK configure run.
        save(self, os.path.join(self.generators_folder, "xfont2.pc"),
             "prefix={sdk}\n"
             "Name: xfont2\n"
             "Description: X font library (metadata-only stub for the\n"
             " xorg-server SDK configure; not packaged, nothing links it)\n"
             "Version: 2.0.0\n"
             "Cflags:\n"
             "Libs:\n".format(sdk=sdk))

    def build(self):
        # 1. generate the xorg-server SDK the driver compiles against
        self._setup_xorg_sdk()

        # 2. build the driver against it
        autotools = Autotools(self)
        autotools.configure()
        # E011: config.status (generated file) re-creates its temp dir with
        # `umask 077 && mktemp`, which is unwritable on HMDFS.  Patch it in
        # place; if config.status already failed during configure (Makefile
        # missing), fix and re-run it (same handling as the abook recipe).
        self._fix_config_status(self.build_folder)
        config_status = os.path.join(self.build_folder, "config.status")
        makefile = os.path.join(self.build_folder, "Makefile")
        if os.path.exists(config_status) and not os.path.exists(makefile):
            self.run('cd "' + self.build_folder + '" && bash config.status',
                     env="conanbuild")
        # E074: HMDFS jobserver fifo EPERM — build serially
        autotools.make(args=["-j1"])

    def _fix_config_status(self, build_folder):
        path = os.path.join(build_folder, "config.status")
        if not os.path.exists(path):
            return
        content = load(self, path)
        content = content.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(mktemp -d "./confXXXXXX") 2>/dev/null`')
        content = content.replace('(umask 077 && mkdir "$tmp")',
                                  'mkdir "$tmp"')
        save(self, path, content)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Loadable X server modules — consumers locate them via libdirs;
        # nothing is linked against them (the X server dlopens the modules
        # and provides the server symbols).
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/xorg/modules/drivers"]
        self.cpp_info.includedirs = []
