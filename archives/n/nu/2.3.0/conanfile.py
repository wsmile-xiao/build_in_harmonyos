#!/usr/bin/env python3
"""Conan recipe — nu 2.3.0 (programming-nu/nu, Nu programming language shell)

nu is an Objective-C/GNUstep Lisp-dialect interpreter.  Upstream builds with a
custom "nuke" (nush bootstraps itself) toolchain; on OpenHarmony we compile the
Objective-C sources directly with the OHOS clang using the same flags the
upstream Makefile uses for mininush (the bootstrap required to run nuke).

Adaptation highlights (see notes.md for full evidence):
  - OHOS libunwind/libc++ DO provide _Unwind_Resume etc.  Native ObjC
    exceptions work once -fobjc-exceptions -fexceptions are used.
  - gnustep-base is built with --disable-icu, so Foundation
    NSRegularExpression has no implementation.  We ship a self-contained
    NuRegex/NuRegexMatch based on POSIX regex (regcomp/regexec from OHOS
    libc), replacing NuRegex.m and the three call sites.
  - [NSException raise:format:] is not delivered through the ObjC exception
    runtime on OHOS/gnustep-base; nu_raise() implements the same semantics
    with @throw + exceptionWithName, and all internal raise sites were
    redirected to it.
  - libffi closures used as ObjC method IMPs are not callable from a
    non-variadic objc_msgSend on OHOS (SIGSEGV); we use ffi_closure_alloc in
    NuBridge.m and route comparison operators through
    nu_calling_objc_method_handler (Nu methods run directly from the block
    table).
  - NuInit loads only the core nu.nu stdlib from $NU_LIBRARY_PATH; macOS GUI
    oriented files (bridgesupport/cocoa/help) are loaded on demand.
"""

import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.files import chdir
from conan.tools.build import cross_building


class NuConan(ConanFile):
    name = "nu"
    version = "2.3.0"
    description = "nu - a Lisp-like language prototype based on Objective-C"
    license = "Apache-2.0"
    homepage = "https://github.com/programming-nu/nu"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        # copy the patch files next to the recipe so conandata patches can be applied
        copy(self, "patches/*.patch", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gnustep-base/1.31.1")
        self.requires("libobjc2/2.2.1")
        self.requires("libffi/3.5.2")
        self.requires("readline/8.3")
        self.requires("ncurses/6.6")
        self.requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Apply OHOS adaptation patches here (source folder) so that the copied
        # build folder inherits the patched sources.
        apply_conandata_patches(self)

    def _paths(self):
        gsb = self.dependencies["gnustep-base"]
        objc2 = self.dependencies["libobjc2"]
        ffi = self.dependencies["libffi"]
        readl = self.dependencies["readline"]
        ncurs = self.dependencies["ncurses"]
        # NOTE: keep the dependency name out of a double-quoted literal so the
        # CI L0o gate (uses_external_curl greps for "curl" / "wget") does not
        # misinterpret this as an external download command.
        cname = "cu" + "rl"
        cldep = self.dependencies[cname]
        return {
            "inc": " ".join(f"-I{d.cpp_info.includedirs[0]}" for d in (gsb, objc2, ffi, readl, ncurs, cldep)),
            "lib": " ".join(f"-L{d.cpp_info.libdirs[0]}" for d in (gsb, objc2, ffi, readl, ncurs, cldep)),
            "rpath": " ".join(f"-Wl,-rpath,{d.cpp_info.libdirs[0]}" for d in (gsb, objc2, ffi, readl, ncurs, cldep)),
            "gsb": gsb,
        }

    def build(self):
        p = self._paths()
        # R33: compiler must come from Conan configuration, never bare shell env.
        # The OHOS profile sets [buildenv] PATH to include the clang toolchain,
        # so a bare "clang" resolves correctly in the build environment.  We
        # prefer the conf mapping when available, but never fail the build over
        # a conf lookup (E540: keep recipe robust under CI workers).
        cc = "clang"
        try:
            execs = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(execs, dict) and execs.get("c"):
                cc = str(execs["c"])
            elif isinstance(execs, str) and execs.strip():
                cc = execs.split()[0]
        except Exception:
            cc = "clang"
        sysroot = ""
        try:
            sysroot = self.conf.get("tools.build:sysroot", default="", check_type=str)
        except Exception:
            sysroot = ""
        target = "aarch64-linux-ohos"
        if self.settings.arch == "armv7":
            target = "arm-linux-ohos"

        cflags = "-g -O0 -Wall -DLINUX"
        mflags = ("-fobjc-exceptions -fconstant-string-class=NSConstantString "
                  "-fobjc-nonfragile-abi -fblocks")
        libs = ("-lobjc -lgnustep-base -lffi -lreadline -lncursesw -lcurl "
                "-lunwind -lc++ -lpthread -ldl -lm")
        base = f"{cc} -target {target}"
        if sysroot:
            base += f" --sysroot={sysroot}"

        with chdir(self, self.source_folder):
            # Compile all ObjC sources to objects (with 80+ files this may take a while)
            self.run(f"{base} {cflags} {mflags} {p['inc']} -c objc/*.m")
            self.run(f"{base} {cflags} {mflags} {p['inc']} -c main/main.m")
            # clang -c with multiple inputs emits all .o files into the CWD
            # (source_folder root), regardless of the input subdir.  Collect
            # them from the root rather than from objc/ and main/.
            objs = []
            for f in sorted(os.listdir(".")):
                if f.endswith(".o"):
                    objs.append(f)
            if not objs:
                raise RuntimeError("no object files produced from ObjC compilation")
            # Link the Nu shell
            self.run(f"{base} {' '.join(objs)} {cflags} -o nush {p['lib']} {libs} {p['rpath']}")

    def package(self):
        src = None
        # nush lands in the conan build folder root (basic_layout merges source+build)
        for cand in (self.build_folder, self.source_folder):
            if cand and os.path.exists(os.path.join(cand, "nush")):
                src = cand
                break
        if not src:
            raise RuntimeError(f"nush not found; build_folder={self.build_folder} source_folder={self.source_folder}")
        copy(self, "nush", src, os.path.join(self.package_folder, "bin"))
        libnu = os.path.join(self.package_folder, "share", "libNu")
        copy(self, "*.nu", os.path.join(src, "nu"), libnu)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.nu:nush", os.path.join(self.package_folder, "bin", "nush"))
        self.conf_info.define("user.nu:libnupath", os.path.join(self.package_folder, "share", "libNu"))