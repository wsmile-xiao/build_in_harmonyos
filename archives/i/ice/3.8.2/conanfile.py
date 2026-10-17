#!/usr/bin/env python3
"""Conan recipe for ZeroC Ice 3.8.2 (C++ RPC framework) on HarmonyOS PC / OHOS aarch64.

Build: Ice 3.8.2 ships its own Makefile system (no autotools/cmake configure).
  - OHOS clang defines __linux__ but NOT __GLIBC__ (musl libc).
  - make must be invoked with os=Linux explicitly.
  - Third-party deps are injected via MCPP_HOME/ICONV_HOME/EXPAT_HOME/BZ2_HOME/LMDB_HOME
    (include+lib layout expected) plus CXXFLAGS/LDFLAGS for openssl/readline/ncurses.
  - IceGrid/IceStorm parsers use libedit API (#include <editline/readline.h>, -ledit);
    OHOS has no libedit, so patch 0004 adds an editline shim header that maps to GNU
    readline, and build() merges libreadline.a + libncursesw.a into a self-contained
    libedit.a for the -ledit link flag.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class IceConan(ConanFile):
    name = "ice"
    version = "3.8.2"
    description = "ZeroC Ice is a comprehensive RPC framework with support for C++, Java, Python, Ruby, PHP and more"
    license = "GPL-2.0"
    homepage = "https://zeroc.com"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All deps resolved from the local cache / ohpcd registry (OHOS armv8 binaries)
        self.requires("bzip2/1.0.8")
        self.requires("expat/2.8.2.1")
        # Ice's public headers expose openssl/iconv types (Ice/SSL/Config.h → <openssl/...>,
        # Ice/IconvStringConverter.h → <iconv.h>), and the libs are statically merged into
        # libIce.so. Mark transitive_headers so downstream consumers still get the headers.
        self.requires("libiconv/1.17", transitive_headers=True, transitive_libs=True)
        self.requires("lmdb/0.9.35")
        self.requires("mcpp/2.7.2")
        self.requires("openssl/3.5.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("readline/8.3")  # -> ncurses/6.6 (transitive)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ──

    def _dep_pkg(self, name):
        try:
            dep = self.dependencies[name]
        except KeyError:
            raise ConanException(f"missing dependency: {name}")
        if not dep.package_folder:
            raise ConanException(f"dependency {name} has no package folder (binary missing)")
        return dep

    def _dep_cxxflags(self):
        """-I flags for every dependency include dir (absolute)."""
        flags = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if not pf:
                continue
            for d in dep.cpp_info.includedirs:
                # cpp_info.includedirs may already be absolute (OHOS-conan quirk)
                flags.append(f"-I{d if os.path.isabs(d) else f'{pf}/{d}'}")
        return " ".join(flags)

    def _dep_ldflags(self):
        """-L flags for every dependency lib dir + rpath so binaries run from the cache."""
        flags = []
        for dep in self.dependencies.values():
            pf = dep.package_folder
            if not pf:
                continue
            for d in dep.cpp_info.libdirs:
                # cpp_info.libdirs may already be absolute (OHOS-conan quirk)
                dd = d if os.path.isabs(d) else f"{pf}/{d}"
                flags.append(f"-L{dd}")
                flags.append(f"-Wl,-rpath,{dd}")
        return " ".join(flags)

    def _mirror_slice_files(self):
        """Mirror slice definitions the Ice make system resolves under slice/.

        slice2cpp is invoked with -I slice/ and resolves `#include "Metrics.ice"`,
        `"Election.ice"`, `"SubscriberRecord.ice"`, `"LLURecord.ice"` against that
        search root.  Upstream keeps those files at cpp/src/IceStorm/ (Election.ice,
        LLURecord.ice, SubscriberRecord.ice) and slice/IceStorm/Metrics.ice, so an
        unpatched tree fails to resolve the includes.  Copy the canonical upstream
        files to the expected paths at build time instead of shipping a patch that
        re-declares existing upstream files as new.
        """
        src = self.source_folder
        mirrors = [
            ("cpp/src/IceStorm/Election.ice", "slice/IceStorm/Election.ice"),
            ("cpp/src/IceStorm/LLURecord.ice", "slice/IceStorm/LLURecord.ice"),
            ("cpp/src/IceStorm/SubscriberRecord.ice", "slice/IceStorm/SubscriberRecord.ice"),
            ("slice/IceStorm/Metrics.ice", "slice/Metrics.ice"),
        ]
        for canonical, target in mirrors:
            s = os.path.join(src, canonical)
            if not os.path.exists(s):
                raise ConanException(f"cannot mirror slice file: {canonical} not found in source")
            t = os.path.join(src, target)
            os.makedirs(os.path.dirname(t), exist_ok=True)
            shutil.copy2(s, t)

    def _make_readline_shim(self):
        """Merge libreadline.a + libncursesw.a into a self-contained libedit.a.

        The Ice build hardcodes `-ledit` for IceGrid/IceStorm admin tools; GNU
        readline's static archive needs termcap (tget*/tputs) which libncursesw
        provides.  Merging both archives makes `-ledit` resolve everything.
        """
        shim = os.path.join(self.source_folder, "libedit-shim")
        shim_lib = os.path.join(shim, "lib")
        os.makedirs(shim_lib, exist_ok=True)
        if os.path.exists(os.path.join(shim_lib, "libedit.a")):
            return shim_lib

        readline_pkg = self._dep_pkg("readline").package_folder
        ncurses_pkg = self._dep_pkg("ncurses").package_folder
        ra = os.path.join(readline_pkg, "lib", "libreadline.a")
        na = os.path.join(ncurses_pkg, "lib", "libncursesw.a")
        if not os.path.exists(ra):
            raise ConanException(f"libreadline.a not found in readline pkg: {ra}")
        if not os.path.exists(na):
            raise ConanException(f"libncursesw.a not found in ncurses pkg: {na}")

        ar = self.conf.get("tools.build:compiler_executables", {}, check_type=dict).get("ar", "llvm-ar")
        work = os.path.join(self.source_folder, "libedit-shim", "arch")
        os.makedirs(work, exist_ok=True)
        for a in (ra, na):
            self.run(f"{ar} x {a}", cwd=work)
        objs = [o for o in os.listdir(work) if o.endswith(".o")]
        if not objs:
            raise ConanException("no objects extracted for libedit merge")
        self.run(f"{ar} rcs {os.path.join(shim_lib, 'libedit.a')} *.o", cwd=work)
        return shim_lib

    def build(self):
        apply_conandata_patches(self)

        # slice2cpp resolves #include "Metrics.ice"/"Election.ice"/... against -I slice/;
        # mirror the canonical upstream slice files into those paths (patch-free).
        self._mirror_slice_files()

        compilers = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        # self-contained libedit.a (readline + ncursesw) for -ledit
        shim_lib = self._make_readline_shim()

        deps_inc = self._dep_cxxflags()
        deps_ld = self._dep_ldflags()

        cxxflags = f"-fPIC -O2 {deps_inc}"
        ldflags = f"-L{shim_lib} {deps_ld}"

        # Map the Ice "home" variables to the conan dependency package folders
        bz2 = self._dep_pkg("bzip2").package_folder
        expat = self._dep_pkg("expat").package_folder
        iconv = self._dep_pkg("libiconv").package_folder
        lmdb = self._dep_pkg("lmdb").package_folder
        mcpp = self._dep_pkg("mcpp").package_folder

        make_cmd = (
            f"make os=Linux srcs "
            f"CC={cc} CXX={cxx} "
            f"MCPP_HOME={mcpp} ICONV_HOME={iconv} EXPAT_HOME={expat} "
            f"BZ2_HOME={bz2} LMDB_HOME={lmdb} "
            f"CXXFLAGS='{cxxflags}' LDFLAGS='{ldflags}' "
            f"-j1"
        )
        self.run(make_cmd, cwd=os.path.join(self.source_folder, "cpp"))

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # shared libraries + static libs, preserving the lib64 version/symlink layout
        lib_src = os.path.join(src, "cpp", "lib64")
        os.makedirs(os.path.join(pkg, "lib"), exist_ok=True)
        # copy real files; recreate symlinks with their original link targets
        for entry in sorted(os.listdir(lib_src)):
            full = os.path.join(lib_src, entry)
            if os.path.islink(full):
                os.symlink(os.readlink(full), os.path.join(pkg, "lib", entry))
            elif os.path.isfile(full):
                shutil.copy2(full, os.path.join(pkg, "lib", entry))

        # lib64/ symlinks to ../lib so binaries find libs via $ORIGIN/../lib64
        lib64 = os.path.join(pkg, "lib64")
        os.makedirs(lib64, exist_ok=True)
        for entry in os.listdir(os.path.join(pkg, "lib")):
            if entry.startswith("lib"):
                os.symlink(os.path.join("..", "lib", entry), os.path.join(lib64, entry))

        # headers
        copy(self, "*", os.path.join(src, "cpp", "include"), os.path.join(pkg, "include"))

        # executables
        copy(self, "*", os.path.join(src, "cpp", "bin"), os.path.join(pkg, "bin"))

        # config (templates.xml etc.)
        copy(self, "*.xml", os.path.join(src, "cpp", "config"), os.path.join(pkg, "config"))

        # slice definitions
        copy(self, "*", os.path.join(src, "slice"), os.path.join(pkg, "share", "ice", "slice"))

        # license
        copy(self, "LICENSE", src, os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.libs = [
            "IceStormService", "IceStorm", "IceGrid", "Glacier2", "IceBox",
            "IceLocatorDiscovery", "IceDiscovery", "DataStorm", "Ice",
        ]
        self.cpp_info.libs.sort(reverse=True)  # reverse so Ice (core) links last
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # generated/ headers (Ice/Version.h etc.) are emitted into include/generated
        self.cpp_info.includedirs = ["include", "include/generated"]
        self.buildenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))
