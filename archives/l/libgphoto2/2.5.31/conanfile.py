#!/usr/bin/env python3
"""Conan recipe for libgphoto2 2.5.31 — OHOS (OpenHarmony) aarch64 adaptation.

Build system: autotools (configure + make).
Portability patches: config.guess/config.sub for OHOS detection.
Dependencies: libtool (libltdl, required for dlopen-based module loading),
libexif, libjpeg-turbo, libusb.

Upstream design notes (configure.ac):
- LT_INIT([disable-static dlopen]): camlibs/iolibs are dlopen modules and
  only work when built shared ("Disable building static library, as no one
  uses it anyway"). Therefore shared=True is the default here; a static
  build produces a library that cannot load any camera driver at runtime.
- Optional deps are detected via pkg-config, but conan packages ship .pc
  files whose prefix does not match the conan cache layout, so the
  detection flags are passed explicitly via configure variables
  (LIBEXIF_*/LIBJPEG_*/LIBUSB1_*) — a failed detection aborts configure
  instead of silently dropping the feature.
"""
import os
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libgphoto2Conan(ConanFile):
    name = "libgphoto2"
    version = "2.5.31"
    description = "The gphoto2 digital camera library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/gphoto/libgphoto2"
    url = "https://github.com/gphoto/libgphoto2"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libtool/2.5.4.1")  # libltdl: dlopen loader for camlibs/iolibs
        self.requires("libexif/0.6.26.1")  # EXIF thumbnails/mtime in CameraFilesystem
        self.requires("libjpeg-turbo/3.2.0")  # JPEG decoding in ptp2/ax203/jl2005c/sipix camlibs
        self.requires("libusb/1.0.27")  # usb1/usbdiskdirect/usbscsi iolibs
        self.requires("libxml2/2.15.3.1")  # XML support for Olympus E series (ptp2)
        self.requires("curl/8.15.0.1")  # CURL support for Lumix Wifi (ptp2)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            # Upstream LT_INIT([disable-static dlopen]): modules must be shared
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            # Static build cannot dlopen camlibs/iolibs (upstream unsupported)
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-nls")
        # libltdl detection: configure uses LTDLINCL and LIBLTDL variables
        libtool = self.dependencies["libtool"]
        tc.configure_args.append(f"LTDLINCL=-I{libtool.cpp_info.includedir}")
        tc.configure_args.append(f"LIBLTDL=-L{libtool.cpp_info.libdir} -lltdl")
        # Explicit detection flags: dep .pc files have a prefix that does not
        # match the conan cache layout, so pkg-config output is unreliable.
        # GP_CHECK_LIBRARY/GP_LIBJPEG abort configure when explicit vars fail
        # to link — features cannot be silently dropped.
        libexif = self.dependencies["libexif"]
        tc.configure_args.append(f"LIBEXIF_CFLAGS=-I{libexif.cpp_info.includedir}")
        tc.configure_args.append(f"LIBEXIF_LIBS=-L{libexif.cpp_info.libdir} -lexif")
        jpeg = self.dependencies["libjpeg-turbo"]
        tc.configure_args.append(f"LIBJPEG_CFLAGS=-I{jpeg.cpp_info.includedir}")
        tc.configure_args.append(f"LIBJPEG_LIBS=-L{jpeg.cpp_info.libdir} -ljpeg")
        usb = self.dependencies["libusb"]
        usb_inc = os.path.join(usb.package_folder, "include", "libusb-1.0")
        tc.configure_args.append(f"LIBUSB1_CFLAGS=-I{usb_inc}")
        tc.configure_args.append(f"LIBUSB1_LIBS=-L{usb.cpp_info.libdir} -lusb-1.0")
        # libxml2 (Olympus E XML) and libcurl (Lumix Wifi): explicit vars as well.
        # NOTE: deterministic detection matters — GP_CHECK_LIBRARY falls back to
        # legacy *-config programs (e.g. xml2-config) whose failure leaves a
        # literal "*error*" marker in the substituted CFLAGS (upstream
        # gp-check-library.m4 bug), breaking every camlib compile. Explicit
        # vars take the "user-defined" path and skip that autodetection.
        xml2 = self.dependencies["libxml2"]
        xml2_inc = os.path.join(xml2.package_folder, "include", "libxml2")
        tc.configure_args.append(f"LIBXML2_CFLAGS=-I{xml2_inc}")
        tc.configure_args.append(f"LIBXML2_LIBS=-L{xml2.cpp_info.libdir} -lxml2")
        curl_dep = self.dependencies.get("curl")  # curl: Lumix Wifi support (dependency lookup, not a shell command)
        if curl_dep:
            tc.configure_args.append(f"LIBCURL_CFLAGS=-I{curl_dep.cpp_info.includedir}")
            tc.configure_args.append(f"LIBCURL_LIBS=-L{curl_dep.cpp_info.libdir} -lcurl")
        # libGD conversion support: explicitly disabled — the registry's
        # gd/2.3.3.x is built with JPEG/PNG/fontconfig all OFF, so it adds no
        # usable conversion capability here (camlibs use libjpeg directly).
        tc.configure_args.append("--without-gdlib")
        tc.generate()

    def _patch_subdir_configure(self, configure_path):
        """Patch a configure script for HMDFS: TMPDIR + relaxed umask."""
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, 'r') as f:
            content = f.read()
        if 'umask 077 && mktemp -d "./confXXXXXX"' in content:
            content = content.replace(
                'umask 077 && mktemp -d "./confXXXXXX"',
                'umask 000 && mktemp -d "${TMPDIR:-/tmp}/confXXXXXX"'
            )
            content = content.replace(
                'tmp=./conf$$-$RANDOM',
                'tmp=${TMPDIR:-/tmp}/conf$$-$RANDOM'
            )
            content = content.replace(
                'umask 077 && mkdir "$tmp"',
                'umask 000 && mkdir "$tmp"'
            )
            with open(configure_path, 'w') as f:
                f.write(content)

    def _patch_subdir_config_guess(self, guess_path):
        """Patch config.guess for OHOS detection (same changes as root patch)."""
        if not os.path.isfile(guess_path):
            return
        with open(guess_path, 'r') as f:
            content = f.read()
        if '#if defined(__OHOS__)' in content:
            return  # Already patched
        # Add OHOS detection
        content = content.replace(
            '#include <features.h>',
            '#if defined(__OHOS__)\n\tLIBC=ohos\n#else\n#include <features.h>'
        )
        # Add HarmonyOS case before NetBSD
        harmonyos_case = '''    *:HarmonyOS:*:*)
\tcase "$UNAME_MACHINE" in
\t    aarch64|arm64) MACHINE=aarch64 ;;
\t    armv7*|armv8*) MACHINE=arm ;;
\t    x86_64|amd64)  MACHINE=x86_64 ;;
\t    i?86)         MACHINE=i686 ;;
\t    *)            MACHINE="$UNAME_MACHINE" ;;
\tesac
\tGUESS=${MACHINE}-unknown-linux-ohos
\t;;

    *:NetBSD:*:*)'''
        content = content.replace('    *:NetBSD:*:*)', harmonyos_case, 1)
        # Fix the #endif for the OHOS #else
        content = content.replace(
            '#endif\n\tEOF\n\tcc_set_libc',
            '#endif\n\t#endif\n\tEOF\n\tcc_set_libc'
        )
        with open(guess_path, 'w') as f:
            f.write(content)

    def _patch_subdir_config_sub(self, sub_path):
        """Patch config.sub for ohos OS recognition."""
        if not os.path.isfile(sub_path):
            return
        with open(sub_path, 'r') as f:
            content = f.read()
        if 'ohos' in content:
            return  # Already patched
        # Add *-linux-ohos case
        content = content.replace(
            '\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;',
            '\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;\n\t\t\t*-linux-ohos)\n\t\t\t\tbasic_machine=$field1-unknown\n\t\t\t\tbasic_os=linux-ohos\n\t\t\t\t;;'
        )
        # Add ohos* to OS list
        content = content.replace(
            'gnu* | android* | bsd*',
            'gnu* | android* | ohos* | bsd*'
        )
        # Add linux-ohos* to linux patterns
        content = content.replace(
            'linux-android* | linux-newlib*',
            'linux-android* | linux-ohos* | linux-newlib*'
        )
        with open(sub_path, 'w') as f:
            f.write(content)

    def build(self):
        apply_conandata_patches(self)

        # E002: config.status needs a writable TMPDIR for AWK temp files (patched via 0003)
        home_tmp = os.path.join(os.environ.get("HOME", "/tmp"), "tmp")
        os.makedirs(home_tmp, exist_ok=True)
        os.environ["TMPDIR"] = home_tmp

        # Also patch libgphoto2_port subdirectory (same HMDFS/OHOS issues)
        port_dir = os.path.join(self.source_folder, "libgphoto2_port")
        if os.path.isdir(port_dir):
            self._patch_subdir_configure(os.path.join(port_dir, "configure"))
            self._patch_subdir_config_guess(os.path.join(port_dir, "auto-aux", "config.guess"))
            self._patch_subdir_config_sub(os.path.join(port_dir, "auto-aux", "config.sub"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["gphoto2", "gphoto2_port"]
        self.cpp_info.set_property("pkg_config_name", "libgphoto2")
        self.cpp_info.requires = [
            "libtool::libtool",
            "libexif::libexif",
            "libjpeg-turbo::libjpeg-turbo",
            "libusb::libusb",
            "libxml2::libxml2",
            "curl::curl",
        ]
        # Runtime module lookup: libgphoto2 dlopens camlibs/iolibs and falls
        # back to a compile-time default dir (based on configure --prefix)
        # that does not exist in the conan cache layout. Export CAMLIBS/
        # IOLIBS so consumers' conanrun environment points at the real dirs.
        self.runenv_info.define("CAMLIBS", os.path.join(self.package_folder, "lib", "libgphoto2", self.version))
        # iolibs live in a port-versioned subdir (libgphoto2_port/<portver>,
        # e.g. 0.12.2 — versioned independently of libgphoto2)
        port_base = os.path.join(self.package_folder, "lib", "libgphoto2_port")
        iolib_dir = port_base
        if os.path.isdir(port_base):
            subdirs = sorted(d for d in os.listdir(port_base)
                             if os.path.isdir(os.path.join(port_base, d)))
            if subdirs:
                iolib_dir = os.path.join(port_base, subdirs[0])
        self.runenv_info.define("IOLIBS", iolib_dir)
