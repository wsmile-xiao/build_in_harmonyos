#!/usr/bin/env python3
"""Conan recipe — ArgyllCMS 3.5.0 (argyll-cms)

ArgyllCMS is an ICC compatible colour management system: it ships ~47
command line tools (dispcal/dispwin/dispread, colprof, colverify, targen,
chartread, cctiff, iccdump, icclu/iccgamut, collink, ...) that calibrate
and profile displays, scanners, cameras and printers.

Build system
------------
Upstream uses **Perforce Jam** (`jam -fJambase`) — the release zip ships
`Jambase`/`Jamfile`/`Jamtop` but *not* the jam binary, so the Argyll-flavoured
jam is consumed as a Conan `tool_requires` (registry `jam/ajam-2.5.2-1.3.4`
= FT-Jam 2.5.2 + ArgyllCMS V1.3.3 Jambase, the exact rule set this zip
expects).  `jam install` installs into `$(DESTDIR)$(PREFIX)/bin` and
`$(DESTDIR)$(PREFIX)/ref`.

OHOS / HarmonyOS adaptation (details in notes.md)
-------------------------------------------------
* `Jamtop` locates the X11 headers/libs by globbing fixed FHS paths
  (`/usr/X11R6`, `/usr/include`, `/usr/lib64`, ...) and `EXIT`s when none
  match.  Patch 0001 lets it take both paths from the `X11HDRDIR` /
  `X11LIBDIR` jam variables, which `generate()` fills with the Conan
  dependency include/lib dirs (the recipe writes a `JamExtra` file, the
  hook upstream's own `Jamtop` already provides for exactly this purpose).
* Argyll bundles zlib/jpeg/png/tiff (and axTLS for `ccast`); `BUILTIN_*`
  is forced true so the build never picks up ambient host libraries
  (`Jamtop`'s `CheckForLibrary` probes `/usr/include` + `/usr/lib*`).
* The bundled jpeg/tiff `configure` scripts ship 2008/2011-era
  `config.guess`/`config.sub` that do not know HarmonyOS: patches 0002/0003
  add the `*:HarmonyOS:*:*` branch (E007) and the `linux-ohos` triplet, and
  relax their `.tmp` directory `umask 077` to `022` (E011 — HMDFS UID
  mapping makes 0700 temp dirs unwritable, config.status then dies with
  "can't create ./confXXXXXX/subs1.awk: Permission denied").
* USB instruments need no extra library on this platform: the Linux backend
  (`spectro/usbio_lx.c`) talks to `<linux/usbdevice_fs.h>` directly and the
  OHOS sysroot ships that header.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ArgyllCmsConan(ConanFile):
    name = "argyll-cms"
    version = "3.5.0"
    description = ("ArgyllCMS 3.5.0 — ICC compatible colour management system "
                   "(display/scanner/camera/printer profiling command line suite)")
    license = "AGPL-3.0-or-later"
    homepage = "https://www.argyllcms.com/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"argyll-cms supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Jamtop's GUILINKFLAGS = -lX11 -lXext -lXxf86vm -lXinerama -lXrandr
        # -lXau -lXdmcp -lXss.  Version track = the cmd-pkgs "6.4.0" line
        # (libx11/6.4.0 + libxext/6.4.0) shared with libxi/libxscrnsaver/
        # libxcursor/libxrandr, so the published binaries resolve as-is.
        self.requires("libx11/6.4.0")
        self.requires("libxext/6.4.0")
        self.requires("libxxf86vm/1.1.5")
        self.requires("libxinerama/1.1.6")
        self.requires("libxrandr/1.5.5.1")
        self.requires("libxscrnsaver/1.2.5")
        # -lXau / -lXdmcp are on the GUILINKFLAGS line as well: pin the exact
        # versions libxcb/1.16 already pulls in (libxau/1.0.11, libxdmcp/1.1.5)
        # so their libdirs are always injected and no version conflict arises.
        self.requires("libxau/1.0.11")
        self.requires("libxdmcp/1.1.5")

    def build_requirements(self):
        # Argyll's build tool (Jam + the ArgyllCMS Jambase ruleset).
        self.tool_requires("jam/ajam-2.5.2-1.3.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler executables come from the Conan toolchain conf,
        # never from bare shell environment variables.
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp.get("c") or "clang"
        cxx = comp.get("cpp") or comp.get("cxx") or "clang++"

        incs, libs = [], []
        for dep in self.dependencies.host.values():
            folder = dep.package_folder
            if not folder:
                continue
            info = dep.cpp_info.aggregated_components()
            incs += [os.path.join(folder, d) for d in info.includedirs]
            libs += [os.path.join(folder, d) for d in info.libdirs]

        inc_flags = " ".join(f"-I{d}" for d in incs)
        lib_flags = " ".join(f"-L{d}" for d in libs)
        rpath_flags = " ".join(f"-Wl,-rpath,{d}" for d in libs)

        # Jamtop includes `JamExtra` (top of the source tree) before applying
        # its own defaults, which is upstream's documented override hook.
        # `=` (not `?=`) is required: Jambase has already set CC/C++ to "cc".
        content = f"""# ArgyllCMS build configuration — generated by the Conan recipe.
