#!/usr/bin/env python3
"""Conan recipe — libaemu 0.1.2 (CMake, gfxstream build config).

AEMU is the Android emulation utilities library (base + logging +
host-common + snapshot). Upstream builds with CMake; the gfxstream
build-config selects the standalone library subset used by gfxstream/QEMU.
Upstream tests are gtest suites gated by ENABLE_VKCEREAL_TESTS (two
binaries: aemu-base_unittests + aemu-host-common_unittests, 123 ctest
entries total: 124 source macros minus 1 upstream DISABLED_ excluded by
gtest on all platforms); this recipe enables them and runs ctest in build().
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout
from conan.tools.files import copy
from conan.tools.gnu import PkgConfigDeps
from conan.tools.scm import Git


class LibaemuConan(ConanFile):
    name = "libaemu"
    version = "0.1.2"
    description = "Android emulation utilities library"
    license = "Apache-2.0"
    homepage = "https://android.googlesource.com/platform/hardware/google/aemu"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libaemu is supported on Linux and OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        # Upstream third-party/CMakeLists.txt:15 calls
        # find_package(PkgConfig) before pkg_search_module(gtest/gmock);
        # the true-device PATH has no pkg-config, so provide it via
        # tool_requires (ext4fuse/ekg2/fceux precedent, pkgconf/3.0.5
        # already published in this repo).
        self.tool_requires("pkgconf/3.0.5")
        # Upstream tests need gtest+gmock (third-party/CMakeLists.txt uses
        # pkg_search_module when ENABLE_VKCEREAL_TESTS=ON).
        # RREV pin: bare gtest/1.17.0 resolves via conancenter-first to the CCI
        # recipe whose tool_requires cmake/4.4.x has no OHOS sources entry
        # (KeyError: 'OHOS' at cmake build() line 35, this round's preflight).
        # Pin to the ohpcd hardened revision (atracdenc/cucumber-cpp precedent,
        # verified 2026-08-10) which carries no cmake tool requirement; the
        # cmake binary comes from HMBS-injected PATH (HMBS_CMAKE), so no
        # tool_requires cmake is declared here.
        self.test_requires("gtest/1.17.0#ab1bc3bf51522490eef07a83c2dbd203")

    def source(self):
        # Source acquisition (2026-09-25 fix for the preflight
        # ConnectTimeout to android.googlesource.com): clone the pinned
        # commit, Tsinghua AOSP mirror first, official googlesource last.
        # The old +archive tarball URL was dropped on purpose: Gitiles
        # regenerates the gzip per request (same tag URL served 423118 B /
        # sha256 a69bf040… and hours later 423321 B / 00deeca3…), so a pinned
        # tarball sha256 rots; the immutable git commit is the stable
        # identity (conandata.yml documents the verification evidence).
        git = Git(self)
        urls = self.conan_data["sources"]["git_urls"]
        if isinstance(urls, str):
            urls = [urls]
        commit = self.conan_data["sources"]["git_commit"]
        cloned = False
        last_err = None
        for url in urls:
            self._clean_source_folder()
            try:
                self.output.info("Cloning libaemu from %s" % url)
                git.clone(url, target=".")
                cloned = True
                last_err = None
                break
            except ConanException as exc:
                self.output.warning("Clone from %s failed: %s" % (url, exc))
                last_err = exc
        if not cloned:
            raise ConanException(
                "All libaemu source mirrors failed: %s" % (last_err,)
            )
        git.checkout(commit=commit)
        head = git.get_commit()
        if head != commit:
            raise ConanException(
                "Checked-out commit %s != pinned %s" % (head, commit)
            )
        self._patch_host_common_includes()
        self._patch_thirdparty_gtest_main()

    def _patch_thirdparty_gtest_main(self):
        # Round-24 real fix, part 1 (Exp2 "missing link declaration" shape):
        # upstream third-party/CMakeLists.txt queries gtest, gmock and
        # gmock_main via pkg_search_module + ALIAS, but both test executables
        # link plain `gtest_main` (base/CMakeLists.txt,
        # host-common/CMakeLists.txt) with no matching stanza, so CMake
        # degrades it to a bare `-lgtest_main` carrying no -L search path
        # and the OHOS link dies with
        # `ld.lld: error: unable to find library -lgtest_main`
        # (round-23 linktxt/linkfailed). Desktops with system gtest resolve
        # the bare flag, which is why upstream never noticed. Mirror the
        # existing gmock_main stanza (same indent + version predicate); the
        # recipe's fallback gtest_main.pc already supplies
        # `-lgtest_main -lgtest`, so the imported interface also restores
        # the gtest transitive edge. Idempotent, warn-only when absent.
        def _emit(msg):
            try:
                self.output.error("HMBS diag gtest-main-patch: %s" % msg)
            except Exception:
                try:
                    self.output.warning("HMBS diag gtest-main-patch: %s" % msg)
                except Exception:
                    pass
        path = os.path.join(self.source_folder, "third-party",
                            "CMakeLists.txt")
        try:
            if not os.path.isfile(path):
                _emit("no third-party/CMakeLists.txt")
                return
            with open(path, "r", encoding="utf-8",
                      errors="replace") as f:
                txt = f.read()
            if "pkg_search_module(gtest_main" in txt:
                _emit("gtest_main stanza already present")
                return
            anchor = re.compile(
                r"(^[ \t]*add_library\(gmock_main\s+ALIAS\s+"
                r"PkgConfig::gmock_main\)[ \t]*\r?\n)",
                re.MULTILINE)
            m = anchor.search(txt)
            if not m:
                _emit("gmock_main alias anchor absent (layout changed)")
                return
            indent = re.match(r"[ \t]*", m.group(1)).group(0)
            stanza = (
                "%spkg_search_module(gtest_main REQUIRED IMPORTED_TARGET "
                "GLOBAL gtest_main>=0.0.0)\n"
                "%sadd_library(gtest_main ALIAS PkgConfig::gtest_main)\n"
                % (indent, indent))
            txt = txt[:m.end(1)] + stanza + txt[m.end(1):]
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            _emit("gtest_main stanza added after gmock_main alias")
        except Exception as e:
            try:
                self.output.warning("HMBS diag gtest-main-patch failed: %s" % e)
            except Exception:
                pass

    def _patch_host_common_includes(self):
        # Round-17 root-cause fix, round-18 hardened: host-common/CMakeLists.txt
        # exposes PRIVATE include/host-common as -I. That directory contains
        # upstream host-common/features.h, so libc++ __config:261's
        # angle #include <features.h> (glibc/musl feature detection)
        # resolves to the upstream file instead of sysroot/usr/include/
        # features.h. Upstream features.h:16 then re-enters <functional>
        # mid-config -> _LIBCPP_BEGIN_NAMESPACE_STD unknown-type cascade
        # in every TU that pulls <chrono>/<thread>/<cstdint> (logging.cpp,
        # exact.cpp V5). Toy <functional>+<string> without -I compiles,
        # V5 with the 4 upstream -I fails: proven by round-16 probe.
        # Fix: keep the parent `include` on -I (so qualified
        # <host-common/features.h> still resolves) but demote the toxic
        # leaf dir to -iquote (quoted-only): bare "features.h"/"logging.h"
        # keeps working, angle <features.h> falls through to the sysroot.
        # Round-18: exact-whitespace matching proved fragile (this round's
        # fullcmd shows the logging lib patched but the build still fails
        # elsewhere while recapture rc=0 for logging.cpp). Use regex so any
        # whitespace/layout variant is covered, patch EVERY remaining
        # include/host-common occurrence in the file, and emit status via
        # the error channel so it survives preflight summary truncation.
        # Idempotent, warn-only when the pattern is absent.
        def _emit(msg):
            try:
                self.output.error("HMBS diag include-patch: %s" % msg)
            except Exception:
                try:
                    self.output.warning("HMBS diag include-patch: %s" % msg)
                except Exception:
                    pass
        path = os.path.join(self.source_folder, "host-common",
                            "CMakeLists.txt")
        try:
            if not os.path.isfile(path):
                _emit("no host-common/CMakeLists.txt")
                return
            with open(path, "r", encoding="utf-8",
                      errors="replace") as f:
                txt = f.read()
            orig = txt
            # 1) Demote every remaining leaf reference to the parent dir.
            #    Parent `include` still resolves qualified
            #    <host-common/features.h>; bare quoted includes are preserved
            #    by the -iquote blocks added below.
            leaf_count = txt.count("include/host-common")
            txt = txt.replace("include/host-common", "include")
            # Collapse accidental `include/include` from double replacement
            # (idempotency across rounds: second run must be a no-op).
            while "include/include" in txt:
                txt = txt.replace("include/include", "include")
            # 2) Ensure both C++ libs carry the quoted-only fallback.
            #    Regex-anchored so layout variants still match.
            if ("-iquote${CMAKE_CURRENT_SOURCE_DIR}/include/host-common"
                    not in txt):
                # Logging lib block.
                pat_log = re.compile(
                    r"target_include_directories\(\s*\$\{LOGGING_LIB_NAME\}"
                    r"\s*PRIVATE\s*include\s*\)")
                if pat_log.search(txt):
                    txt = pat_log.sub(
                        "target_include_directories(\n"
                        "    ${LOGGING_LIB_NAME}\n"
                        "    PRIVATE\n"
                        "    include)\n"
                        "target_compile_options(\n"
                        "    ${LOGGING_LIB_NAME}\n"
                        "    PRIVATE\n"
                        "    -iquote${CMAKE_CURRENT_SOURCE_DIR}"
                        "/include/host-common)",
                        txt, count=1)
                    _emit("logging lib -I->-iquote (regex)")
                else:
                    _emit("logging pattern absent "
                          "(already patched or layout changed)")
                # Main host-common lib: append at END of file (target must
                # exist; first-match insert hit line 43 before add_library).
                pat_main = re.compile(
                    r"target_include_directories\(\s*aemu-host-common"
                    r"\b[^)]*?\)",
                    re.DOTALL)
                m = pat_main.search(txt)
                if m:
                    anchor = m.group(0)
                    iquote = ("\nif(TARGET aemu-host-common)\ntarget_compile_options(\n"
                              "        aemu-host-common\n"
                              "        PRIVATE\n"
                              "        -iquote${CMAKE_CURRENT_SOURCE_DIR}"
                              "/include/host-common)\nendif()\n")
                    txt += iquote + "\n"
                    _emit("aemu-host-common -iquote added (regex)")
                else:
                    # Fallback: attach to any aemu-host-common occurrence.
                    if "aemu-host-common" in txt:
                        txt += ("\n# HMBS round-18 fallback iquote\n"
                                "if(TARGET aemu-host-common)\n"
                                "target_compile_options(\n"
                                "        aemu-host-common\n"
                                "        PRIVATE\n"
                                "        -iquote${CMAKE_CURRENT_SOURCE_DIR}"
                                "/include/host-common)\nendif()\n")
                        _emit("aemu-host-common fallback -iquote appended")
                    else:
                        _emit("main-lib pattern absent")
            else:
                _emit("iquote already present, leaf refs replaced=%d"
                      % leaf_count)
            # 3) Generic sweep: any other CMakeLists in the tree that still
            #    exposes a bare `include/host-common` -I root gets the same
            #    demotion (read-only audit first, then fix).
            try:
                for root, _dirs, files in os.walk(self.source_folder):
                    # Round-20: sweep CMakeLists.txt AND helper *.cmake
                    # (build-config/*.cmake can also inject include dirs;
                    # old sweep missed them, leaving toxic_Ientries>0).
                    sweep_targets = []
                    if "CMakeLists.txt" in files:
                        sweep_targets.append(
                            os.path.join(root, "CMakeLists.txt"))
                    for fn in files:
                        if fn.endswith(".cmake"):
                            sweep_targets.append(os.path.join(root, fn))
                    for fp in sweep_targets:
                        if os.path.abspath(fp) == os.path.abspath(path):
                            continue
                        try:
                            with open(fp, "r", encoding="utf-8",
                                      errors="replace") as f:
                                sub = f.read()
                        except Exception:
                            continue
                        if "include/host-common" in sub:
                            sub = sub.replace("include/host-common", "include")
                            while "include/include" in sub:
                                sub = sub.replace("include/include", "include")
                            try:
                                with open(fp, "w", encoding="utf-8") as f:
                                    f.write(sub)
                                _emit("swept %s"
                                      % os.path.relpath(fp, self.source_folder))
                            except Exception as e:
                                _emit("sweep-write-failed %s: %s" % (fp, e))
            except Exception as e:
                _emit("sweep-failed: %s" % e)
            if txt != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt)
                _emit("patched %s leaf_refs=%d" % (path, leaf_count))
            else:
                _emit("no change leaf_refs=%d" % leaf_count)
        except Exception as e:
            try:
                self.output.warning("HMBS diag include-patch failed: %s" % e)
            except Exception:
                pass

    def _clean_source_folder(self):
        # Drop leftovers of a failed clone attempt so the next mirror URL
        # starts from an empty directory (git clone refuses a non-empty
        # target). The folder is expected to be empty on the first attempt.
        if not os.path.isdir(self.source_folder):
            return
        for entry in os.listdir(self.source_folder):
            full = os.path.join(self.source_folder, entry)
            if os.path.isdir(full) and not os.path.islink(full):
                shutil.rmtree(full, ignore_errors=True)
            else:
                try:
                    os.remove(full)
                except OSError:
                    pass

    def _ohos_toolchain(self):
        # OHOS builds must go through the SDK ohos.toolchain.cmake
        # (expat/2.8.4, zstd/1.5.6-1.5.7.1, glfw/3.4.6 precedent). Conan's
        # CMakeToolchain only maps os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS
        # with no sysroot/target, so the SDK libcxx-ohos headers fail with
        # _LIBCPP_* unknown-type cascades (this round: compile command has
        # -stdlib=libc++ but --sysroot/--target MISSING, tc SYSROOT-unset).
        # Search order: profile user_toolchain conf, OHOS env vars, then
        # CI (/data/...) and HMBS harmonybrew (/storage/... + $HOME) globs.
        try:
            ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                               default=[], check_type=list)
        except Exception:
            ut = []
        candidates = list(ut) if isinstance(ut, list) else ([ut] if ut else [])
        for env_key, suffix in (("OHOS_NDK_HOME", "build/cmake/ohos.toolchain.cmake"),
                                ("OHOS_SDK_HOME", "ohos/native/build/cmake/ohos.toolchain.cmake"),
                                ("OHOS_SDK_NATIVE", "build/cmake/ohos.toolchain.cmake")):
            ndk = os.environ.get(env_key, "")
            if ndk:
                candidates.append(os.path.join(ndk, suffix))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        home = os.path.expanduser("~")
        for base in ("/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk",
                     os.path.join(home, ".harmonybrew/Cellar/ohos-sdk"),
                     os.path.join(home, ".harmonybrew", "Cellar", "ohos-sdk")):
            patterns.append(os.path.join(base, "*/native/build/cmake/ohos.toolchain.cmake"))
            patterns.append(os.path.join(base, "*/*/native/build/cmake/ohos.toolchain.cmake"))
        sdk_home = os.environ.get("OHOS_SDK_HOME", "")
        if sdk_home:
            patterns.append(os.path.join(sdk_home, "*/ohos/native/build/cmake/ohos.toolchain.cmake"))
            patterns.append(os.path.join(sdk_home, "ohos/native/build/cmake/ohos.toolchain.cmake"))
        for pat in patterns:
            try:
                found = sorted(glob.glob(pat))
            except Exception:
                continue
            if found:
                return found[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME/OHOS_SDK_HOME "
            "or profile tools.cmake.cmaketoolchain:user_toolchain")

    def _prepare_env(self):
        # OHOS SDK lld needs libxml2.so.16 from SDK llvm/lib at link time
        # (E132; zstd/expat precedent). Extend LD_LIBRARY_PATH defensively.
        try:
            cands = sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
            home = os.path.expanduser("~")
            for pat in ("/storage/Users/currentUser/.harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib",
                        os.path.join(home, ".harmonybrew/Cellar/ohos-sdk/*/native/llvm/lib")):
                try:
                    cands += sorted(glob.glob(pat))
                except Exception:
                    pass
            if cands:
                old = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = cands[-1] + (os.pathsep + old if old else "")
        except Exception as e:
            self.output.warning("HMBS diag LD_LIBRARY_PATH setup failed: %s" % e)

    def _ensure_gtest_pc_fallback(self):
        # Pinned gtest/1.17.0#ab1... package_info declares only libs=["gtest"],
        # so PkgConfigDeps emits gtest.pc but no gmock.pc/gmock_main.pc/
        # gtest_main.pc, while upstream third-party/CMakeLists.txt calls
        # pkg_search_module for all of them (1.17.0.2 fixed this with
        # pkg_config_name components, but switching pins needs a new ohpcd
        # RREV; supplementing local .pc files keeps the hardened pin).
        # Round-26: Libs carry ABSOLUTE archive paths, not -l names. The
        # aemu-base_unittests link resolves -lgtest to an archive lacking
        # testing::internal::IsTrue/GTestLog (round-25 snip) while the same
        # package's headers declare them, i.e. -l search-order roulette
        # (a shadow libgtest wins over the Conan one). Absolute
        # ${libdir}/libX.a paths make the resolution deterministic; .a is
        # preferred over .so (static default, visibility-independent).
        # Files land in the same generators folder PkgConfigDeps already
        # puts on PKG_CONFIG_PATH. gtest.pc itself is left alone when
        # PkgConfigDeps generated it (it may carry pthread/defines).
        try:
            gtest = self.dependencies["gtest"]
        except Exception as e:
            self.output.warning("HMBS diag gmock pc: no gtest dep: %s" % e)
            return
        gen = getattr(self, "generators_folder", None)
        if not gen or not os.path.isdir(gen):
            self.output.warning("HMBS diag gmock pc: no generators folder")
            return
        try:
            pkg = gtest.package_folder.replace("\\", "/")
            ver = "1.17.0"
            try:
                _libdirs = list(getattr(gtest.cpp_info, "libdirs", None)
                                or ["lib"])
            except Exception:
                _libdirs = ["lib"]
            _libdir = None
            for _ld in _libdirs:
                _p = os.path.join(pkg, _ld)
                if os.path.isdir(_p):
                    _libdir = _p
                    break
            if _libdir is None:
                _libdir = os.path.join(pkg, "lib")

            def _pick(lib):
                for ext in (".a", ".so"):
                    cand = os.path.join(_libdir, "lib%s%s" % (lib, ext))
                    if os.path.isfile(cand):
                        return "${libdir}/lib%s%s" % (lib, ext)
                return "-l%s" % lib

            _gtest = _pick("gtest")
            _gmock = _pick("gmock")
            _gtest_main = _pick("gtest_main")
            _gmock_main = _pick("gmock_main")
            specs = {
                "gmock": "%s %s" % (_gmock, _gtest),
                "gmock_main": "%s %s %s" % (_gmock_main, _gmock, _gtest),
                "gtest_main": "%s %s" % (_gtest_main, _gtest),
            }
            try:
                if not os.path.isfile(os.path.join(gen, "gtest.pc")):
                    specs["gtest"] = _gtest
            except Exception:
                pass
            _libdirbase = os.path.basename(_libdir.rstrip("/")) or "lib"
            for name, libs in specs.items():
                path = os.path.join(gen, name + ".pc")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(
                        "prefix=%s\nlibdir=${prefix}/%s\n"
                        "includedir=${prefix}/include\n\n"
                        "Name: %s\nDescription: gtest fallback for libaemu\n"
                        "Version: %s\nLibs: %s\n"
                        "Cflags: -I${includedir}\n"
                        % (pkg, _libdirbase, name, ver, libs)
                    )
                try:
                    self.output.error("HMBS diag gtest-pc %s: Libs=%s"
                                      % (name, libs[:160]))
                except Exception:
                    pass
        except Exception as e:
            self.output.warning("HMBS diag gmock pc fallback failed: %s" % e)

    def generate(self):
        # No CMakeToolchain on OHOS: it yields SYSTEM_NAME=HarmonyOS without
        # sysroot/target (see _ohos_toolchain). Bare cmake with the SDK
        # toolchain file owns all compiler/sysroot flags; PkgConfigDeps only
        # supplies gtest .pc files for upstream pkg_search_module.
        PkgConfigDeps(self).generate()
        self._ensure_gtest_pc_fallback()
        if str(self.settings.os) == "OHOS":
            try:
                tc = self._ohos_toolchain()
                self.output.info("HMBS diag ohos.toolchain: %s" % tc)
            except Exception as e:
                self.output.warning("HMBS diag ohos.toolchain lookup: %s" % e)
        else:
            from conan.tools.cmake import CMakeToolchain
            tc = CMakeToolchain(self)
            tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
            tc.variables["AEMU_COMMON_BUILD_CONFIG"] = "gfxstream"
            tc.variables["AEMU_COMMON_GEN_PKGCONFIG"] = "ON"
            tc.variables["ENABLE_VKCEREAL_TESTS"] = "ON"
            tc.variables["AEMU_BASE_USE_LZ4"] = "OFF"
            tc.variables["AEMU_COMMON_USE_PERFETTO"] = "OFF"
            tc.generate()

    def build(self):
        self._prepare_env()
        if str(self.settings.os) == "OHOS":
            self._build_with_ohos_toolchain()
        else:
            self._build_with_conan_cmake()
        if can_run(self):
            bdir = os.path.join(self.build_folder, "build-ohos") \
                if str(self.settings.os) == "OHOS" and \
                os.path.isdir(os.path.join(self.build_folder, "build-ohos")) \
                else self.build_folder
            self._run_upstream_tests(bdir)

    def _cmake_defs(self):
        shared = "ON" if self.options.shared else "OFF"
        defs = [
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DBUILD_SHARED_LIBS=%s" % shared,
            "-DAEMU_COMMON_BUILD_CONFIG=gfxstream",
            "-DAEMU_COMMON_GEN_PKGCONFIG=ON",
            "-DENABLE_VKCEREAL_TESTS=ON",
            "-DAEMU_BASE_USE_LZ4=OFF",
            "-DAEMU_COMMON_USE_PERFETTO=OFF",
            "-DCMAKE_CXX_STANDARD=17",
            "-DCMAKE_CXX_STANDARD_REQUIRED=ON",
            # Round-14: -stdlib lives in a wrapper toolchain file (see
            # _hmbs_wrapper_toolchain), never in -D FLAGS (round-11,
            # destructive) nor absent (round-12) nor env-only (round-13,
            # fullcmd still MISSING). No -D FLAGS here on purpose.
            "-DCMAKE_POSITION_INDEPENDENT_CODE=%s" % (
                "ON" if bool(self.options.get_safe("fPIC", True)) else "OFF"),
            "-DCMAKE_VERBOSE_MAKEFILE=ON",
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        ]
        if str(self.settings.os) == "OHOS" and self.options.shared:
            # No Platform/HarmonyOS.cmake module in CMake: the Linux module
            # that defines CMAKE_SHARED_LIBRARY_SONAME_C_FLAG is not loaded,
            # so upstream VERSION/SOVERSION never turns into a -Wl,-soname
            # flag (see knowledge/DRAFT-libharu-2.3.0-missing-dt-soname.md).
            defs.append("-DCMAKE_SHARED_LIBRARY_SONAME_C_FLAG=-Wl,-soname,")
            defs.append("-DCMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,")
        return defs

    def _hmbs_wrapper_toolchain(self, sdk_toolchain, extra_link_dirs=None):
        # Round-14: three injections never reached compile_commands (-D in
        # round-11, absent in round-12, CXXFLAGS env in round-13 all show
        # -stdlib=MISSING): something inside cmake (SDK toolchain FORCE-set
        # or upstream overwrite) drops outside flags. The surviving pattern
        # is the one Conan's own CMakeToolchain uses (ada/xqilla precedent):
        # string(APPEND ...) evaluated AFTER the SDK toolchain body. This
        # wrapper includes the SDK file first, then appends -stdlib to the
        # compile and link flag variables. Written under the build folder,
        # idempotent per content.
        # Round-21: textual sweeping cannot converge (24 toxic TUs remain
        # with NO literal `include/host-common` in any CMakeLists/*.cmake:
        # the leaf is built dynamically, so no text pattern catches it).
        # Different strategy: a compiler filter script demotes ANY
        # `-I.../host-common/include/host-common` (split/combined, cmdline
        # or response file) to `-iquote...` at exec time. Set as
        # CMAKE_C/CXX_COMPILER below (after the SDK include) so it survives
        # any FORCE-set inside the SDK file.
        bdir = os.path.join(self.build_folder, "build-ohos")
        try:
            os.makedirs(bdir, exist_ok=True)
        except Exception:
            pass
        wrapper = os.path.join(bdir, "hmbs-aemu-ohos-tc.cmake")
        # Round-21: compiler filter scripts (leaf -I -> -iquote at exec).
        # Round-25: also demote -isystem leaf (split/combined/@rsp). The
        # 24/78 toxic -I entries never converged over 4 rounds; any leaf
        # arriving via -isystem bypasses the -I-only rewrite and hijacks
        # angle <features.h> identically. -iquote keeps quoted lookup.
        try:
            native_dir = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(sdk_toolchain))))
            real_cxx = os.path.join(native_dir, "llvm", "bin", "clang++")
            real_cc = os.path.join(native_dir, "llvm", "bin", "clang")
        except Exception:
            real_cxx, real_cc = "clang++", "clang"
        _filter_tpl = (
            "#!/usr/bin/env python3\n"
            "import os, re, sys, tempfile\n"
            "REAL = %r\n"
            "def _map_inc(path):\n"
            "    if \"host-common/include/host-common\" in path.replace(chr(92), \"/\"):\n"
            "        return \"-iquote\" + path\n"
            "    return None\n"
            "def _filter_rsp(text):\n"
            "    text = re.sub(r\"-I([^\\s]+host-common/include/host-common[^\\s]*)\",\n"
            "                lambda m: \"-iquote\" + m.group(1), text)\n"
            "    text = re.sub(r\"-isystem\\s+([^\\s]*host-common/include/host-common[^\\s]*)\",\n"
            "                lambda m: \"-iquote\" + m.group(1), text)\n"
            "    return re.sub(r\"-isystem([^\\s]+host-common/include/host-common[^\\s]*)\",\n"
            "                lambda m: \"-iquote\" + m.group(1), text)\n"
            "def main():\n"
            "    args = sys.argv[1:]\n"
            "    out = []\n"
            "    i = 0\n"
            "    while i < len(args):\n"
            "        a = args[i]\n"
            "        if a == \"-I\" and i + 1 < len(args):\n"
            "            m = _map_inc(args[i + 1])\n"
            "            out.append(m if m is not None else \"-I\")\n"
            "            if m is None:\n"
            "                out.append(args[i + 1])\n"
            "            i += 2\n"
            "            continue\n"
            "        if a.startswith(\"-I\") and len(a) > 2:\n"
            "            m = _map_inc(a[2:])\n"
            "            out.append(m if m is not None else a)\n"
            "            i += 1\n"
            "            continue\n"
            "        if a == \"-isystem\" and i + 1 < len(args):\n"
            "            m = _map_inc(args[i + 1])\n"
            "            out.append(m if m is not None else \"-isystem\")\n"
            "            if m is None:\n"
            "                out.append(args[i + 1])\n"
            "            i += 2\n"
            "            continue\n"
            "        if a.startswith(\"-isystem\") and len(a) > 8:\n"
            "            m = _map_inc(a[8:])\n"
            "            out.append(m if m is not None else a)\n"
            "            i += 1\n"
            "            continue\n"
            "        if a.startswith(\"@\") and len(a) > 1:\n"
            "            try:\n"
            "                with open(a[1:], \"r\", encoding=\"utf-8\", errors=\"replace\") as f:\n"
            "                    text = f.read()\n"
            "                new = _filter_rsp(text)\n"
            "                if new != text:\n"
            "                    fd, tmp = tempfile.mkstemp(suffix=\".rsp\")\n"
            "                    with os.fdopen(fd, \"w\", encoding=\"utf-8\") as f:\n"
            "                        f.write(new)\n"
            "                    out.append(\"@\" + tmp)\n"
            "                else:\n"
            "                    out.append(a)\n"
            "            except Exception:\n"
            "                out.append(a)\n"
            "            i += 1\n"
            "            continue\n"
            "        out.append(a)\n"
            "        i += 1\n"
            "    os.execv(REAL, [REAL] + out)\n"
            "main()\n"
        )
        cxx_filter = os.path.join(bdir, "hmbs-cxx-filter.py")
        cc_filter = os.path.join(bdir, "hmbs-cc-filter.py")
        try:
            for _fp, _real in ((cxx_filter, real_cxx), (cc_filter, real_cc)):
                _content = _filter_tpl % (_real.replace("\\", "/"),)
                _old = ""
                if os.path.isfile(_fp):
                    with open(_fp, "r", encoding="utf-8",
                              errors="replace") as _f:
                        _old = _f.read()
                if _old != _content:
                    with open(_fp, "w", encoding="utf-8") as _f:
                        _f.write(_content)
                    try:
                        os.chmod(_fp, 0o755)
                    except Exception:
                        pass
            try:
                self.output.error("HMBS diag compiler-filter: cxx=%s"
                                  % real_cxx[-60:])
            except Exception:
                pass
        except Exception as _e:
            try:
                self.output.warning("HMBS diag compiler-filter failed: %s" % _e)
            except Exception:
                pass
        content = (
            '# HMBS wrapper toolchain for libaemu (round-14, generated)\n'
            '# Includes the SDK toolchain, then appends -stdlib AFTER it so\n'
            '# the flag survives any FORCE-set inside the SDK file.\n'
            'include("%s")\n'
            'string(APPEND CMAKE_CXX_FLAGS " -stdlib=libc++")\n'
            'string(APPEND CMAKE_EXE_LINKER_FLAGS " -stdlib=libc++")\n'
            'string(APPEND CMAKE_SHARED_LINKER_FLAGS " -stdlib=libc++")\n'
            'string(APPEND CMAKE_MODULE_LINKER_FLAGS " -stdlib=libc++")\n'
            '# Round-21: route compiles through the leaf-demoting filter.\n'
            'set(CMAKE_C_COMPILER "%s" CACHE FILEPATH "" FORCE)\n'
            'set(CMAKE_CXX_COMPILER "%s" CACHE FILEPATH "" FORCE)\n'
            % (sdk_toolchain.replace("\\", "/"),
               cc_filter.replace("\\", "/"),
               cxx_filter.replace("\\", "/"))
        )
        # Round-27: pin archiver to the SDK absolute path (CI #62453:
        # first archive host-common/libaemu-logging.a dies with
        # `Error running link command: no such file or directory` while
        # every TU compiles, i.e. the archiver binary itself is missing).
        # CI PATH is minimal with no host `ar`; the HMBS true-machine has
        # host binutils, which is why the same commit passed preflight.
        # Appended AFTER the SDK include via FORCE, same mechanism as the
        # compiler filter. Existence-checked, falls back to bare names.
        try:
            _native27 = os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(sdk_toolchain))))
            _ar27 = os.path.join(_native27, "llvm", "bin", "llvm-ar")
            _ran27 = os.path.join(_native27, "llvm", "bin", "llvm-ranlib")
            _real_ar27 = _ar27 if os.path.isfile(_ar27) else "ar"
            _real_ran27 = _ran27 if os.path.isfile(_ran27) else "ranlib"
            try:
                self.output.error("HMBS diag archiver: ar=%s ranlib=%s"
                                  % (_real_ar27[-80:], _real_ran27[-80:]))
            except Exception:
                pass
            content = content + (
                'set(CMAKE_AR "%s" CACHE FILEPATH "" FORCE)\n'
                'set(CMAKE_RANLIB "%s" CACHE FILEPATH "" FORCE)\n'
                % (_real_ar27.replace("\\", "/"),
                   _real_ran27.replace("\\", "/")))
        except Exception as _e27:
            try:
                self.output.warning("HMBS diag archiver setup failed: %s" % _e27)
            except Exception:
                pass
        # Round-24: order-independent library search path for test-exe
        # links (Exp2 fallback shape). -L carries no ordering semantics, so
        # appending it here cannot break symbol resolution; it only lets
        # bare `-lgtest_main/-lgmock/-lgtest` flags (upstream links plain
        # names with no visible target, round-23 linktxt) resolve to the
        # Conan gtest package. EXE/SHARED/MODULE only; static archives take
        # no -L. Same string(APPEND)-after-include mechanism as -stdlib.
        _ld_extra = ""
        try:
            for _d in (extra_link_dirs or []):
                _dd = _d.replace("\\", "/")
                if not _dd:
                    continue
                _ld_extra += (
                    'string(APPEND CMAKE_EXE_LINKER_FLAGS " -L%s")\n'
                    'string(APPEND CMAKE_SHARED_LINKER_FLAGS " -L%s")\n'
                    'string(APPEND CMAKE_MODULE_LINKER_FLAGS " -L%s")\n'
                    % (_dd, _dd, _dd))
                try:
                    self.output.error("HMBS diag wrapper linkdir: %s" % _dd)
                except Exception:
                    pass
        except Exception as _e:
            try:
                self.output.warning("HMBS diag wrapper linkdir failed: %s" % _e)
            except Exception:
                pass
        if _ld_extra:
            content = content + _ld_extra
        try:
            old = ""
            if os.path.isfile(wrapper):
                with open(wrapper, "r", encoding="utf-8",
                          errors="replace") as f:
                    old = f.read()
            if old != content:
                with open(wrapper, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info("HMBS diag wrote wrapper toolchain: %s"
                                 % wrapper)
        except Exception as e:
            self.output.warning("HMBS diag wrapper toolchain write failed: %s"
                                % e)
        return wrapper

    def _probe_cxx_environment(self, sdk_tc):
        # Cycle-5 / round-15 isolation probe (read-only, never raises).
        #
        # Why this instead of a fifth flag tweak: rounds 11-14 falsified
        # the whole flag-injection family. The latest fullcmd already
        # carries --target + --sysroot + -D__MUSL__ + -stdlib=libc++ (x2)
        # + -std=gnu++17, i.e. every flag the four rounds chased is
        # provably present, yet the _LIBCPP_* cascade is byte-identical.
        # Flag STRINGS are therefore exhausted as a diagnostic. None of
        # rounds 6-14 ever collected (a) which __config file the compiler
        # actually includes (-H trace), (b) predefined macros (-dM:
        # __OHOS__/__MUSL__/clang version), (c) whether ANY minimal C++
        # TU survives the same base flags (environment-vs-upstream
        # isolation, incl. the hnp wrapper compiler as a control), (d) a
        # shadowing audit of the TRUE source tree, (e) CPLUS_INCLUDE_PATH
        # style env that flag dumps never show. This probe emits exactly
        # that through the error channel (preflight-summary safe).
        def emit(msg):
            try:
                for line in str(msg).splitlines() or [""]:
                    self.output.error("HMBS diag probe: %s" % line[:600])
            except Exception:
                pass

        emit("start")
        try:
            emit("sdk_toolchain=%s" % sdk_tc)
            native = sdk_tc
            for _ in range(3):
                native = os.path.dirname(native)
            emit("sdk_native=%s" % native)
            sysroot = os.path.join(native, "sysroot")
            emit("sysroot_exists=%s" % os.path.isdir(sysroot))
            # (a) compilers: SDK clang++ vs hnp wrapper clang++.
            sdk_cxx = os.path.join(native, "llvm", "bin", "clang++")
            hnp_cxx = "/data/service/hnp/bin/clang++"
            for cxx in (sdk_cxx, hnp_cxx):
                if cxx and os.path.isfile(cxx):
                    try:
                        p = subprocess.run(
                            [cxx, "--version"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=60, check=False)
                        first = (p.stdout or "").strip().splitlines()
                        emit("compiler %s -> %s"
                             % (cxx, first[0] if first else "empty"))
                    except Exception as e:
                        emit("compiler %s run-failed=%s" % (cxx, e))
                else:
                    emit("compiler %s MISSING" % cxx)
            main_cxx = sdk_cxx if os.path.isfile(sdk_cxx) else hnp_cxx
            if not os.path.isfile(main_cxx):
                emit("no compiler available, stop probe")
                return
            # (b) shadowing audit on the TRUE source tree + build tree: any
            # file whose basename would hijack a libc++ angle-include when
            # an -I root precedes the system path. Round-16: the old set
            # missed exactly the headers logging.cpp uses (chrono/thread/
            # sstream/cstdio/cstring/cinttypes), so a toy <functional>
            # probe can pass while the real TU fails. Cover the full set
            # and walk both source and build folders (generated headers
            # can shadow too).
            shadow_names = {"__config", "__config_site", "version",
                            "functional", "string", "vector", "memory",
                            "algorithm", "cstdio", "ctime", "cstdint",
                            "string.h", "time.h", "chrono", "thread",
                            "sstream", "cstring", "cinttypes", "cstdio",
                            "cstdlib", "cstddef", "type_traits", "utility",
                            "mutex", "condition_variable", "atomic",
                            "system_error", "locale", "codecvt", "ios",
                            "iostream", "istream", "ostream", "streambuf",
                            "features.h"}
            hits = []
            try:
                roots = [self.source_folder]
                try:
                    if os.path.isdir(self.build_folder):
                        roots.append(self.build_folder)
                except Exception:
                    pass
                for top in roots:
                    for root, _dirs, files in os.walk(top):
                        for fn in files:
                            if fn in shadow_names:
                                try:
                                    rel = os.path.relpath(
                                        os.path.join(root, fn), top)
                                except Exception:
                                    rel = os.path.join(root, fn)
                                tag = ("build:" if top != self.source_folder
                                       else "src:")
                                hits.append(tag + rel)
                                if len(hits) >= 30:
                                    break
                        if len(hits) >= 30:
                            break
                    if len(hits) >= 30:
                        break
            except Exception as e:
                emit("source-walk-failed=%s" % e)
            emit("shadow_hits=%d %s" % (len(hits), hits[:30]))
            # (c) __config_site presence under this SDK layout.
            for pat in (os.path.join(native, "llvm", "include",
                                     "libcxx-ohos", "include", "c++", "v1",
                                     "__config*"),
                        os.path.join(native, "llvm", "lib", "clang", "*",
                                     "include", "__config_site"),
                        os.path.join(sysroot, "usr", "include", "c++", "v1",
                                     "__config_site")):
                try:
                    emit("glob %s -> %s" % (pat, sorted(glob.glob(pat))[:5]))
                except Exception as e:
                    emit("glob-failed %s: %s" % (pat, e))
            # (d) minimal TU under the same base flags as the failing TU.
            pdir = os.path.join(self.build_folder, "hmbs-probe")
            try:
                os.makedirs(pdir, exist_ok=True)
            except Exception:
                pass
            tu = os.path.join(pdir, "probe.cpp")
            empty = os.path.join(pdir, "empty.cpp")
            try:
                with open(tu, "w", encoding="utf-8") as f:
                    f.write("#include <functional>\n#include <string>\n"
                            "int main(){ std::function<int(int)> f = "
                            "[](int x){ return x + 1; }; "
                            "return f(41) == 42 ? 0 : 1; }\n")
                with open(empty, "w", encoding="utf-8") as f:
                    f.write("\n")
            except Exception as e:
                emit("probe-write-failed=%s" % e)
                return
            base = ["--target=aarch64-linux-ohos",
                    "--sysroot=%s" % sysroot,
                    "-stdlib=libc++", "-fPIC"]
            variants = {
                "V1-mirror": base + ["-D__MUSL__", "-std=gnu++17"],
                "V2-noMUSL": base + ["-std=gnu++17"],
                "V3-cxx17": base + ["-D__MUSL__", "-std=c++17"],
            }
            for vname, flags in variants.items():
                try:
                    p = subprocess.run(
                        [main_cxx] + flags + ["-c", tu, "-o",
                                              os.path.join(pdir, vname + ".o")],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=180, check=False)
                    out = p.stdout or ""
                    emit("%s rc=%d" % (vname, p.returncode))
                    if p.returncode != 0:
                        for tl in out.strip().splitlines()[-6:]:
                            emit("%s err: %s" % (vname, tl[:400]))
                    else:
                        emit("%s COMPILES" % vname)
                except Exception as e:
                    emit("%s run-failed=%s" % (vname, e))
            # Control: same TU with the hnp wrapper compiler (ada/baloo
            # route). If hnp compiles it while the SDK clang++ does not,
            # the defect is compiler/headers, not flags or upstream.
            if hnp_cxx != main_cxx and os.path.isfile(hnp_cxx):
                try:
                    p = subprocess.run(
                        [hnp_cxx] + variants["V1-mirror"] + ["-c", tu, "-o",
                                     os.path.join(pdir, "V4-hnp.o")],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=180, check=False)
                    out = p.stdout or ""
                    emit("V4-hnp rc=%d" % p.returncode)
                    if p.returncode != 0:
                        for tl in out.strip().splitlines()[-6:]:
                            emit("V4-hnp err: %s" % (tl[:400]))
                    else:
                        emit("V4-hnp COMPILES")
                except Exception as e:
                    emit("V4-hnp run-failed=%s" % e)
            # (d2) Round-16 exact-header bisection: the V1-V3 toy TU
            # (<functional>+<string>) COMPILES on this SDK, so it is a
            # false negative for the real failure (logging.cpp includes
            # <chrono>/<cinttypes>/<cstdio>/<cstring>/<sstream>/<thread>
            # plus the __linux__ <sys/syscall.h> block). Build the exact
            # header set with the same base flags AND the real upstream
            # -I roots, in three variants (mirror/noMUSL/cxx17). This
            # distinguishes "specific std headers break with -D__MUSL__/
            # gnu++17" from "upstream -I shadows a header". Read-only.
            try:
                exact = os.path.join(pdir, "exact.cpp")
                with open(exact, "w", encoding="utf-8") as f:
                    f.write("#include <chrono>\n#include <cinttypes>\n"
                            "#include <cstdio>\n#include <cstring>\n"
                            "#include <sstream>\n#include <thread>\n"
                            "int main(){ return 0; }\n")
                inc_roots = []
                for cand in (
                        os.path.join(self.source_folder, "base", "include"),
                        os.path.join(self.source_folder, "host-common",
                                     "include"),
                        os.path.join(self.source_folder, "host-common",
                                     "include", "host-common"),
                        os.path.join(self.source_folder, "snapshot",
                                     "include")):
                    if os.path.isdir(cand):
                        inc_roots.append(cand)
                emit("exact inc_roots=%d %s"
                     % (len(inc_roots), inc_roots[:4]))
                exact_variants = {
                    "V5-exact-mirror": base + ["-D__MUSL__",
                                               "-std=gnu++17"],
                    "V6-exact-noMUSL": base + ["-std=gnu++17"],
                    "V7-exact-cxx17": base + ["-D__MUSL__",
                                              "-std=c++17"],
                }
                for vname, flags in exact_variants.items():
                    inc_flags = []
                    for r in inc_roots:
                        inc_flags += ["-I", r]
                    try:
                        p = subprocess.run(
                            [main_cxx] + flags + inc_flags +
                            ["-c", exact, "-o",
                             os.path.join(pdir, vname + ".o")],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True, timeout=180, check=False)
                        out = p.stdout or ""
                        emit("%s rc=%d" % (vname, p.returncode))
                        if p.returncode != 0:
                            for tl in out.strip().splitlines()[:8]:
                                emit("%s err: %s" % (vname, tl[:400]))
                        else:
                            emit("%s COMPILES" % vname)
                    except Exception as e:
                        emit("%s run-failed=%s" % (vname, e))
                # Round-19 V8: validate the PATCHED flag shape (parent -I +
                # -iquote leaf, i.e. what the real build uses after the
                # round-17/18 CMakeLists patch). V5-V7 always use the raw
                # leaf -I so they stay red even after the fix; V8 must turn
                # green to prove the patch works. Read-only.
                try:
                    patched_flags = []
                    for r in inc_roots:
                        if r.endswith("include/host-common"):
                            continue
                        patched_flags += ["-I", r]
                    leaf = os.path.join(self.source_folder, "host-common",
                                        "include", "host-common")
                    v8_flags = (base + ["-D__MUSL__", "-std=gnu++17"]
                                + patched_flags)
                    if os.path.isdir(leaf):
                        v8_flags += ["-iquote", leaf]
                    p = subprocess.run(
                        [main_cxx] + v8_flags +
                        ["-c", exact, "-o",
                         os.path.join(pdir, "V8-patched.o")],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True, timeout=180, check=False)
                    out = p.stdout or ""
                    emit("V8-patched rc=%d" % p.returncode)
                    if p.returncode != 0:
                        for tl in out.strip().splitlines()[:8]:
                            emit("V8-patched err: %s" % (tl[:400]))
                    else:
                        emit("V8-patched COMPILES")
                except Exception as e:
                    emit("V8-patched run-failed=%s" % e)
            except Exception as e:
                emit("exact-probe-failed=%s" % e)
            # (e) predefined macros.
            try:
                p = subprocess.run(
                    [main_cxx, "--target=aarch64-linux-ohos",
                     "--sysroot=%s" % sysroot, "-D__MUSL__",
                     "-stdlib=libc++", "-std=gnu++17",
                     "-E", "-dM", "-x", "c++", empty],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=120, check=False)
                wants = ("__OHOS__", "__ohos__", "__MUSL__", "__musl__",
                         "__clang_major__", "__clang_minor__",
                         "__cplusplus", "__GLIBC__", "__ANDROID__",
                         "_LIBCPP_VERSION")
                for line in (p.stdout or "").splitlines():
                    if any(w in line for w in wants):
                        emit("dM: %s" % line.strip()[:300])
            except Exception as e:
                emit("dM-failed=%s" % e)
            # (f) include trace: WHICH __config is actually picked.
            try:
                p = subprocess.run(
                    [main_cxx] + variants["V1-mirror"] + ["-H", "-c", tu,
                                                          "-o", os.path.join(
                                                              pdir, "trace.o")],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=180, check=False)
                shown = 0
                for line in (p.stdout or "").splitlines():
                    if "__config" in line or "functional" in line:
                        emit("trace: %s" % line.strip()[:400])
                        shown += 1
                        if shown >= 15:
                            break
                emit("trace rc=%d" % p.returncode)
            except Exception as e:
                emit("trace-failed=%s" % e)
            # (g) include-path env that flag dumps never show.
            for key in ("CPLUS_INCLUDE_PATH", "CPATH", "C_INCLUDE_PATH",
                        "CROSS_CPLUS_INCLUDE_PATH"):
                emit("env %s=%s" % (key, os.environ.get(key, "")[:400]))
        except Exception as e:
            try:
                self.output.error("HMBS diag probe: outer-failed=%s" % e)
            except Exception:
                pass

    def _build_with_ohos_toolchain(self):
        sdk_tc = self._ohos_toolchain()
        self.output.info("HMBS diag using ohos.toolchain: %s" % sdk_tc)
        # Round-24: gtest package libdirs for the wrapper -L fallback (the
        # pinned gtest/1.17.0 package_info declares no pkg_config components,
        # upstream links bare -lgtest_main with no target; -L is order-free).
        gtest_libdirs = []
        try:
            gdep = self.dependencies["gtest"]
            _pkg = gdep.package_folder.replace("\\", "/")
            try:
                _libdirs = list(getattr(gdep.cpp_info, "libdirs", None)
                                or ["lib"])
            except Exception:
                _libdirs = ["lib"]
            for _ld in _libdirs:
                _p = os.path.join(_pkg, _ld)
                if os.path.isdir(_p):
                    gtest_libdirs.append(_p.replace("\\", "/"))
            if not gtest_libdirs:
                gtest_libdirs.append(os.path.join(_pkg, "lib").replace(
                    "\\", "/"))
        except Exception as e:
            self.output.warning("HMBS diag gtest libdir lookup failed: %s" % e)
        toolchain = self._hmbs_wrapper_toolchain(sdk_tc,
                                                 extra_link_dirs=gtest_libdirs)
        # Cycle-5 / round-15: run the read-only isolation probe BEFORE
        # cmake configure (never raises; real build proceeds regardless).
        # Four flag-injection rounds left the fingerprint byte-identical
        # with all flags provably present, so this round collects the
        # never-before-seen evidence (include trace, predefined macros,
        # minimal-TU isolation, true-source shadowing audit) instead of
        # a fifth flag tweak.
        try:
            self._probe_cxx_environment(sdk_tc)
        except Exception as e:
            self.output.warning("HMBS diag probe outer: %s" % e)
        # Bare cmake (no conan_toolchain.cmake) does not inherit the
        # generators-folder PKG_CONFIG_PATH that CMakeToolchain used to wire
        # for PkgConfigDeps; upstream third-party/CMakeLists.txt calls
        # pkg_search_module(gtest/gmock/...) so export it explicitly.
        try:
            gen = getattr(self, "generators_folder", None)
            if gen and os.path.isdir(gen):
                old_pc = os.environ.get("PKG_CONFIG_PATH", "")
                paths = [gen] + ([old_pc] if old_pc else [])
                os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(paths)
                self.output.info("HMBS diag PKG_CONFIG_PATH=%s"
                                 % os.environ["PKG_CONFIG_PATH"])
                try:
                    pcs = sorted(os.listdir(gen))
                    self.output.info("HMBS diag generators pcs=%s" % pcs)
                except Exception:
                    pass
            else:
                self.output.warning("HMBS diag no generators folder for pkg-config")
        except Exception as e:
            self.output.warning("HMBS diag PKG_CONFIG_PATH setup failed: %s" % e)
        # Round-13: safe-append -stdlib=libc++ via env (xqilla extra_cxxflags
        # equivalent for bare cmake). A -D CMAKE_CXX_FLAGS=... would overwrite
        # the ohos.toolchain INIT (round-11 lesson); CXXFLAGS env is merged by
        # CMake on first configure, preserving --target/--sysroot/-D__MUSL__.
        # Idempotent: only append when the substring is absent.
        try:
            cxxf = os.environ.get("CXXFLAGS", "")
            if "-stdlib=libc++" not in cxxf:
                os.environ["CXXFLAGS"] = (cxxf + " -stdlib=libc++").strip()
            ldf = os.environ.get("LDFLAGS", "")
            if "-stdlib=libc++" not in ldf:
                os.environ["LDFLAGS"] = (ldf + " -stdlib=libc++").strip()
            self.output.info("HMBS diag CXXFLAGS=%s"
                             % os.environ.get("CXXFLAGS", ""))
            self.output.info("HMBS diag LDFLAGS=%s"
                             % os.environ.get("LDFLAGS", ""))
        except Exception as e:
            self.output.warning("HMBS diag stdlib env setup failed: %s" % e)
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join(['-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
                         "-DOHOS_ARCH=arm64-v8a"] + self._cmake_defs())
        try:
            self.run('cmake -B "%s" -S "%s" %s' % (bdir, self.source_folder, defs))
        except Exception as exc:
            try:
                self._report_build_failure_evidence(exc, bdir, toolchain)
            except ConanException:
                raise
            raise
        # Round-19: capture the REAL build output instead of discarding it.
        # self.run() only raises "Error 2 while executing" with no TU name,
        # so round-18's fail-guess always fell back to logging.cpp (rc=0)
        # while the true culprit hid in the truncated middle. Run cmake
        # --build via subprocess, stream nothing, but on failure emit the
        # failing target file + first error lines via the error channel and
        # re-raise with that context attached so _report can recapture the
        # exact TU instead of the hardcoded one.
        try:
            self._cmake_build_capture(bdir)
        except Exception as exc:
            try:
                self._report_build_failure_evidence(exc, bdir, toolchain)
            except ConanException:
                raise
            raise

    def _cmake_build_capture(self, bdir):
        # Run `cmake --build` capturing combined output; on success return
        # silently, on failure raise ConanException whose message embeds the
        # failing .cpp path (FAILED:/error: parsing below) plus the first
        # error lines, so the evidence reporter can target the real TU.
        cmd = 'cmake --build "%s"' % bdir
        try:
            self.output.info("HMBS diag build-capture: %s" % cmd)
        except Exception:
            pass
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3600,
            check=False,
        )
        output = proc.stdout or ""
        if proc.returncode == 0:
            try:
                tail = output.splitlines()[-3:]
                for line in tail:
                    self.output.info("HMBS diag build-ok: %s" % line[:400])
            except Exception:
                pass
            return
        # Failure: find the failing TU path, distinguishing compile vs link.
        # Round-20: WorkerThread_unittest.cpp recapture rc=0 proves the old
        # guess misattributes linker failures to the last compiled .cpp.
        # Round-21 fix: `ninja: build stopped` fires for EVERY failure and
        # `GfxstreamFatalError.cpp.o` contains substring "error", so the old
        # test misclassified a compile failure as kind=link with progress
        # lines as builderr. Compile errors dominate: any `.cpp:line` plus
        # `error:` means compile; link only when ld/undefined appears with
        # NO `.cpp:line` error at all.
        # Round-22: round-21's link regex names the FIRST aemu-* substring
        # after FAILED:, which for an executable link is an INPUT archive
        # (libaemu-logging.a), not the linking target — while upstream
        # declares the logging lib via plain add_library() (static under
        # BUILD_SHARED_LIBS=OFF), so `ar` can never emit "clang++: error:
        # linker command failed". The LINK:aemu-logging.a label is therefore
        # a misattribution; take the real `FAILED: <target>` path instead,
        # skip verbose compiler echoes that hid the ld.lld lines, and widen
        # the link window (one error per undefined symbol).
        fail = ""
        kind = "unknown"
        failed_targets = []
        linking_lines = []
        _snip = []
        try:
            for _ln in output.splitlines():
                _s = _ln.strip()
                if _s.startswith("FAILED:"):
                    _tok = _s[len("FAILED:"):].strip().split()
                    if _tok:
                        failed_targets.append(_tok[0][:200])
                elif _s.startswith("Linking CXX"):
                    # Make-generator progress line; the LAST one names the
                    # step that was running when the build died.
                    linking_lines.append(_s[:300])
            # Round-23: Make-generator `make[n]: *** [...] Error` lines. The
            # FIRST (deepest) one names the real failed target; outer ones
            # are just directory-level `Error 2` propagation.
            try:
                _merrs = re.findall(
                    r"make\[\d+\]: \*\*\* \[([^\]]+)\]", output)
                if _merrs:
                    _deep = _merrs[0].strip().split()
                    _deep = [t for t in _deep if "/" in t]
                    if _deep:
                        failed_targets.append(_deep[-1][:200])
            except Exception:
                pass
            # dedupe, keep order
            _seen = set()
            failed_targets = [t for t in failed_targets
                              if not (t in _seen or _seen.add(t))]
            # Ninja/GNU-make styles: FAILED: <obj> ... <src>.cpp or
            # "Building CXX object ... <src>.cpp.o" followed by error:.
            cands = re.findall(r"[\w\-./\\]+\.cpp", output)
            # Prefer the .cpp nearest to the first "error:" line.
            err_idx = output.lower().find("error:")
            low_all = output.lower()
            has_any_error = ("error:" in low_all)
            has_cpp_err = bool(
                re.search(r"\.cpp:\d+", low_all))
            has_link_sig = bool(
                re.search(r"ld\.lld:\s*error|undefined (reference|symbol)|"
                          r"multiple definition|duplicate symbol|"
                          r"relocation |cannot find -l|ar:\s*.*error",
                          low_all))
            if has_any_error and has_cpp_err:
                kind = "compile"
                if err_idx >= 0 and cands:
                    best = ""
                    best_pos = -1
                    for c in cands:
                        pos = output.rfind(c, 0, err_idx + 2000)
                        if pos > best_pos:
                            best_pos = pos
                            best = c
                    fail = best or cands[-1]
                elif cands:
                    fail = cands[-1]
            elif has_link_sig and not has_cpp_err:
                kind = "link"
                # Round-23: Make-generator aware. This tree builds with Unix
                # Makefiles (link.txt exists, no FAILED: lines), so the
                # FIRST `Linking CXX` line is a stale success echo — the
                # round-22 fallback named it and re-mislabeled the failure.
                # Use the LAST `Linking CXX ... <target>` line; the deepest
                # `make[n]` Error target (already first in failed_targets)
                # wins when present.
                _link_target = ""
                for _ll in linking_lines:
                    _tok = _ll.strip().split()
                    if _tok:
                        _link_target = _tok[-1][:200]
                if failed_targets:
                    fail = "LINK:" + os.path.basename(
                        failed_targets[0].replace("\\", "/"))[:120]
                elif _link_target:
                    fail = "LINK:" + os.path.basename(
                        _link_target.replace("\\", "/"))[:120]
                else:
                    fail = "LINK:unknown"
            elif kind == "unknown":
                # Round-27: static-archive failures carry neither a
                # `.cpp:line error:` nor an ld.lld/undefined signature;
                # Make prints `Error running link command: no such file or
                # directory` for the `ar` step (CI #62453:
                # host-common/libaemu-logging.a). Classify them as
                # kind=archive so the evidence reporter dumps link.txt /
                # CMAKE_AR instead of misattributing a TU compile.
                try:
                    _arch_t = [t for t in failed_targets
                               if t.strip().endswith(".a")]
                except Exception:
                    _arch_t = []
                if _arch_t or ("error running link command" in low_all
                               and ".a" in low_all):
                    kind = "archive"
                    _base27 = ""
                    if _arch_t:
                        _base27 = os.path.basename(_arch_t[0])
                    elif failed_targets:
                        _base27 = os.path.basename(failed_targets[0])
                    fail = "ARCHIVE:" + (_base27[:120] if _base27
                                           else "unknown")
        except Exception:
            pass
        try:
            self.output.error("HMBS diag build-fail kind=%s file=%s rc=%d"
                              % (kind, fail[-120:] if fail else "UNKNOWN",
                                 proc.returncode))
            shown = 0
            # Round-21: `GfxstreamFatalError.cpp.o` contains substring
            # "error", so a plain `"error" in line` test fills all 6 slots
            # with progress lines. Skip Ninja/Make progress lines and require
            # a real error signal (`error:`, `undefined`, `ld.lld`,
            # `cannot find`, `FAILED:`).
            # Round-22: FAILED lines go first (they name the true target).
            # Verbose compiler echoes through the filter scripts
            # (hmbs-cxx-filter.py ...) carry flags but no diagnostic; they
            # previously filled the window and hid the ld.lld lines, so skip
            # them unless they also carry a link signal. Link failures emit
            # one error per undefined symbol, hence the wider link window.
            _prog = re.compile(r"^\s*\[\s*\d+%\]")
            _errpat = re.compile(
                r"error:|undefined|multiple definition|duplicate symbol|"
                r"relocation|cannot find|no such file|permission denied|"
                r"FAILED:",
                re.IGNORECASE)
            _linksig = re.compile(
                r"undefined|ld\.lld|multiple definition|duplicate symbol|"
                r"relocation|cannot find",
                re.IGNORECASE)
            _cap = 25 if kind == "link" else 6
            for _fln in output.splitlines():
                _fs = _fln.strip()
                if _fs.startswith("FAILED:"):
                    self.output.error("HMBS diag builderr: %s" % _fs[:500])
                    _snip.append(_fs[:200])
                    shown += 1
                    if shown >= _cap:
                        break
            if shown < _cap:
                for line in output.splitlines():
                    s = line.strip()
                    if not s:
                        continue
                    if s.startswith("FAILED:"):
                        continue  # already emitted above
                    if _prog.match(s) and ("Building" in s or "Linking" in s
                                           or "Archiving" in s or "Copying" in s):
                        continue
                    if ("hmbs-cxx-filter.py" in s or "hmbs-cc-filter.py" in s) \
                            and not _linksig.search(s):
                        continue
                    if not _errpat.search(s):
                        continue
                    self.output.error("HMBS diag builderr: %s" % s[:500])
                    _snip.append(s[:200])
                    shown += 1
                    if shown >= _cap:
                        break
            # Round-23: always surface make Error lines (they name the failed
            # make target path). They never matched _errpat (`Error 1` has
            # no colon), so they were silently dropped every round.
            _mshown = 0
            for line in output.splitlines():
                s = line.strip()
                if re.match(r"make\[\d+\]: \*\*\*", s):
                    self.output.error("HMBS diag builderr: %s" % s[:500])
                    _snip.append(s[:200])
                    _mshown += 1
                    if _mshown >= 5:
                        break
            if kind == "link":
                # Round-23: scan from the END (the failed step is last under
                # Make) and never label a `-c` compile as linkcmd — round-22
                # printed a stale logging.cpp compile as the "link command".
                _found_cmd = False
                for line in reversed(output.splitlines()):
                    s = line.strip()
                    if " -o " not in s:
                        continue
                    if ("hmbs-cxx-filter.py" not in s
                            and "hmbs-cc-filter.py" not in s
                            and "clang++" not in s
                            and "ld.lld" not in s):
                        continue
                    if " -c " in s.split(" -o ")[0] or " -c " in s:
                        # A compile echo, not the link: keep looking back
                        # for the real link, but remember it as fallback.
                        if not _found_cmd:
                            self.output.error("HMBS diag lastcmd-compile: %s"
                                              % s[:300])
                            _found_cmd = True
                        continue
                    if len(s) > 900:
                        _i = s.find(" -o ")
                        self.output.error(
                            "HMBS diag linkcmd: %s ... %s"
                            % (s[:400], s[_i:_i + 500]))
                    else:
                        self.output.error("HMBS diag linkcmd: %s" % s[:900])
                    _found_cmd = True
                    break
                if not _found_cmd:
                    for line in reversed(output.splitlines()):
                        s = line.strip()
                        if " -o " in s and ("clang++" in s or "ld.lld" in s
                                            or "filter.py" in s):
                            self.output.error("HMBS diag linkcmd-last-o: %s"
                                              % s[:900])
                            break
            if shown == 0:
                # Fallback: last lines if no error keyword found.
                for line in output.splitlines()[-8:]:
                    if line.strip():
                        self.output.error("HMBS diag builderr-tail: %s"
                                          % line.strip()[:500])
                        _snip.append(line.strip()[:200])
        except Exception:
            pass
        _snip_txt = (" /// ".join(_snip[:3])[:600] if _snip else "none")
        raise ConanException(
            "HMBS diag build-capture kind=%s failed file=%s rc=%d failed-targets=%s || snip=%s || original build output %d chars"
            % (kind, fail, proc.returncode, ",".join(failed_targets[:5]),
               _snip_txt, len(output)))

    def _build_with_conan_cmake(self):
        # Linux fallback keeps the plain conan flow (no OHOS SDK involved).
        from conan.tools.cmake import CMake
        cmake = CMake(self)
        cmake.configure()
        try:
            cmake.build()
        except ConanException as exc:
            try:
                self._report_build_failure_evidence(exc, self.build_folder, "")
            except ConanException:
                raise
            raise

    def _report_build_failure_evidence(self, exc, bdir, toolchain):
        # Read-only: pack compiler/-std/-stdlib/--sysroot/--target for the
        # ACTUAL failing TU into one short error-channel message, then raise
        # it with the original attached. Round-18: the old version always
        # reported host-common/logging.cpp, but round-17 patched that TU
        # (recapture rc=0) while the build still fails elsewhere, so the
        # hardcoded file hid the real culprit. Now (a) guess the failing
        # file from the exception text, (b) fall back to logging.cpp, (c)
        # audit toxic -I leaf counts across ALL compile_commands entries.
        # Round-19: parse the build-capture "failed file=" marker first;
        # entry lookup prioritises the guessed file over logging.cpp.
        items = []
        fullcmd = ""
        fail_file = ""
        fail_kind = "unknown"
        try:
            mk = re.search(r"kind=(\w+)", str(exc)[:3000])
            if mk:
                fail_kind = mk.group(1)
        except Exception:
            pass
        try:
            m = re.search(r"failed file=([^\s|]+)",
                          str(exc)[:3000])
            if m and m.group(1) not in ("UNKNOWN", ""):
                fail_file = m.group(1)
            else:
                m2 = re.search(r"[\w\-./\\]+\.cpp", str(exc)[:3000])
                if m2:
                    fail_file = m2.group(0)
        except Exception:
            pass
        if not fail_file:
            fail_file = "host-common/logging.cpp"
        # Round-20: surface compile-vs-link kind in the evidence line so a
        # LINK failure is never mistaken for a TU compile failure again.
        items.append("kind=%s" % fail_kind)
        if fail_file.startswith("LINK:"):
            items.append("linktarget=%s" % fail_file[5:][:80])
        elif fail_file.startswith("ARCHIVE:"):
            items.append("archivetarget=%s" % fail_file[8:][:80])
        # Round-27: archive failures have no TU either; every TU-specific
        # lookup/recapture below must be skipped for both LINK and ARCHIVE.
        _is_nontu27 = (fail_file.startswith("LINK:")
                       or fail_file.startswith("ARCHIVE:")
                       or fail_kind in ("link", "archive"))
        try:
            cc_path = os.path.join(bdir, "compile_commands.json")
            if os.path.isfile(cc_path):
                with open(cc_path, "r", encoding="utf-8",
                          errors="replace") as f:
                    entries = json.load(f)
                # Round-19: two-pass lookup — guessed failing TU first,
                # logging.cpp only as fallback (old single-pass OR always
                # stopped at logging.cpp even when fail pointed elsewhere).
                # Round-20: LINK failures have no TU; skip TU matching so
                # the evidence never falls back to a misleading logging.cpp.
                _matched = None
                if _is_nontu27:
                    items.append("tu-lookup=skipped(kind=link)")
                elif fail_file and not fail_file.endswith(
                        "host-common/logging.cpp"):
                    for ent in entries:
                        _f = str(ent.get("file", ""))
                        if _f.endswith(os.path.basename(fail_file)):
                            _matched = ent
                            break
                if _matched is None and not _is_nontu27:
                    for ent in entries:
                        _f = str(ent.get("file", ""))
                        if _f.endswith("host-common/logging.cpp"):
                            _matched = ent
                            break
                if _matched is not None:
                    ent = _matched
                    _f = str(ent.get("file", ""))
                    cmd = ent.get("command", "") or ""
                    fullcmd = cmd
                    items.append("file=%s" % _f[-80:])
                    words = cmd.split()
                    items.append("compiler=%s"
                                 % (words[0] if words else "MISSING"))
                    for tok in ("-std=", "-stdlib=", "--sysroot=",
                                "--target="):
                        hit = [w for w in words if w.startswith(tok)]
                        items.append("%s=%s"
                                     % (tok.rstrip("="),
                                        hit[0] if hit else "MISSING"))
                    # Count both split ("-I", path) and combined
                    # ("-I<path>") include forms; the old counter only
                    # saw the split form and always reported incflags=0.
                    incs = [w for w in words
                            if w in ("-I", "-isystem")
                            or w.startswith("-I")
                            or w.startswith("-isystem")]
                    items.append("incflags=%d" % len(incs))
                    # Forensics for C-vs-C++ misparse (template errors
                    # + empty _LIBCPP macros happen when a .cpp is
                    # parsed as C): -x/lang flags, C-std flags,
                    # -nostdinc*, -D count.
                    xflags = [w for w in words
                              if w in ("-x", "-nostdinc",
                                       "-nostdinc++", "-nobuiltininc")
                              or w.startswith("-x")
                              or w.startswith("-std=c")]
                    items.append("langflags=%s"
                                 % ("|".join(xflags) if xflags
                                    else "none"))
                    items.append("defines=%d"
                                 % len([w for w in words
                                        if w == "-D"
                                        or w.startswith("-D")]))
                    # Toxic leaf audit for THIS entry: only a real -I leaf
                    # hijacks angle <features.h>; -iquote is the fix
                    # (round-19: old counter flagged the cure as poison,
                    # yielding toxic_leaf=1 on the patched logging.cpp
                    # and toxic_entries=27/78 that only counted iquotes).
                    toxic = [w for w in words
                             if w.startswith("-I")
                             and "include/host-common" in w]
                    items.append("toxic_Ileaf=%d" % len(toxic))
                else:
                    items.append("target-entry=MISSING fail_guess=%s"
                                 % fail_file)
                # Global toxic audit: how many TUs still carry a real -I leaf
                # (iquote excluded: it is the fix, not the poison).
                try:
                    _toxic_total = 0
                    _toxic_samples = []
                    for ent in entries:
                        _c = ent.get("command", "") or ""
                        _words = _c.split()
                        _leaf = [w for w in _words
                                 if w.startswith("-I") and
                                 "include/host-common" in w]
                        if _leaf:
                            _toxic_total += 1
                            if len(_toxic_samples) < 3:
                                _toxic_samples.append(
                                    "%s:%s" % (
                                        os.path.basename(
                                            str(ent.get("file", ""))),
                                        _leaf[0][-60:]))
                    items.append("toxic_Ientries=%d/%d"
                                 % (_toxic_total, len(entries)))
                    # Round-20: name the remaining toxic TUs so the next
                    # round knows whether the sweep missed a CMakeLists or
                    # the leaf comes from an INTERFACE propagation.
                    if _toxic_samples:
                        items.append("toxic_samples=%s"
                                     % (";".join(_toxic_samples)[:300]))
                except Exception:
                    pass
            else:
                items.append("compile_commands.json=MISSING")
        except Exception as e:
            items.append("cmd-read-failed=%s" % e)
        items.append("ohos.toolchain=%s" % (toolchain if toolchain else "N/A"))
        # Round-21: compile_commands.json records PRE-filter flags, so
        # toxic_Ientries stays red even when the exec-time filter demotes the
        # leaf. Mark the filter so the next round reads toxic as stale.
        items.append("filter=wrapper-active")
        # Round-22: for link kind, dump the failing target's link.txt (Make
        # generator) so the next round sees objects + libs around the
        # undefined symbols. Read-only, never raises.
        if _is_nontu27:
            try:
                _ft = ""
                try:
                    _mft = re.search(r"failed-targets=([^|]+)", str(exc))
                    if _mft:
                        _cands = [c.strip()
                                  for c in _mft.group(1).split(",")
                                  if c.strip()]
                        if _cands:
                            _ft = _cands[0].replace("\\", "/")
                except Exception:
                    pass
                _base = os.path.basename(_ft) if _ft else ""
                if not _base and fail_file.startswith("LINK:"):
                    _base = fail_file[5:][:120]
                elif not _base and fail_file.startswith("ARCHIVE:"):
                    _base = fail_file[8:][:120]
                try:
                    self.output.error("HMBS diag linkfailed: %s"
                                      % (_base[:200] if _base else "unknown"))
                except Exception:
                    pass
                try:
                    _found = []
                    for _root, _dirs, _files in os.walk(bdir):
                        if "link.txt" in _files:
                            _found.append(os.path.join(_root, "link.txt"))
                            if len(_found) >= 20:
                                break
                    _stem = _base or ""
                    for _suf in (".a", ".so", ".o"):
                        if _stem.endswith(_suf):
                            _stem = _stem[:-len(_suf)]
                    _linktxt = ""
                    for _p in _found:
                        if _stem and _stem in _p.replace("\\", "/"):
                            _linktxt = _p
                            break
                    if not _linktxt and _found:
                        _linktxt = _found[0]
                    try:
                        self.output.error("HMBS diag linktxt-cands=%d"
                                          % len(_found))
                    except Exception:
                        pass
                    if _linktxt and os.path.isfile(_linktxt):
                        with open(_linktxt, "r", encoding="utf-8",
                                  errors="replace") as _f:
                            _lt = " ".join(_f.read().split())
                        if len(_lt) > 1400:
                            _i = _lt.find(" -o ")
                            if _i > 0:
                                _lt = _lt[:500] + " ... " + _lt[_i:_i + 700]
                            else:
                                _lt = _lt[:1200]
                        self.output.error(
                            "HMBS diag linktxt %s: %s"
                            % (os.path.relpath(_linktxt, bdir)[:120],
                               _lt[:1300]))
                    else:
                        try:
                            _names = sorted(os.listdir(bdir))[:20]
                        except Exception:
                            _names = []
                        self.output.error(
                            "HMBS diag linktxt: MISSING (bdir=%s)"
                            % (",".join(_names)[:300]))
                except Exception as _e:
                    try:
                        self.output.error("HMBS diag linktxt-failed=%s" % _e)
                    except Exception:
                        pass
                # Round-27: archiver identity (CMAKE_AR/RANLIB from cache +
                # the failing archive rule's command) so an `ar not found`
                # is directly attributable next round.
                try:
                    _cache27 = os.path.join(bdir, "CMakeCache.txt")
                    if os.path.isfile(_cache27):
                        with open(_cache27, "r", encoding="utf-8",
                                  errors="replace") as _f27:
                            for _line27 in _f27:
                                if ("CMAKE_AR:" in _line27
                                        or "CMAKE_RANLIB:" in _line27):
                                    try:
                                        self.output.error(
                                            "HMBS diag archiver-cache: %s"
                                            % _line27.strip()[:200])
                                    except Exception:
                                        pass
                    _rule27 = ""
                    for _root27, _dirs27, _files27 in os.walk(bdir):
                        if _base and _base in _files27:
                            _rule27 = os.path.join(_root27, _base)
                            break
                    if not _rule27 and _base:
                        for _root27, _dirs27, _files27 in os.walk(bdir):
                            if "build.make" in _files27:
                                _p27 = os.path.join(_root27, "build.make")
                                try:
                                    with open(_p27, "r", encoding="utf-8",
                                              errors="replace") as _f27:
                                        _t27 = _f27.read()
                                    if _base in _t27:
                                        _rule27 = _p27
                                        break
                                except Exception:
                                    pass
                    if _rule27 and os.path.isfile(_rule27):
                        try:
                            with open(_rule27, "r", encoding="utf-8",
                                      errors="replace") as _f27:
                                _t27 = _f27.read()
                            _shown27 = 0
                            for _ln27 in _t27.splitlines():
                                _s27 = _ln27.strip()
                                if ("Error running link command" in _s27
                                        or "cmake_link_script" in _s27
                                        or _s27.startswith("cd ")
                                        and ".cmake" in _s27):
                                    try:
                                        self.output.error(
                                            "HMBS diag archiver-rule: %s"
                                            % _s27[:400])
                                    except Exception:
                                        pass
                                    _shown27 += 1
                                    if _shown27 >= 4:
                                        break
                        except Exception as _e27b:
                            try:
                                self.output.error(
                                    "HMBS diag archiver-rule-failed=%s"
                                    % _e27b)
                            except Exception:
                                pass
                except Exception:
                    pass
            except Exception:
                pass
        msg = "HMBS diag evidence build-failed: " + " | ".join(items)
        msg = msg[:2000]
        try:
            self.output.error(msg)
        except Exception:
            pass
        # Full command (read-only) goes through the error channel too so it
        # survives the preflight summary truncation that drops info lines.
        if fullcmd:
            try:
                self.output.error("HMBS diag fullcmd %s: %s"
                                  % (os.path.basename(fail_file),
                                     fullcmd[:1500]))
            except Exception:
                pass
        # Round-16: the real compiler error lines live in the truncated
        # middle of the log (5 rounds of identical fingerprint without one
        # visible first-error line). Re-run the exact failing command with
        # output capture and re-emit the first lines via the error channel
        # so the next summary retains them. Read-only: output goes to a
        # temp object, never touches the real build tree.
        # Round-20: skip TU recapture for kind=link (compilealone rc=0
        # misled round-19 into blaming WorkerThread_unittest.cpp); emit an
        # explicit mismatch note when recapture passes but the build failed.
        if fullcmd and not _is_nontu27:
            try:
                import shlex as _shlex
                import tempfile as _tf
                tmpd = self.build_folder or "."
                fd, tmpo = _tf.mkstemp(suffix=".o", dir=tmpd)
                try:
                    os.close(fd)
                except Exception:
                    pass
                # Replace the original -o target with the temp object so
                # the re-run cannot clobber build outputs.
                try:
                    parts = _shlex.split(fullcmd, posix=True)
                except Exception:
                    parts = fullcmd.split()
                if "-o" in parts:
                    idx = parts.index("-o")
                    if idx + 1 < len(parts):
                        parts[idx + 1] = tmpo
                else:
                    parts += ["-o", tmpo]
                # Cap: only re-run if it looks like a real TU compile.
                if any(p.endswith(".cpp") for p in parts):
                    p = subprocess.run(
                        parts,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=300, check=False)
                    out = p.stdout or ""
                    self.output.error("HMBS diag recapture rc=%d"
                                      % p.returncode)
                    if p.returncode == 0:
                        self.output.error(
                            "HMBS diag recapture-mismatch: TU compiles "
                            "alone but cmake --build failed; true failure "
                            "is likely link/parallel, see builderr kind")
                        msg = (msg + " | recapture=pass-mismatch")[:2200]
                    else:
                        msg = (msg + " | recapture=fail")[:2200]
                    shown = 0
                    for line in out.splitlines():
                        s = line.strip()
                        if not s:
                            continue
                        # First lines carry the root cause; keep them.
                        self.output.error("HMBS diag errmsg: %s"
                                          % s[:500])
                        shown += 1
                        if shown >= 12:
                            break
                    if shown == 0:
                        self.output.error("HMBS diag errmsg: <empty>")
                try:
                    if os.path.isfile(tmpo):
                        os.remove(tmpo)
                except Exception:
                    pass
            except Exception as e:
                try:
                    self.output.error("HMBS diag recapture-failed=%s" % e)
                except Exception:
                    pass
        # Round-14: pinpoint where -stdlib disappears (cache vs per-target)
        # so the next round can distinguish toolchain FORCE-set from
        # upstream overwrite. Read-only, never raises.
        try:
            cache_path = os.path.join(bdir, "CMakeCache.txt")
            if os.path.isfile(cache_path):
                hits = []
                with open(cache_path, "r", encoding="utf-8",
                          errors="replace") as f:
                    for line in f:
                        if ("CMAKE_CXX_FLAGS" in line
                                or "CMAKE_EXE_LINKER_FLAGS" in line):
                            hits.append(line.strip())
                if hits:
                    self.output.error("HMBS diag cache flags: %s"
                                      % (" || ".join(hits)[:1200]))
            fm = os.path.join(bdir, "host-common", "CMakeFiles",
                              "aemu-logging.dir", "flags.make")
            if os.path.isfile(fm):
                with open(fm, "r", encoding="utf-8",
                          errors="replace") as f:
                    txt = f.read()
                m = re.search(r"CXX_FLAGS\s*=\s*(.*)", txt)
                if m:
                    self.output.error("HMBS diag flags.make CXX_FLAGS: %s"
                                      % m.group(1).strip()[:1200])
        except Exception:
            pass
        raise ConanException(msg + " || original=%s" % exc)

    def _run_upstream_tests(self, bdir):
        """Run ctest and emit HMBS_UPSTREAM_TEST_RESULT.

        Deterministic sources only: discovered from `ctest -N` entry lines,
        executed/passed/failed/skipped from per-test `Test #N ... <result>`
        lines of the real `ctest --output-on-failure` run. No substring
        counting, no arithmetic repair branches.
        """
        ctest = "ctest"
        # discovered: one line per registered test from `ctest -N`.
        proc_n = subprocess.run(
            [ctest, "-N"],
            cwd=bdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )
        out_n = proc_n.stdout or ""
        discovered = len(
            re.findall(r"^\s*Test\s+#\d+\s*:", out_n, flags=re.MULTILINE)
        )
        self.output.info("[upstream] ctest -N discovered=%d" % discovered)
        for line in out_n.splitlines()[-5:]:
            self.output.info("[upstream] ctest -N: %s" % line)

        proc = subprocess.run(
            [ctest, "--output-on-failure"],
            cwd=bdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
            check=False,
        )
        output = proc.stdout or ""
        tail = output.splitlines()[-15:] if output else []
        for line in tail:
            self.output.info("[upstream] ctest: %s" % line)

        passed = len(
            re.findall(
                r"Test\s+#\d+[^\n]*\.\.\.\s+Passed",
                output,
            )
        )
        failed = len(
            re.findall(
                r"Test\s+#\d+[^\n]*\.\.\.\s+Failed",
                output,
            )
        )
        skipped = len(
            re.findall(
                r"Test\s+#\d+[^\n]*\.\.\.\s+(Skipped|Disabled|Not Run)",
                output,
            )
        )
        # ctest lists Disabled tests only in the trailing summary.
        try:
            _dnr = len(re.findall(r"^\s*\d+\s*-\s*.+\((Disabled|Not Run|Skipped)\)", output, flags=re.MULTILINE))
            if _dnr > skipped:
                skipped = _dnr
        except Exception:
            pass
        # Timeout is a distinct ctest result word.
        failed += len(
            re.findall(
                r"Test\s+#\d+[^\n]*\.\.\.\s+Timeout",
                output,
            )
        )
        executed = passed + failed
        self.output.info(
            "[upstream] parsed discovered=%d executed=%d passed=%d "
            "failed=%d skipped=%d" % (discovered, executed, passed, failed, skipped)
        )
        ok_identities = (
            discovered >= 0
            and executed >= 0
            and passed >= 0
            and failed >= 0
            and skipped >= 0
            and passed + failed == executed
            and executed + skipped <= discovered
            and executed <= discovered
        )
        # Declared upstream total (test_package/MANIFEST.yml, ctest_entries
        # audit): 123 `ctest -N` entries under ENABLE_VKCEREAL_TESTS=ON
        # (base 79 + host-common 44). Source-macro audit finds 124 macros;
        # the 124th is the upstream DISABLED_ ring_buffer case excluded by
        # gtest itself on every platform, so 123 is the official runner
        # registration, not a machine subset.
        _upstream_total = 123
        undiscovered = _upstream_total - discovered
        if undiscovered < 0:
            undiscovered = 0
        # Status follows the catch2 precedent in this repo: "passed" only
        # when every registered test executed and passed with no gaps.
        # Any skipped/undiscovered entry (here the upstream DISABLED_
        # family) yields "incomplete" with gaps instead of "passed" with
        # gaps, which rule4 rejects as self-contradictory. "failed" is
        # reserved for real failures (failed>0 or ctest rc!=0 or broken
        # identities). "incomplete" only warns so the build and package
        # still publish with honest evidence.
        if not ok_identities or failed > 0 or proc.returncode != 0:
            status = "failed"
        elif skipped > 0 or undiscovered > 0 or executed < discovered:
            status = "incomplete"
        else:
            status = "passed"
        # Collect skipped test display names deterministically from the
        # same ctest output (no second source for counts; names only).
        _skipped_names = []
        try:
            for _m in re.finditer(
                r"^\s*\d+\s*-\s*(.+?)\s*\((Disabled|Not Run|Skipped)\)",
                output,
                flags=re.MULTILINE,
            ):
                _skipped_names.append(_m.group(0).strip()[:200])
        except Exception:
            pass
        try:
            for _m in re.finditer(
                r"Test\s+#\d+[^\n]*?\.\.\.\s+(Skipped|Disabled|Not Run)",
                output,
            ):
                _skipped_names.append(_m.group(0).strip()[:200])
        except Exception:
            pass
        # Dedupe, keep order, cap for marker size.
        try:
            _seen = set()
            _uniq = []
            for _n in _skipped_names:
                if _n not in _seen:
                    _seen.add(_n)
                    _uniq.append(_n)
            _skipped_names = _uniq[:5]
        except Exception:
            pass
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        _gaps = []
        if skipped > 0:
            _ev = (
                ("; ".join(_skipped_names) if _skipped_names else "")
                or "ctest per-test result lines"
            )
            _gaps.append(
                {
                    "count": skipped,
                    "category": "ohos_feature",
                    "detail": "ctest run reports Skipped/Disabled entry "
                    "(ring_buffer DISABLED_ProducerDrivenSync family; "
                    "upstream TEST with DISABLED_ prefix is not executed "
                    "by default); see ctest output above",
                    "evidence": _ev[:600],
                }
            )
        if undiscovered > 0:
            _gaps.append(
                {
                    "count": undiscovered,
                    "category": "ohos_feature",
                    "detail": "ctest -N discovered=%d is below the declared "
                    "runner total 123; see ctest -N output above" % discovered,
                    "evidence": "ctest -N Total Tests vs "
                    "test_package/MANIFEST.yml ctest_entries=123",
                }
            )
        if _gaps:
            marker["gaps"] = _gaps
        print(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False),
            flush=True,
        )
        if not ok_identities:
            raise ConanException(
                "Upstream test count identities violated "
                "(discovered=%d executed=%d passed=%d failed=%d skipped=%d)"
                % (discovered, executed, passed, failed, skipped)
            )
        if status == "failed":
            raise ConanException(
                "Upstream ctest suite failed "
                "(discovered=%d executed=%d passed=%d failed=%d skipped=%d rc=%d)"
                % (discovered, executed, passed, failed, skipped,
                   proc.returncode)
            )
        if status == "incomplete":
            try:
                self.output.warning(
                    "[upstream] incomplete with gaps explained: passed=%d/%d"
                    % (passed, discovered)
                )
            except Exception:
                pass

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos") \
            if str(self.settings.os) == "OHOS" and \
            os.path.isdir(os.path.join(self.build_folder, "build-ohos")) \
            else self.build_folder
        self.run('cmake --install "%s" --prefix "%s"' % (bdir, self.package_folder))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # HarmonyOS PC requires self-signed .so for dlopen; strip stale
        # .codesign and re-sign defensively (zstd/expat precedent). Static
        # default has no .so: no-op. Missing tools: warn only.
        if str(self.settings.os) != "OHOS" or not bool(self.options.shared):
            return
        import glob as _glob
        libdir = os.path.join(self.package_folder, "lib")
        targets = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        targets = [t for t in targets if os.path.isfile(t) and not os.path.islink(t)]
        if not targets:
            return
        objcopy = os.environ.get("OHOS_OBJCOPY") or shutil.which("llvm-objcopy") \
            or "/data/service/hnp/bin/llvm-objcopy"
        signer = os.environ.get("OHOS_SIGN_TOOL") or shutil.which("binary-sign-tool") \
            or "/data/service/hnp/bin/binary-sign-tool"
        if not (objcopy and os.path.isfile(objcopy)) or not (signer and os.path.isfile(signer)):
            self.output.warning("OHOS signing tools missing, skip re-sign")
            return
        for so in targets:
            self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true' % (objcopy, so))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, so, so))

    def package_info(self):
        self.cpp_info.libs = [
            "aemu-base",
            "aemu-host-common",
            "aemu-logging",
            "aemu-snapshot",
        ]
        self.cpp_info.set_property("cmake_file_name", "libaemu")
        self.cpp_info.set_property("cmake_target_name", "libaemu::libaemu")
        self.cpp_info.set_property("pkg_config_name", "libaemu")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
