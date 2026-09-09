#!/usr/bin/env python3
"""Conan recipe — AFL++ tools 4.40c (Makefile-based fuzzer suite).

Package name 'afl++-tools' (conan slug allows '+', e.g. vera++) — must match
the archives/a/afl++-tools/ directory name and branch name per CI L0m/L0n.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AflToolsConan(ConanFile):
    name = "afl++-tools"
    version = "4.40c"
    description = (
        "AFL++ is a fast instrumented fuzzer with many enhancements "
        "over the original AFL."
    )
    license = "Apache-2.0"
    homepage = "https://github.com/AFLplusplus/AFLplusplus"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ── core fuzzing tools (Makefile) ───────────────────────────────
    # 4.40c: afl-cmin moved into PROGS (built via "cp -f afl-cmin.py
    # afl-cmin" in GNUmakefile — the C rewrite src/afl-cmin.c is not yet
    # enabled upstream, the shipped artifact is still the Python script).
    PROGS = [
        "afl-fuzz", "afl-showmap", "afl-tmin",
        "afl-gotcpu", "afl-analyze", "afl-cmin",
    ]

    # Shell scripts that ship in the source root (no compilation needed).
    # 4.40c: afl-cmin replaced by afl-cmin.awk in SH_PROGS.
    SH_PROGS = [
        "afl-plot", "afl-cmin.awk", "afl-cmin.bash", "afl-cmin.py",
        "afl-whatsup", "afl-addseeds", "afl-system-config",
        "afl-persistent-config",
    ]
    # afl-wine-trace is Windows-only, excluded.

    # ── LLVM instrumentation mode (GNUmakefile.llvm) ────────────────
    # afl-cc is the compiler wrapper; the .so files are LLVM pass plugins
    # loaded by clang at compile time. OHOS ships LLVM 15.0.4 (clang + dev
    # headers + llvm-config), so these build without adapting LLVM itself.
    # cmplog-routines-pass.so is REQUIRED: afl-cc only sets have_llvm=1
    # when it finds this file (src/afl-cc.c find_object), so omitting it
    # makes every afl-clang-fast invocation abort with "LLVM mode is not
    # available". LTO passes (SanitizerCoverageLTO.so, afl-ld-lto) are
    # excluded — they need LLD, which is optional.
    LLVM_PROGS = [
        "afl-cc",                        # wrapper (creates afl-clang etc.)
        "afl-compiler-rt.o",             # runtime linked into instrumented code
        "SanitizerCoveragePCGUARD.so",   # modern instrumentation pass
        "afl-llvm-pass.so",              # classic instrumentation pass
        "cmplog-routines-pass.so",       # required for have_llvm detection
        "cmplog-instructions-pass.so",   # cmp-log instrumentation
        "cmplog-switches-pass.so",       # cmp-log instrumentation
        "split-compares-pass.so",        # comparison splitting
        "split-switches-pass.so",        # switch splitting
        "compare-transform-pass.so",     # comparison transform
        "afl-llvm-dict2file.so",         # dictionary extraction
        "injection-pass.so",             # input injection
    ]
    # afl-cc dispatches on argv[0]; these symlinks are created by the
    # afl-cc build rule and must be preserved in the package.
    AFL_CC_SYMLINKS = [
        "afl-c++", "afl-gcc", "afl-g++",
        "afl-clang", "afl-clang++",
        "afl-clang-fast", "afl-clang-fast++",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # AFL++ builds in-source (GNUmakefile).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compilers from Conan conf, never from bare shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        # Conan profile uses "cpp" key for the C++ compiler (not "cxx").
        cxx = compilers.get("cxx", compilers.get("cpp", "clang++"))

        # SYS=Linux: OHOS is ABI-compatible but not listed in the Makefile;
        # this ensures Linux linker flags (-ldl -lrt -lm) and -Wl,-znodelete.
        # NO_PYTHON=1: CI has no python3-config to satisfy the Python check.
        # TEST_MMAP=1: OHOS blocks SysV shared memory (shmget -> SIGSYS), so
        # force AFL++'s mmap-based shared memory (-DUSEMMAP=1) instead.
        make_env = (
            ' CC="{}" CXX="{}"'
            " NO_PYTHON=1"
            " TEST_MMAP=1"
            " PREFIX=/"
            " SYS=Linux"
        ).format(cc, cxx)

        # 1. Core fuzzing tools.
        self.run(
            "make -f GNUmakefile -j2 {} {}".format(
                " ".join(self.PROGS), make_env
            )
        )

        # 2. LLVM instrumentation (afl-cc + passes). Non-fatal: if LLVM dev
        # is missing, the core tools above are still built and packaged.
        llvm_config = "llvm-config"
        if os.path.isabs(cc):
            _bin = os.path.dirname(cc)
            _candidate = os.path.join(_bin, "llvm-config")
            if os.path.exists(_candidate):
                llvm_config = _candidate
        self.run(
            "make -f GNUmakefile.llvm -k -j2 {}"
            ' LLVM_CONFIG="{}" {}'.format(
                " ".join(self.LLVM_PROGS), llvm_config, make_env
            ),
            ignore_errors=True,
        )

    def package(self):
        # Manual install — the upstream "make install" tries to install
        # afl-cc (needs LLVM) and fails when it's missing.
        dst_bin = os.path.join(self.package_folder, "bin")
        dst_lib_afl = os.path.join(self.package_folder, "lib", "afl")
        dst_include = os.path.join(self.package_folder, "include", "afl")
        dst_share_afl = os.path.join(self.package_folder, "share", "afl")
        dst_doc = os.path.join(self.package_folder, "share", "doc", "afl")
        dst_man = os.path.join(self.package_folder, "share", "man", "man8")

        for d in (dst_bin, dst_lib_afl, dst_include, dst_share_afl,
                  dst_doc, dst_man):
            os.makedirs(d, exist_ok=True)

        # Core binaries.
        for p in self.PROGS:
            src = os.path.join(self.source_folder, p)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_bin, p))
                os.chmod(os.path.join(dst_bin, p), 0o755)

        # Shell scripts (exist in source root).
        for s in self.SH_PROGS:
            src = os.path.join(self.source_folder, s)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_bin, s))
                os.chmod(os.path.join(dst_bin, s), 0o755)

        # afl-cc wrapper + its dispatch symlinks.
        afl_cc = os.path.join(self.source_folder, "afl-cc")
        if os.path.isfile(afl_cc):
            shutil.copy2(afl_cc, os.path.join(dst_bin, "afl-cc"))
            os.chmod(os.path.join(dst_bin, "afl-cc"), 0o755)
            for s in self.AFL_CC_SYMLINKS:
                dst = os.path.join(dst_bin, s)
                if not os.path.lexists(dst):
                    os.symlink("afl-cc", dst)

        # LLVM pass plugins + runtime object → lib/afl (AFL_PATH).
        for f in os.listdir(self.source_folder):
            if f.endswith(".so") or f.endswith(".o") or f.endswith(".a"):
                fp = os.path.join(self.source_folder, f)
                if os.path.isfile(fp) and not os.path.islink(fp):
                    shutil.copy2(fp, os.path.join(dst_lib_afl, f))

        # Headers.
        headers_dir = os.path.join(self.source_folder, "include")
        if os.path.isdir(headers_dir):
            for h in os.listdir(headers_dir):
                hp = os.path.join(headers_dir, h)
                if os.path.isfile(hp):
                    shutil.copy2(hp, os.path.join(dst_include, h))

        # Testcases + dictionaries (bundled corpus for afl-fuzz).
        for sub in ("testcases", "dictionaries"):
            src_sub = os.path.join(self.source_folder, sub)
            if os.path.isdir(src_sub):
                dst_sub = os.path.join(dst_share_afl, sub)
                if os.path.exists(dst_sub):
                    shutil.rmtree(dst_sub)
                shutil.copytree(src_sub, dst_sub)

        # Injections dictionary.
        inj = os.path.join(self.source_folder, "injections.dic")
        if os.path.isfile(inj):
            shutil.copy2(inj, os.path.join(dst_share_afl, "injections.dic"))

        # Documentation.
        docs_src = os.path.join(self.source_folder, "docs")
        if os.path.isdir(docs_src):
            for f in os.listdir(docs_src):
                fp = os.path.join(docs_src, f)
                if os.path.isfile(fp) and f.endswith(".md"):
                    shutil.copy2(fp, os.path.join(dst_doc, f))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/afl"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        # afl-cc locates its pass plugins + runtime via AFL_PATH.
        self.runenv_info.define("AFL_PATH", os.path.join(
            self.package_folder, "lib", "afl"))
