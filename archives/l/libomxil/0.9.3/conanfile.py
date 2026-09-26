#!/usr/bin/env python3
"""Conan recipe — libomxil (Bellagio OpenMAX IL) 0.9.3 for HarmonyOS PC.

Upstream project : libomxil-bellagio — Bellagio open source implementation of
                   the Khronos OpenMAX Integration Layer API
Upstream tarball : libomxil-bellagio_0.9.3.orig.tar.gz (Debian orig tarball,
                   identical to the omxil.sourceforge.net 0.9.3 release)
Adapted target   : os=OHOS, arch=armv8 (aarch64), clang 15

The package delivers the OpenMAX IL core library, the dynamic component
loader plugin, the Bellagio component set, the Khronos IL headers and the
omxregister-bellagio registration tool:

  lib/libomxil-bellagio.so                 IL core (OMX_Init/OMX_GetHandle/…)
  lib/omxloaders/libomxdynamicloader.so    loader plugin, dlopen()ed by the core
  lib/bellagio/*.so                        components (audio effects, clock
                                           source, video scheduler)
  bin/omxregister-bellagio                 component registry generator
  include/OMX_*.h, include/bellagio/*.h    Khronos IL + Bellagio extension headers
  lib/pkgconfig/libomxil-bellagio.pc       pkg-config metadata

Platform notes
--------------
* Bellagio is registry based at run time: omxregister-bellagio scans a
  component directory and writes the registry file ($OMX_BELLAGIO_REGISTRY,
  falling back to ~/.omxregister); OMX_Init() fails with ENOENT when no
  registry exists, so the registration tool ships in bin/ and is exercised
  end to end by test_package.
* The loader plugin directory (${libdir}/omxloaders) and the compiled-in
  component search path are baked into the binaries at configure time; conan's
  package prefix makes both resolve inside the package folder.
* No external build requirements: the core links libc + pthread + dl only
  (pthread/dl are folded into libc on the OHOS musl).
* Six upstream patches, all portability-only:
  - 0001/0002 teach the bundled config.guess/config.sub HarmonyOS/ohos
    (same pair as the libm17n-core recipe).
  - 0003 creates configure's ./confXXXXXX helper directory with umask 022
    instead of 077 (the OHOS worker's HMDFS storage rejects the 0700
    directory).
  - 0004 drops -Werror (clang 15 warns on the 2009-era sources).
  - 0005 makes src/base/rm.h declare its globals as extern with a single
    definition in rm.c — lld defaults to -fno-common and rejects the
    duplicate definitions the old header produced.
  - 0006 gives src/dynamic_loader the same LIBADD the component libraries
    already have, so the loader plugin carries a DT_NEEDED on the IL core
    and RM_Init resolves when the plugin is dlopen()ed.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, rm, rmdir)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibomxilConan(ConanFile):
    name = "libomxil"
    version = "0.9.3"
    description = ("Bellagio OpenMAX Integration Layer implementation "
                   "(IL core, component loader, components and "
                   "omxregister-bellagio) for HarmonyOS PC")
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/omxil/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} is adapted for Linux and OHOS only"
            )

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-dependency-tracking",
            # AC_FUNC_MALLOC / AC_FUNC_REALLOC default to "broken" when their
            # test program cannot be run (cross building), which makes config.h
            # "#define malloc rpl_malloc" and breaks every compilation unit
            # that assigns through the macro — no rpl_malloc is provided
            # upstream.  musl returns a unique pointer for malloc(0) /
            # realloc(p, 0), so the answers are seeded instead of letting the
            # run test decide (same rationale as the libm17n-core recipe).
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
        ])
        if self.options.shared:
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # automake 1.11-era recursive makefiles are not parallel-safe
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

        libdir = os.path.join(self.package_folder, "lib")
        # libtool archives burn the build-time libdir into consumer link
        # lines; conan builds with prefix "/" so they would point at
        # "//lib/lib*.la".
        rm(self, "*.la", libdir, recursive=True)
        # share/doc only carries README/ChangeLog/TODO copies of files that
        # are shipped in the archive itself.
        rmdir(self, os.path.join(self.package_folder, "share"))
        # The upstream top-level Makefile.am bakes $(DESTDIR)$(prefix) into
        # docdir, so automake's "$(DESTDIR)$(docdir)" install rule produces a
        # nested "<pkg>/<pkg>//share/doc" tree whose top-level name is the
        # first path component of the build machine's package folder.  Drop
        # every top-level entry that is not part of the package layout.
        keep = {"bin", "include", "lib"}
        for entry in sorted(os.listdir(self.package_folder)):
            if entry in keep:
                continue
            path = os.path.join(self.package_folder, entry)
            if os.path.isdir(path):
                rmdir(self, path)
                self.output.info(f"package(): removed stray directory "
                                 f"'{entry}' (upstream docdir/DESTDIR bug)")
            elif os.path.isfile(path):
                os.remove(path)
                self.output.info(f"package(): removed stray file '{entry}'")
        # Code signing must be the last step that touches the ELF bytes,
        # because the signature covers them (E135/E077/E489).
        self._sign_elfs()

    def _sign_elfs(self):
        """Code-sign the shipped ELF files when the OHOS tools exist.

        HarmonyOS PC requires executables and dlopen()ed libraries to carry a
        valid signature; the signature is a hash over the file bytes, so it is
        applied after every other packaging step.  Everything that is executed
        or dlopen()ed is signed: the core and component .so files (the
        bellagio/ and omxloaders/ subdirectories included) plus
        bin/omxregister-bellagio.  The tools only exist on the OHOS build
        worker, so this is a no-op on other machines (the device CI signs
        during its own conan create).
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.info("OHOS code-signing tools not present: "
                             "skipping ELF signing")
            return
        bin_dir = os.path.join(self.package_folder, "bin")
        targets = []
        for root, _dirs, files in os.walk(self.package_folder):
            for name in sorted(files):
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                is_shared = name.endswith(".so") or ".so." in name
                is_executable = os.path.dirname(path) == bin_dir
                if is_shared or is_executable:
                    targets.append(path)
        for path in targets:
            self.run(f'{objcopy} --remove-section .codesign "{path}" '
                     f'2>/dev/null || true', ignore_errors=True)
            ret = self.run(f'{signer} sign -inFile "{path}" -outFile "{path}" '
                           f'-selfSign 1', ignore_errors=True)
            if ret != 0:
                self.output.warning(
                    f"binary-sign-tool returned {ret} for {path}")
        self.output.info(f"ELF signing: {len(targets)} file(s) processed")

    def package_info(self):
        self.cpp_info.libs = ["omxil-bellagio"]
        # bin/omxregister-bellagio is the Bellagio deployment tool (R38):
        # it generates the component registry OMX_Init() requires.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libomxil-bellagio")
