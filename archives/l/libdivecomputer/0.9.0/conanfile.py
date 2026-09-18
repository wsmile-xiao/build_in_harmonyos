#!/usr/bin/env python3
"""Conan recipe — libdivecomputer 0.9.0 (autotools, libtool).

Cross-platform dive computer support library. Upstream build facts
(verified against the official libdivecomputer-0.9.0.tar.gz,
sha256 a7b80b9083a2113a43280ee7b51d48d66ea5a779fc3fee57df7c451da0251c65):

  * Build system: autotools (configure + libtool LT_INIT), builds
    libdivecomputer.la plus the optional dctool example program
    (--enable-examples, default yes).
  * Transports are compile-time optional and all degrade gracefully:
      - serial  : always on for non-win32 (serial_posix.c, standard POSIX
                  termios; no extra library).
      - usb     : --with-libusb (pkg-config libusb-1.0, HAVE_LIBUSB).
      - usbhid  : --with-hidapi (pkg-config hidapi-libusb or hidapi,
                  HAVE_HIDAPI); falls back to libusb when hidapi is
                  absent and platform != mac (USE_LIBUSB in usbhid.c).
      - irda    : header-probe only (linux/irda.h); naturally absent on
                  OHOS, sources compile to no-ops.
      - bluetooth: --with-bluez (pkg-config bluez, HAVE_BLUEZ); without
                  it bluetooth.c compiles to the unsupported stubs.
      - ble     : transport_ble is hard-coded "no" in 0.9.0 (ble.c is a
                  public API shell without a backend yet).
  * No hardware is required to build: every transport with missing
    dependencies degrades to DC_STATUS_UNSUPPORTED at runtime.
  * Upstream ships zero automated tests (no check target, no tests/
    directory); dctool is a manual tool. Test strategy: test_package
    exercises the hardware-free public API surface (version, context,
    descriptor iterator, parser over a synthetic buffer).

OHOS specifics (aarch64-unknown-linux-ohos):
  * Bundled config.sub (2022-01-03) rejects the ohos triplet:
    "Invalid configuration 'aarch64-unknown-linux-ohos': OS 'ohos' not
    recognized" — patched via patches/0001-config.sub-ohos.patch
    (same root cause and fix shape as the acpid/adplug precedents).
  * OHOS workers run a toybox userland: recipe-side umask fix for
    configure's mktemp temp dir (same as libusb/a52dec) and make -j1
    (R9).
  * Serial transport compiles against <termios.h> only; OHOS musl
    provides it (no TCGETA usage — E565 not applicable).
  * libusb-1.0 (1.0.27) is available in the artifact repo with an
    ohos-aarch64 binary; bluez 5.79 is published but pulls in glib/dbus
    and is a daemon-centric package. Default options keep libusb on
    (real dependency, real backend) and bluez/hidapi off by default,
    each toggleable; with_libusb/with_bluez/with_hidapi are NOT forced
    off, and none of them gate the core library build.
"""

