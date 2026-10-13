#!/usr/bin/env python3
"""Conan recipe for pd-flext 0.6.4 - the flext C++ layer for Pd externals.

flext is a C++ framework that Pure Data (Pd) and Max/MSP externals are written
against.  Upstream builds it either through autotools (the tarball ships only
``configure.ac``, no generated ``configure``) or through its own shell build
system (``build.sh pd gcc``).  Both drive a GNU toolchain and expect a Pd
source tree ("sdkdir") to pull the Pd API headers from.

For OHOS this recipe compiles the flext core directly into the shared
framework library ``libflext-pd.so`` - the exact translation units listed in
upstream ``source/Makefile.am`` (``SRCS_FLEXT``) - with the compile-time ABI
selectors that upstream's ``pd-flext.pc`` publishes (``-DFLEXT_SYS=2
-DFLEXT_SHARED``) and the export selector ``-DFLEXT_EXPORTS``.  The resulting
library is a *host-loaded* shared object: it has no ``DT_NEEDED`` entry for Pd
(a host executable linked with ``-rdynamic``); its Pd symbols stay undefined
and are bound when the object is loaded into the ``pd`` process.  Consumers
(i.e. flext-based externals) link against this library and must be compiled
with the matching ``-DFLEXT_SHARED`` selector, otherwise the class symbols are
mangled with a different ABI suffix (``flext_base_shared`` vs
``flext_base_single``) and fail to resolve.

Host (Pd) API headers: ``flext.h`` includes ``<m_pd.h>`` and flext also needs
the Pd *internal* headers ``g_canvas.h`` and ``m_imp.h``.  The ``puredata``
Conan package installs them under its package folder but exposes no include
dir (it is an ``application`` and sets ``cpp_info.includedirs = []``), so -
like the pd-maxlib / pd-libdir recipes - this recipe fetches the matching
Pure Data source (0.54-1) and installs the public API headers together with
the package, so downstream externals can compile against it.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# Pure Data source release the puredata/0.54.1 package is built from; used only
# to obtain the Pd API headers (m_pd.h, g_canvas.h, m_imp.h, ...).
PD_SRC_URL = "https://github.com/pure-data/pure-data/archive/refs/tags/0.54-1.tar.gz"
PD_SRC_SHA256 = "19a0e2bfcbb5bad5e6dd016d1cda35464db6de008d1803a14c7e1f1625f31353"

# flext core translation units (source/Makefile.am SRCS_FLEXT).  flstk.cpp and
# flsndobj.cpp are only built when the optional STK / SndObj support is on.
FLEXT_SRCS = [
    "flbase", "flext", "flbuf", "fldsp", "fllib", "flxlet", "flattr",
    "flattr_ed", "flsupport", "flutil", "flthr", "fltimer", "flsimd",
    "flout", "flatom", "flatom_pr", "flatom_part", "flitem", "flmeth",
    "flmsg", "flproxy", "flqueue", "flbind", "flmap",
]

LIB_VERSION = "0.6.4"
SONAME = "libflext-pd.so.0.6"


class PdFlextConan(ConanFile):
    name = "pd-flext"
    version = LIB_VERSION
    description = "flext: C++ layer for Pure Data (Pd) and Max/MSP externals"
    license = "GPL-2.0-or-later"
    homepage = "http://grrrr.org/research/software/flext/"
    url = ""

    package_type = "library"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pd-flext OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        pd_dir = os.path.join(self.source_folder, "pd-api")
        os.makedirs(pd_dir, exist_ok=True)
        get(self, url=PD_SRC_URL, sha256=PD_SRC_SHA256,
            filename="pure-data-0.54-1.tar.gz", strip_root=True,
            destination=pd_dir)

    def _compiler(self, name, fallback):
        exe = self.conf.get("tools.build:compiler_executables",
                            default={}, check_type=dict) or {}
        return exe.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cxx = self._compiler("cpp", "clang++")
        src = os.path.join(self.source_folder, "source")
        pdinc = os.path.join(self.source_folder, "pd-api", "src")
        for header in ("m_pd.h", "g_canvas.h", "m_imp.h"):
            if not os.path.isfile(os.path.join(pdinc, header)):
                raise ConanInvalidConfiguration(
                    "Pd API header not found: " + os.path.join(pdinc, header))
        obj = os.path.join(self.build_folder, "obj")
        os.makedirs(obj, exist_ok=True)
        flags = " ".join([
            "-O2", "-fPIC", "-std=c++17",
            "-DFLEXT_SYS=2", "-DFLEXT_SHARED", "-DFLEXT_EXPORTS",
            '-I"%s"' % src, '-I"%s"' % pdinc,
        ])
        objs = []
        for name in FLEXT_SRCS:
            cpp = os.path.join(src, name + ".cpp")
            if not os.path.isfile(cpp):
                raise ConanInvalidConfiguration("missing source " + cpp)
            out = os.path.join(obj, name + ".o")
            self.run('"%s" %s -c "%s" -o "%s"' % (cxx, flags, cpp, out),
                     env="conanbuild")
            objs.append(out)
        real = os.path.join(obj, "libflext-pd.so." + LIB_VERSION)
        self.run('"%s" -shared -Wl,-soname,%s -o "%s" %s -lpthread'
                 % (cxx, SONAME, real, " ".join('"%s"' % o for o in objs)),
                 env="conanbuild")
        if not os.path.isfile(real):
            raise ConanInvalidConfiguration("framework library not produced")

    def package(self):
        src = os.path.join(self.source_folder, "source")
        inc_flext = os.path.join(self.package_folder, "include", "flext")
        copy(self, "*.h", src=src, dst=inc_flext)
        copy(self, "*.cpp", src=src, dst=inc_flext)
        copy(self, "*.hpp", src=os.path.join(src, "lockfree"),
             dst=os.path.join(inc_flext, "lockfree"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "pd-api", "src"),
             dst=os.path.join(self.package_folder, "include", "puredata"))

        libdir = os.path.join(self.package_folder, "lib")
        os.makedirs(libdir, exist_ok=True)
        real = os.path.join(self.build_folder, "obj",
                            "libflext-pd.so." + LIB_VERSION)
        # Ship the versioned object and two aliases as plain files; OHOS/HMDFS
        # materialises symlinks through a mode-projecting layer, so a real copy
        # keeps the dev link (libflext-pd.so) and the runtime soname
        # (libflext-pd.so.0.6) robust.
        for alias in ("libflext-pd.so." + LIB_VERSION, SONAME, "libflext-pd.so"):
            shutil.copyfile(real, os.path.join(libdir, alias))

        pcdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        with open(os.path.join(pcdir, "pd-flext.pc"), "w", encoding="utf-8") as f:
            f.write(
                "prefix=${pcfiledir}/../..\n"
                "exec_prefix=${prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include/flext\n"
                "pdincdir=${prefix}/include/puredata\n\n"
                "Name: pd-flext\n"
                "Description: flext: C++ layer for Pure Data (Pd) externals\n"
                "Version: " + LIB_VERSION + "\n"
                "Cflags: -I${includedir} -I${pdincdir} "
                "-DFLEXT_SYS=2 -DFLEXT_SHARED -pthread\n"
                "Libs: -L${libdir} -lflext-pd -pthread\n")

        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include/flext", "include/puredata"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["flext-pd"]
        self.cpp_info.cxxflags = ["-DFLEXT_SYS=2", "-DFLEXT_SHARED", "-pthread"]
        self.cpp_info.system_libs = ["pthread"]