# Loaded by Jamtop via its `if [ GLOB $(TOP) : JamExtra ] {{ include ... }}` hook.

CC = {cc} ;
C++ = {cxx} ;
AR = ar rusc ;
RANLIB = "" ;

# Use the zlib/jpeg/png/tiff sources shipped inside the ArgyllCMS release
# (Jamtop's CheckForLibrary would otherwise pick up ambient /usr libraries).
BUILTIN_TIFF = true ;
BUILTIN_JPEG = true ;
BUILTIN_PNG = true ;
BUILTIN_Z = true ;
BUILTIN_SSL = true ;

# X11 search paths for the patched Jamtop (see patches/0001).
X11HDRDIR = {" ".join(incs)} ;
X11LIBDIR = {" ".join(libs)} ;

CCFLAGS += {inc_flags} ;
C++FLAGS += {inc_flags} ;
CCFLAGS += -ffile-prefix-map={self.source_folder}=. ;
C++FLAGS += -ffile-prefix-map={self.source_folder}=. ;
LINKFLAGS += {lib_flags} ;
LINKFLAGS += {rpath_flags} ;
"""
        with open(os.path.join(self.source_folder, "JamExtra"), "w") as f:
            f.write(content)

    def _jobs(self):
        jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        if jobs:
            return jobs
        return max(2, min(8, os.cpu_count() or 2))

    def build(self):
        apply_conandata_patches(self)

        # The OHOS device exports a generic toolchain environment
        # (AR=llvm-ar, RANLIB=llvm-ranlib, NM/STRIP/AS/LD=llvm-*, plus
        # CFLAGS/CXXFLAGS/CPPFLAGS/LDFLAGS pointing at the user's
        # ~/usr/local prefix).  Jam imports those names as jam variables and
        # autoconf's bundled jpeg/tiff sub-configures read them too, so
        # `llvm-ar` is invoked without an operation ("llvm-ar: error: unknown
        # option n") and the shared user prefix leaks into every link line
        # (R49/E524).  Drop them — the toolchain is pinned by the Conan conf
        # (CC/C++) and by JamExtra (AR/RANLIB).
        for var in ("AR", "RANLIB", "NM", "STRIP", "AS", "LD",
                    "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS"):
            os.environ.pop(var, None)

        # jam's own actions shell out to the usual POSIX tools (rm/mkdir/cp/
        # sed/awk/ar); keep them reachable even if the worker's PATH is bare
        # (appended, so the Conan tool_requires binaries stay first).
        os.environ["PATH"] = os.pathsep.join(
            p for p in (os.environ.get("PATH", ""), "/usr/bin", "/bin") if p
        )

        self.run(f'jam -fJambase -j{self._jobs()}', cwd=self.source_folder)
        # Installs into <source_folder>/bin and <source_folder>/ref
        # (Jamtop's DESTDIR default is the project root).
        self.run("jam -fJambase install", cwd=self.source_folder)

    def package(self):
        copy(self, "License*.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "bin/*", src=self.source_folder, dst=self.package_folder)
        copy(self, "ref/*", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