import os
import shlex
import shutil
import struct

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibdivecomputerConan(ConanFile):
    name = "libdivecomputer"
    version = "0.9.0"
    description = "Cross-platform library for communication with dive computers"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.libdivecomputer.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    languages = "C"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libusb": [True, False],
        "with_hidapi": [True, False],
        "with_bluez": [True, False],
        "enable_examples": [True, False],
        "enable_logging": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_libusb": True,
        "with_hidapi": False,
        "with_bluez": False,
        "enable_examples": True,
        "enable_logging": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # hidapi pulls the same libusb backend plus its own OHOS caveats;
        # usbhid falls back to plain libusb when hidapi is absent, so the
        # USBHID transport remains available with with_libusb only.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        if self.options.with_libusb:
            # Published artifact repo package with an ohos-aarch64 binary.
            self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def package_id(self):
        # dctool (examples) is a build-time tool that does not affect the
        # library ABI; keep package ids identical either way.
        del self.info.options.enable_examples

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libdivecomputer recipe supports Linux/OHOS only, got {}".format(
                    self.settings.os))
        if self.options.with_bluez and self.settings.os == "OHOS":
            # bluez 5.79 is published for OHOS, but its OHOS package is
            # daemon/tool-centric (bluetoothd et al.); linking the library
            # into an OHOS app sandbox is not a validated consumer scenario
            # yet. Allow building only for plain Linux until validated.
            raise ConanInvalidConfiguration(
                "with_bluez=True on OHOS is not validated; the bluez OHOS "
                "package ships tools/daemon, use Linux or --without-bluez")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.enable_examples:
            tc.configure_args.append("--enable-examples")
        else:
            tc.configure_args.append("--disable-examples")
        if not self.options.enable_logging:
            tc.configure_args.append("--disable-logging")
        # Doc/mandoc/doxygen never required on build workers.
        tc.configure_args.append("--disable-doc")
        # Transports: never fake detection — pkg-config decides per the
        # generated PkgConfigDeps files; --without-* only when the option
        # is explicitly off. irda is a header probe that degrades to a
        # no-op; pty (ENABLE_PTY) defaults off upstream and stays off.
        tc.configure_args.append(
            "--with-libusb" if self.options.with_libusb else "--without-libusb")
        if self.options.with_hidapi:
            # AC_ARG_WITH default is the module name "hidapi"; the repo
            # package is hidapi/libhidapi. Keep the plain module name and
            # let PKG_CONFIG_PATH resolve it.
            tc.configure_args.append("--with-hidapi")
        else:
            tc.configure_args.append("--without-hidapi")
        tc.configure_args.append(
            "--with-bluez" if self.options.with_bluez else "--without-bluez")
        # Keep `make install` output inside package_folder.
        tc.configure_args.append("--docdir={}".format(
            shlex.quote(os.path.join(self.package_folder, "share", "doc"))))
        tc.generate()
        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        # Patches are applied to the extracted source in the build folder.
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: OHOS worker stability — build serially (make -j1).
        autotools.make(target="all", args=["-j1"])

    def _sign_if_available(self, path):
        """E077: re-sign an ELF after modification (code-sign section).

        Modifying ELF bytes (RUNPATH strip) invalidates the .codesign
        section linked in via -Wl,--code-sign; the loader then rejects
        the library. Re-sign with the repo's binary-sign-tool when
        present. Tool location differs per environment: CI workers have
        /data/service/hnp/bin/binary-sign-tool, dev machines may carry it
        in ~/usr/local/bin or on PATH.
        """
        sign_tool = None
        for cand in ("/data/service/hnp/bin/binary-sign-tool",
                     os.path.expanduser("~/usr/local/bin/binary-sign-tool"),
                     shutil.which("binary-sign-tool")):
            if cand and os.path.isfile(cand):
                sign_tool = cand
                break
        if not sign_tool or not os.path.isfile(path):
            return
        tmp_signed = path + ".signed"
        try:
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    sign_tool, path, tmp_signed),
                quiet=True,
            )
            os.replace(tmp_signed, path)
            os.chmod(path, 0o755)
        except Exception as exc:
            self.output.warning("signing {} failed: {}".format(path, exc))
            try:
                if os.path.isfile(tmp_signed):
                    os.remove(tmp_signed)
            except Exception:
                pass

    def _strip_runpath(self, path):
        """Rewrite DT_RUNPATH/DT_RPATH entries to benign DT_FLAGS(=0).

        Root cause: clang+lld makes libtool fall back to
        hardcode_libdir_flag_spec="-rpath <dir>", so every -L dependency
        dir from PKG_CONFIG_PATH (the ~/.conan2 cache libusb) is embedded
        as RUNPATH in the installed .so. Host cache paths inside a
        packaged library break relocation and fail the ELF gate.
        Replacing the dynamic-table entry with DT_FLAGS(30)=0 is a valid,
        ignored tag (same trick used by patchelf-style tools).
        """
        with open(path, "rb") as f:
            data = bytearray(f.read())
        e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
        e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
        e_phnum = struct.unpack_from("<H", data, 0x38)[0]
        patched = False
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            if struct.unpack_from("<I", data, off)[0] != 2:  # PT_DYNAMIC
                continue
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            for j in range(p_filesz // 16):
                ent = p_offset + j * 16
                tag = struct.unpack_from("<Q", data, ent)[0]
                if tag in (15, 29):  # DT_RPATH, DT_RUNPATH
                    struct.pack_into("<QQ", data, ent, 30, 0)  # DT_FLAGS = 0
                    patched = True
        if patched:
            with open(path, "wb") as f:
                f.write(data)
        return patched

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        # DESTDIR-free install: AutotoolsToolchain already set --prefix to
        # the package folder. Library + headers + pkg-config file via the
        # standard automake targets; dctool only when examples are enabled.
        autotools.install()
        # Prune libtool archives (static/shared layouts differ per consumer).
        for root, _, files in os.walk(self.package_folder):
            for f in files:
                if f.endswith(".la"):
                    os.remove(os.path.join(root, f))
        # Strip host-cache RUNPATH from installed ELFs (shared lib, and
        # the dctool example when enabled — libtool embeds the libusb
        # cache path in both). E077: re-sign after modification since
        # editing the ELF invalidates the .codesign section.
        if self.options.shared:
            for sub in ("lib", "bin"):
                folder = os.path.join(self.package_folder, sub)
                if not os.path.isdir(folder):
                    continue
                for root, _, files in os.walk(folder):
                    for f in files:
                        path = os.path.join(root, f)
                        if not (f.startswith("libdivecomputer.so") or f == "dctool"):
                            continue
                        if self._strip_runpath(path):
                            self.output.info("stripped RUNPATH from {}".format(f))
                            self._sign_if_available(path)
        # --disable-doc installs nothing into share/doc, but the dir may
        # still be created by `make install`; drop it if empty.
        shutil.rmtree(os.path.join(self.package_folder, "share"), ignore_errors=True)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libdivecomputer")
        self.cpp_info.libs = ["divecomputer"]
        self.cpp_info.includedirs = ["include"]
        if self.options.with_libusb:
            self.cpp_info.requires = ["libusb::libusb"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
