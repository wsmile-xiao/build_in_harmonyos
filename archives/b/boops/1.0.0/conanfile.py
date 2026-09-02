#!/usr/bin/env python3
"""Conan recipe for boops 1.0.0 — LV2 glitch effect sequencer plugin.

BOops is an LV2 glitch effect sequencer plugin by sjaehn.
Upstream uses a plain Makefile (make + pkg-config) producing two
shared objects: BOops.so (DSP) and BOopsGUI.so (GUI, X11/cairo).
On OHOS the X11 GUI is not needed; this recipe builds the DSP
bundle only (BOops.lv2) via the upstream Makefile, keeping the
LV2 TTL metadata and pkg-config based dependency resolution.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class BoopsConan(ConanFile):
    name = "boops"
    version = "1.0.0"
    description = "BOops - glitch effect sequencer LV2 plugin"
    license = "GPL-3.0-only"
    homepage = "https://github.com/sjaehn/BOops"
    url = "https://github.com/sjaehn/BOops"
    topics = ("lv2", "audio", "plugin", "glitch", "sequencer")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("lv2/1.18.11-git")
        self.requires("libsndfile/1.2.2")

    def configure(self):
        for opt, val in (("with_external_libs", False), ("with_mpeg", False), ("programs", False)):
            try:
                setattr(self.options["libsndfile"], opt, val)
            except Exception:
                pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Generate pkg-config files for sndfile/lv2 so Makefile's pkg-config can find them
        # (libsndfile's package removes lib/pkgconfig, but its cpp_info.pkg_config_name
        # lets PkgConfigDeps generate a virtual .pc in generators_folder)
        pkg = PkgConfigDeps(self)
        pkg.generate()
        env = Environment()
        # E002: /tmp is read-only erofs on OHOS — use HMBS injected writable TMPDIR
        # HMBS guarantees TMPDIR/TMP/TEMP are injected; fallback to build_folder/tmp for local.
        tmp_base = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        try:
            os.makedirs(tmp_base, exist_ok=True)
        except OSError:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.define(var, tmp_base)
        env.vars(self).save_script("conanbuild_env")
        VirtualRunEnv(self).generate()

    def _pkg_config_paths(self):
        # Collect PKG_CONFIG_PATH entries: generators_folder (PkgConfigDeps) + deps' pkgconfig dirs
        paths = []
        # 1) PkgConfigDeps output — generators_folder is the canonical location in Conan 2
        gen = getattr(self, "generators_folder", None)
        if gen and os.path.isdir(gen):
            try:
                if any(f.endswith(".pc") for f in os.listdir(gen)):
                    paths.append(gen)
                else:
                    paths.append(gen)
            except OSError:
                paths.append(gen)
        # also consider build_folder as fallback (local conan create may place files there)
        for cand in (self.build_folder, getattr(self, "base_build_folder", None)):
            if cand and cand != gen and os.path.isdir(cand):
                try:
                    if any(f.endswith(".pc") for f in os.listdir(cand)):
                        if cand not in paths:
                            paths.append(cand)
                except OSError:
                    pass
        # 2) Per-dependency lib/pkgconfig (e.g. lv2 provides lib/pkgconfig/lv2.pc)
        for dep in self.dependencies.values():
            try:
                pkg_folder = dep.package_folder
            except Exception:
                continue
            if not pkg_folder:
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                d = os.path.join(pkg_folder, sub)
                if os.path.isdir(d) and d not in paths:
                    paths.append(d)
        return paths

    def _create_lv2_compat_symlinks(self):
        try:
            dep = self.dependencies["lv2"]
            pkg_folder = dep.package_folder
        except (KeyError, AttributeError):
            return
        if not pkg_folder:
            return
        lv2_inc = os.path.join(pkg_folder, "include", "lv2")
        if not os.path.exists(os.path.join(lv2_inc, "core", "lv2.h")):
            return
        compat_base = os.path.join(lv2_inc, "lv2plug.in", "ns")
        os.makedirs(compat_base, exist_ok=True)
        link = os.path.join(compat_base, "lv2core")
        if not os.path.exists(link):
            try:
                os.symlink("../../core", link)
            except OSError:
                pass
        link = os.path.join(compat_base, "ext")
        if not os.path.exists(link):
            try:
                os.symlink("../..", link)
            except OSError:
                pass
        ext_dir = os.path.join(compat_base, "extensions")
        os.makedirs(ext_dir, exist_ok=True)
        link = os.path.join(ext_dir, "ui")
        if not os.path.exists(link):
            try:
                os.symlink("../../../ui", link)
            except OSError:
                pass

    def _ensure_lld_dependencies(self, cc):
        if self.settings.os != "OHOS":
            return
        cc_bin = os.path.dirname(os.path.realpath(cc)) if os.path.exists(cc) else ""
        candidate_dirs = []
        if cc_bin:
            candidate_dirs.append(os.path.join(cc_bin, "..", "lib"))
        candidate_dirs.append("/data/service/hnp/lib")
        candidate_dirs.extend(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        lib_dirs = []
        for d in candidate_dirs:
            d = os.path.normpath(d)
            if d in lib_dirs or not os.path.isdir(d):
                continue
            if glob.glob(os.path.join(d, "libxml2.so*")):
                lib_dirs.insert(0, d)
            else:
                lib_dirs.append(d)
        if not lib_dirs:
            return
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(lib_dirs) + (f":{existing}" if existing else "")
        self.output.info(f"LD_LIBRARY_PATH set for lld dependencies: {os.environ['LD_LIBRARY_PATH']}")

    def build(self):
        apply_conandata_patches(self)
        # OHOS DSP-only: remove x11/cairo checks from Makefile (GUI not built)
        # Makefile evaluates ifeq at parse time, so even `make BOops.so` fails without this.
        # Patch in-place instead of conandata patch to avoid strict patch validation issues
        # (Conan patch apply reports "source file is different - b'makefile'" on some lines).
        for mf_name in ("makefile", "Makefile"):
            mf = os.path.join(self.source_folder, mf_name)
            if os.path.isfile(mf):
                try:
                    txt = open(mf, "r", encoding="utf-8", errors="ignore").read()
                    orig = txt
                    # Remove x11 and cairo ifeq blocks (3 lines each: ifeq, $(error, endif)
                    txt = re.sub(r"ifeq\s*\(\$\(shell\s*\$\(PKG_CONFIG\)\s*--exists\s*'x11[^']*'[^\n]*\n\s*\$\(error[^\n]*\nendif\n", "", txt)
                    txt = re.sub(r"ifeq\s*\(\$\(shell\s*\$\(PKG_CONFIG\)\s*--exists\s*'cairo[^']*'[^\n]*\n\s*\$\(error[^\n]*\nendif\n", "", txt)
                    if txt != orig:
                        open(mf, "w", encoding="utf-8").write(txt)
                        self.output.info(f"Patched {mf} to skip GUI deps check (x11/cairo)")
                except Exception as e:
                    self.output.warning(f"Failed to patch {mf}: {e}")
                break
        self._create_lv2_compat_symlinks()
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")
        self._ensure_lld_dependencies(cc)
        pc_paths = self._pkg_config_paths()
        pc_value = os.pathsep.join(pc_paths) if pc_paths else ""
        if pc_value:
            self.output.info(f"PKG_CONFIG_PATH for boops: {pc_value}")
            build_cmd = (
                f'export PKG_CONFIG_PATH=\"{pc_value}:$PKG_CONFIG_PATH\"; '
                f'make -C {self.source_folder} -j1 CC=\"{cc}\" CXX=\"{cxx}\" AR=\"{ar}\" BOops.so'
            )
        else:
            build_cmd = f'make -C {self.source_folder} -j1 CC=\"{cc}\" CXX=\"{cxx}\" AR=\"{ar}\" BOops.so'
        self.run(build_cmd, env="conanbuild")
        bundle_src = os.path.join(self.source_folder, "BOops.lv2")
        if not os.path.isdir(bundle_src):
            os.makedirs(bundle_src, exist_ok=True)
        for ttl in ("manifest.ttl", "BOops.ttl"):
            src_ttl = os.path.join(self.source_folder, ttl)
            dst_ttl = os.path.join(bundle_src, ttl)
            if os.path.isfile(src_ttl) and not os.path.isfile(dst_ttl):
                shutil.copy2(src_ttl, dst_ttl)
        if os.path.isfile(os.path.join(self.source_folder, "LICENSE")):
            dst_lic = os.path.join(bundle_src, "LICENSE")
            if not os.path.isfile(dst_lic):
                shutil.copy2(os.path.join(self.source_folder, "LICENSE"), dst_lic)
        self.output.info("boops DSP build completed")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder
        bundle_src = os.path.join(src, "BOops.lv2")
        bundle_dst = os.path.join(pkg, "lib", "lv2", "BOops.lv2")
        os.makedirs(bundle_dst, exist_ok=True)
        for so in ("BOops.so", "BOopsGUI.so"):
            s = os.path.join(bundle_src, so)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(bundle_dst, so))
        if not os.path.isfile(os.path.join(bundle_dst, "BOops.so")):
            alt = os.path.join(src, "BOops.so")
            if os.path.isfile(alt):
                shutil.copy2(alt, os.path.join(bundle_dst, "BOops.so"))
        for pattern in ("*.ttl", "LICENSE"):
            copy(self, pattern, src=bundle_src, dst=bundle_dst)
            copy(self, pattern, src=src, dst=bundle_dst)
        inc_src = os.path.join(bundle_src, "inc")
        if os.path.isdir(inc_src):
            copy(self, "*", src=inc_src, dst=os.path.join(bundle_dst, "inc"))
        inc_src2 = os.path.join(src, "inc")
        if os.path.isdir(inc_src2):
            dst_inc = os.path.join(bundle_dst, "inc")
            os.makedirs(dst_inc, exist_ok=True)
            for f in glob.glob(os.path.join(inc_src2, "*")):
                if os.path.isfile(f):
                    if not os.path.exists(os.path.join(dst_inc, os.path.basename(f))):
                        shutil.copy2(f, dst_inc)
        copy(self, "LICENSE", src=src, dst=os.path.join(pkg, "licenses"))
        self.output.info(f"boops installed to {bundle_dst}")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib/lv2"]
