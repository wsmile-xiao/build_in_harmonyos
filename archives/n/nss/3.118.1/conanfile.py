#!/usr/bin/env python3
"""Conan recipe — NSS 3.118.1 (Mozilla Network Security Services)

Build system: NSS coreconf make (NOT autotools).
- Requires conan nspr/4.37 package for NSPR headers/libs
- tarball is the "with-nspr" bundle: after strip_root it contains nss/ and nspr/
- make runs inside the nss/ subdir; NSPR headers are copied into ../dist/public/nspr
  (the path NSS coreconf searches via REQUIRES=nspr -> -I$(SOURCE_XP_DIR)/public/nspr)
- Only the coreconf + lib dirs are built (cmd tools link runtime-dependent .so and
  are not required for the library package)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class NssConan(ConanFile):
    name = "nss"
    version = "3.118.1"
    description = "Mozilla Network Security Services - crypto, TLS, S/MIME libraries"
    license = "MPL-2.0"
    homepage = "https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("nspr/4.37")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        nss_dir = os.path.join(self.source_folder, "nss")
        dist_dir = os.path.join(self.source_folder, "dist")

        # 1. NSPR headers must live where NSS coreconf looks for them:
        #    -I$(SOURCE_XP_DIR)/public/nspr  ->  <src>/dist/public/nspr
        #    The nspr conan package may lay headers out as include/nspr or include/
        nspr_dep = self.dependencies["nspr"]
        nspr_inc = nspr_dep.cpp_info.includedirs[0]
        nspr_hdr = os.path.join(nspr_inc, "nspr") if os.path.isdir(os.path.join(nspr_inc, "nspr")) else nspr_inc
        dst_inc = os.path.join(dist_dir, "public", "nspr")
        shutil.copytree(nspr_hdr, dst_inc, dirs_exist_ok=True)

        # cmd/ is excluded from DIRS (patch 0004-manifest.mn), so its
        # PRIVATE_EXPORTS headers (secutil.h, basicutil.h, pk11table.h) are
        # not auto-exported to dist/private/nss. lib/pk11wrap includes
        # secutil.h, so copy them.
        cmd_lib = os.path.join(self.source_folder, "nss", "cmd", "lib")
        if os.path.isdir(cmd_lib):
            dst_priv = os.path.join(dist_dir, "private", "nss")
            os.makedirs(dst_priv, exist_ok=True)
            for f in os.listdir(cmd_lib):
                if f.endswith(".h"):
                    shutil.copy2(os.path.join(cmd_lib, f), os.path.join(dst_priv, f))

        # 2. Build libs with coreconf make (skip cmd/gtests via DIRS override)
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("AR", "llvm-ar")
        env.define("RANLIB", "llvm-ranlib")
        env.define("LD", "ld.lld")
        env.define("STRIP", "llvm-strip")
        env.define("NSPR_INCLUDE_DIR", nspr_inc)
        env.define("NSPR_LIB_DIR", nspr_dep.cpp_info.libdirs[0])
        with env.vars(self).apply():
            # Patch 0004 (manifest.mn) trims DIRS to "coreconf lib", so plain
            # `make` builds only the libraries (cmd tools need a working
            # softoken at runtime and are not part of the library package).
            self.run("make BUILD_OPT=1 USE_64=1", cwd=nss_dir)
    def package(self):
        # make runs inside source_folder/nss with CORE_DEPTH=., so NSS writes
        # dist output to source_folder/dist. During package(), source_folder may
        # point at the build copy; try both source and build folders.
        dist = None
        for base in (self.source_folder, self.build_folder):
            cand = os.path.join(base, "dist")
            if os.path.isdir(cand):
                dist = cand
                break
        if dist is None:
            raise ConanException("dist output not found in source/build folders")
        self.output.info("packaging from dist: %s" % dist)
        # libs (all subdirs of dist/<OBJDIR>/lib)
        obj_lib = None
        for root, dirs, files in os.walk(dist):
            if root.endswith(os.sep + "lib") and files:
                obj_lib = root
                break
        if obj_lib:
            self.output.info("copying libs from: %s" % obj_lib)
            lib_dst = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dst, exist_ok=True)
            for f in os.listdir(obj_lib):
                if f.endswith(".a") or f.endswith(".so"):
                    shutil.copy2(os.path.join(obj_lib, f),
                                 os.path.join(lib_dst, f))
        # headers: NSS public headers (nss/ssl/smime/util/dbm/coreconf) are
        # flattened into include/ so consumers can `#include "nss.h"`.
        # NSPR headers must keep their subdir structure (obsolete/, private/,
        # md/) because prtypes.h does `#include "obsolete/protypes.h"` — copy
        # the whole dist/public/nspr tree as-is.
        # dist/public contains symlinks -> resolve them to real files.
        inc_dst = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dst, exist_ok=True)
        pub = os.path.join(dist, "public")
        if os.path.isdir(pub):
            for mod in os.listdir(pub):
                src = os.path.join(pub, mod)
                if not os.path.isdir(src):
                    continue
                if mod == "nspr":
                    # preserve subdirs (obsolete/private/md)
                    for f in os.listdir(src):
                        s = os.path.join(src, f)
                        if os.path.isfile(s):
                            shutil.copy2(s, os.path.join(inc_dst, f))
                        elif os.path.isdir(s):
                            shutil.copytree(s, os.path.join(inc_dst, f),
                                            dirs_exist_ok=True,
                                            symlinks=False)
                else:
                    for f in os.listdir(src):
                        if f.endswith(".h") and os.path.isfile(os.path.join(src, f)):
                            shutil.copy2(os.path.join(src, f),
                                         os.path.join(inc_dst, f))
        for root, dirs, files in os.walk(dist):
            if root.endswith(os.sep + "include") and "public" not in root:
                for f in files:
                    if f.endswith(".h") and os.path.isfile(os.path.join(root, f)):
                        shutil.copy2(os.path.join(root, f),
                                     os.path.join(inc_dst, f))
        # license
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "nss"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # NSS coreconf names libs libnss3.so/libssl3.so (shared) but
        # libnss.a/libssl.a (static). Link order: dependents before dependees.
        if self.options.shared:
            libs = ["nss3", "ssl3", "smime3", "nssutil3", "softokn3",
                    "freebl3", "nssckbi", "nssdbm3", "sqlite3"]
        else:
            libs = ["nss", "ssl", "smime", "nssutil", "softokn",
                    "freebl", "nssckfw", "nssdbm", "sqlite"]
        self.cpp_info.libs = libs
        self.cpp_info.system_libs = ["dl", "pthread", "z"]
        self.cpp_info.requires = ["nspr::nspr"]
