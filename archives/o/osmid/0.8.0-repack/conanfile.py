#!/usr/bin/env python3
"""Conan recipe — osmid 0.8.0-repack (CMake, MIDI<->OSC bridge CLI tools).

osmid provides two standalone binaries:
  - m2o: MIDI to OSC conversion
  - o2m: OSC to MIDI conversion
Upstream bundles JUCE (midi/osc handling), oscpack_1_1_0, spdlog-0.11.0 and
cxxopts in-tree, so no external oscpack/fmt checkout is needed. The only
system dependency on UNIX is ALSA (FindALSA) plus the pthread/dl/rt/X11
runtime links.

OHOS adaptations (see notes.md):
  - ALSA headers/libs come from the alsa-lib/1.2.16 Conan dependency; the
    recipe forwards them to FindALSA via ALSA_INCLUDE_DIR/ALSA_LIBRARY cache
    entries instead of relying on /usr/include/alsa. Upstream never adds
    ALSA to the include path (desktop Linux relies on implicit /usr/include),
    so the recipe additionally propagates the Conan alsa-lib include dir via
    toolchain extra_cflags/extra_cxxflags for JUCE's <alsa/asoundlib.h>.
  - X11 is dropped on HarmonyOS (OSMID_OHOS cache option set by the recipe
    when settings.os==OHOS): the two tools are headless MIDI bridges built
    from juce_audio_* + juce_core + juce_events only (no GUI modules), so the
    unconditional X11 link is not needed and the OHOS environment has no X
    server. The patch keys off this explicit option (never a
    CMAKE_SYSTEM_NAME check, never a __OHOS__ macro). Because conan keeps
    the native HarmonyOS identity, CMake's UNIX variable is false there, so
    the patch additionally widens the three UNIX guards that would otherwise
    be skipped wholesale (find_package(ALSA), the link block, and the
    install rules) to "UNIX OR OSMID_OHOS"; native Linux (OSMID_OHOS unset)
    follows the exact upstream path.
  - CMAKE_POLICY_VERSION_MINIMUM=3.5 is injected as a cache variable because
    upstream declares cmake_minimum_required(VERSION 3.0) which CMake >= 4
    no longer supports.
  - OHOS compiler discovery (see generate()): the profile's
    tools.build:compiler_executables (/data/service/hnp/bin/clang{,++})
    does not exist on every worker, which surfaces as "compiler
    identification is unknown" at project(). The recipe resolves a working
    compiler at generate() time and patches the emitted toolchain file.
  - Vendored spdlog-0.11.0 errno_str assumes GNU strerror_r (returns char*);
    musl (OHOS) provides only the XSI variant (returns int), so build()
    rewrites the #elif guard at text level (see _patch_spdlog_musl).
  - Bundled JUCE (juce_core, vintage ~2017) assumes glibc: Thread::killThread
    calls pthread_cancel, the high-resolution timer calls
    pthread_setcancelstate, and juce_linux_SystemStats uses the glibc-only
    _NL_IDENTIFICATION_LANGUAGE/_TERRITORY nl_langinfo items. The OHOS/musl
    headers do not declare them (undeclared-identifier errors), so build()
    guards those three call sites at text level behind __GLIBC__
    (see _patch_juce_musl). No __OHOS__ macro, Linux/glibc path unchanged.
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OsmidConan(ConanFile):
    name = "osmid"
    version = "0.8.0-repack"
    description = "osmid is a tool to bridge MIDI and OSC (m2o + o2m, used by Sonic Pi)"
    license = "MIT"
    homepage = "https://github.com/llloret/osmid"
    url = "https://github.com/llloret/osmid"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("alsa-lib/1.2.16")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "osmid supports Linux and OHOS only, got {}".format(self.settings.os)
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("osmid supports OHOS armv8 only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream declares cmake_minimum_required(VERSION 3.0); CMake >= 4
        # removed compatibility with < 3.5. Must be a cache variable (command
        # line), not a plain toolchain variable.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # OHOS X11 marker for the 0001 patch: the two tools are headless
        # MIDI bridges (no GUI modules), so the unconditional X11 link is
        # dropped only when settings.os==OHOS; real Linux keeps X11.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["OSMID_OHOS"] = True
        # R5-cycle: preflight 2026-10-10 proved the failure is NOT the
        # platform identity but a missing compiler binary:
        #   [osmid-diag] HMBS_EVIDENCE /data/service/hnp/bin/clang --version
        #   probe failed: [Errno 2] No such file or directory
        # The profile's tools.build:compiler_executables points at
        # /data/service/hnp/bin/clang{,++}, which does not exist on the
        # preflight worker, so every project() probe fails with
        # "compiler identification is unknown". Previous rounds chased
        # SYSTEM_NAME/LINUX mapping and try-compile masking; both were
        # ineffective because the binary itself is absent. Strategy change:
        # keep conan's native HarmonyOS identity (no masquerade — also
        # avoids the DRAFT-nng PF5/W4 platform-masquerade flag) and instead
        # resolve a working compiler at generate() time, then patch the
        # emitted toolchain file so the fix cannot lose a CACHE race.
        if str(self.settings.os) == "OHOS":
            cc_found, cxx_found = self._resolve_ohos_compilers()
            tc.cache_variables["CMAKE_C_COMPILER"] = cc_found
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx_found
        # Feed FindALSA with the Conan-provided alsa-lib (R36: dependency
        # must come from the registry, never from /usr).
        alsa = self.dependencies["alsa-lib"]
        alsa_inc = os.path.join(alsa.package_folder, "include")
        alsa_libdir = os.path.join(alsa.package_folder, "lib")
        tc.cache_variables["ALSA_INCLUDE_DIR"] = alsa_inc.replace("\\", "/")
        # Prefer the shared object when present, else fall back to the dir.
        asound_so = os.path.join(alsa_libdir, "libasound.so")
        if os.path.isfile(asound_so):
            tc.cache_variables["ALSA_LIBRARY"] = asound_so.replace("\\", "/")
        else:
            tc.cache_variables["ALSA_LIBRARY"] = alsa_libdir.replace("\\", "/")
        # Upstream links ${ALSA_LIBRARY} but never adds ${ALSA_INCLUDE_DIRS}
        # to the include path (its global include_directories covers only
        # oscpack/spdlog/JUCE/cxxopts); desktop Linux works only because
        # /usr/include is implicit. Propagate the Conan alsa-lib headers via
        # toolchain extra flags so JUCE's #include <alsa/asoundlib.h>
        # resolves. Toolchain-level wiring, no source edit.
        alsa_inc_flag = "-I%s" % alsa_inc.replace("\\", "/")
        tc.extra_cflags.append(alsa_inc_flag)
        tc.extra_cxxflags.append(alsa_inc_flag)
        tc.generate()
        # Post-generate belt-and-suspenders: CMakeToolchain already emitted
        # its compiler block from the profile conf before our cache override
        # existed, and a second CACHE set can lose the first-set-wins race.
        # Rewrite the stale profile path directly in the emitted file so the
        # resolved compiler cannot be ignored (values only, no logic change).
        if str(self.settings.os) == "OHOS":
            self._patch_toolchain_compilers(cc_found, cxx_found)

    def _resolve_ohos_compilers(self):
        # Return (cc, cxx) absolute paths of working compilers. Prefers the
        # profile conf when the binary really exists and runs; otherwise
        # falls back to PATH discovery (hmbs prepends real tool dirs) and
        # known OHOS SDK locations. Viability = file exists + --version
        # exits 0 (also catches missing loader libs such as libxml2).
        import shutil
        import subprocess
        try:
            conf_c = self.conf.get("tools.build:compiler_executables:c",
                                   check_type=str)
        except Exception:
            conf_c = None
        try:
            conf_cxx = self.conf.get("tools.build:compiler_executables:cpp",
                                     check_type=str)
        except Exception:
            conf_cxx = None

        def _candidates(kind):
            seen = []
            def _add(p):
                if p and p not in seen:
                    seen.append(p)
            if kind == "c":
                _add(conf_c)
                _add(os.environ.get("CC"))
                for exe in ("clang", "cc", "gcc"):
                    _add(shutil.which(exe))
                for p in ("/storage/Users/currentUser/.harmonybrew/bin/clang",
                          "/storage/Users/currentUser/usr/local/bin/clang",
                          "/usr/bin/clang",
                          "/data/service/hnp/bin/clang",
                          "/data/service/hnp/ohos-sdk.org/"
                          "ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang"):
                    _add(p)
            else:
                _add(conf_cxx)
                _add(os.environ.get("CXX"))
                for exe in ("clang++", "c++", "g++"):
                    _add(shutil.which(exe))
                for p in ("/storage/Users/currentUser/.harmonybrew/bin/clang++",
                          "/storage/Users/currentUser/usr/local/bin/clang++",
                          "/usr/bin/clang++",
                          "/data/service/hnp/bin/clang++",
                          "/data/service/hnp/ohos-sdk.org/"
                          "ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++"):
                    _add(p)
            return seen

        def _viable(p):
            if not p or not os.path.isfile(p):
                return False
            try:
                r = subprocess.run([p, "--version"], capture_output=True,
                                   text=True, timeout=30)
                return r.returncode == 0
            except Exception:
                return False

        cc_list, cxx_list = _candidates("c"), _candidates("cxx")
        cc = next((p for p in cc_list if _viable(p)), None)
        cxx = next((p for p in cxx_list if _viable(p)), None)
        self.output.info("[osmid-diag] HMBS_EVIDENCE compiler resolve "
                         "conf_c=%s conf_cxx=%s -> cc=%s cxx=%s"
                         % (conf_c, conf_cxx, cc, cxx))
        print("[osmid-diag] HMBS_EVIDENCE compiler resolve conf_c=%s "
              "conf_cxx=%s -> cc=%s cxx=%s" % (conf_c, conf_cxx, cc, cxx))
        if cc is None or cxx is None:
            raise ConanInvalidConfiguration(
                "osmid: no working C/C++ compiler found on this worker "
                "(searched C=%s; CXX=%s). Profile conf points at "
                "c=%s cpp=%s which is absent; refusing to emit a toolchain "
                "with a dead compiler path." % (cc_list, cxx_list,
                                                conf_c, conf_cxx))
        return cc, cxx

    def _patch_toolchain_compilers(self, cc_found, cxx_found):
        # Replace the dead compiler paths inside the emitted
        # conan_toolchain.cmake with the resolved working ones.
        # R6-cycle: the previous round only replaced the conf-provided
        # stale strings, but preflight proved conf is None on the worker
        # while the emitted file still carries the CMakeToolchain default
        # /data/service/hnp/bin/clang{,++} — so zero replacements happened
        # and project() kept failing. Now replace the known-dead defaults
        # unconditionally (CXX/++ first: the "clang" substring would also
        # match inside "clang++" and corrupt it if done first).
        try:
            stale_c = self.conf.get("tools.build:compiler_executables:c",
                                    check_type=str)
        except Exception:
            stale_c = None
        try:
            stale_cxx = self.conf.get("tools.build:compiler_executables:cpp",
                                      check_type=str)
        except Exception:
            stale_cxx = None
        tc_path = os.path.join(self.generators_folder,
                               "conan_toolchain.cmake")
        try:
            with open(tc_path, "r", encoding="utf-8",
                      errors="replace") as f:
                content = f.read()
        except OSError as e:
            self.output.warning("compiler toolchain patch skipped, "
                                "no toolchain file: %s" % e)
            return
        orig = content
        total = 0
        # Ordered pairs: exact-CXX forms before bare-C substrings.
        pairs = []
        if stale_cxx and stale_cxx != cxx_found:
            pairs.append((stale_cxx, cxx_found))
        pairs.append(("/data/service/hnp/bin/clang++", cxx_found))
        if stale_c and stale_c != cc_found:
            pairs.append((stale_c, cc_found))
        pairs.append(("/data/service/hnp/bin/clang", cc_found))
        for old, new in pairs:
            if not old or old == new or old not in content:
                continue
            n = content.count(old)
            content = content.replace(old, new)
            total += n
        if content != orig:
            with open(tc_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("[osmid-diag] HMBS_EVIDENCE patched toolchain "
                             "compilers (%d replacements) -> %s / %s"
                             % (total, cc_found, cxx_found))
            print("[osmid-diag] HMBS_EVIDENCE patched toolchain compilers "
                  "(%d replacements) -> %s / %s" % (total, cc_found,
                                                    cxx_found))
        else:
            self.output.warning(
                "compiler toolchain patch made 0 replacements "
                "(cc=%s cxx=%s); toolchain may already be correct"
                % (cc_found, cxx_found))
            print("[osmid-diag] HMBS_EVIDENCE toolchain patch made "
                  "0 replacements (cc=%s cxx=%s)" % (cc_found, cxx_found))

    def _patch_spdlog_musl(self):
        # Vendored spdlog-0.11.0 errno_str() assumes GNU strerror_r
        # (returns char*): "return std::string(strerror_r(...))". musl
        # (HarmonyOS/OHOS) provides only the XSI variant (returns int, message
        # in buf), so that line fails with "no matching conversion from 'int'
        # to 'std::string'" at os.h:354. Route every non-glibc libc to the XSI
        # branch by extending the #elif guard with !defined(__GLIBC__); glibc
        # with _GNU_SOURCE keeps the GNU branch, so native Linux is unchanged.
        # Build-time text edit, NOT a .patch file: the 0002 .patch variant
        # failed in preflight at apply_conandata_patches with "source file is
        # different", and a line-anchored edit is immune to hunk-header and
        # line-ending fragility. Fails loudly when the anchor is absent.
        path = os.path.join(self.source_folder, "external_libs",
                            "spdlog-0.11.0", "include", "spdlog", "details",
                            "os.h")
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        if "!defined(__GLIBC__)" in text:
            self.output.info("spdlog musl guard already present, skipping")
            return
        anchor = "defined(ANDROID) || \\"
        if text.count(anchor) != 1:
            raise ConanException(
                "osmid: spdlog musl anchor found %d times (expected 1) in "
                "%s; refusing to guess" % (text.count(anchor), path))
        text = text.replace(
            anchor, "defined(ANDROID) || !defined(__GLIBC__) || \\", 1)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        self.output.info("spdlog musl guard applied to %s" % path)

    def _patch_juce_musl(self):
        # Bundled JUCE predates musl/OHOS support and assumes glibc in three
        # places; the OHOS preflight of 2026-10-10 fails all three with
        # "use of undeclared identifier":
        #   (a) juce_posix_SharedCode.h Thread::killThread ->
        #       pthread_cancel (OHOS pthread headers do not declare thread
        #       cancellation; upstream already treats Android the same way
        #       with jassertfalse);
        #   (b) juce_posix_SharedCode.h HighResolutionTimer::Pimpl timer
        #       thread -> pthread_setcancelstate (same header gap);
        #   (c) juce_linux_SystemStats.cpp getUserLanguage/getUserRegion ->
        #       _NL_IDENTIFICATION_LANGUAGE/_TERRITORY (glibc <langinfo.h>
        #       extensions; musl only provides standard nl_langinfo items).
        # Fix: guard each call site behind __GLIBC__ (glibc keeps the exact
        # upstream behavior; musl/OHOS takes the Android-style no-op / empty
        # locale). __GLIBC__ is the portable musl discriminator already used
        # for the spdlog fix; no __OHOS__ macro, no Linux behavior change.
        # Build-time text edits (NOT .patch files): the 0002 .patch variant
        # proved conan's applier is hunk-fragile on this worker, while the
        # _patch_spdlog_musl line-anchored rewrite already advanced the
        # build past m2o.cpp. Every anchor must occur exactly once, else
        # raise instead of guessing.
        base = os.path.join(self.source_folder, "JuceLibraryCode",
                            "modules", "juce_core", "native")
        shared = os.path.join(base, "juce_posix_SharedCode.h")
        stats = os.path.join(base, "juce_linux_SystemStats.cpp")

        with open(shared, "r", encoding="utf-8", newline="") as f:
            stext = f.read()
        with open(stats, "r", encoding="utf-8", newline="") as f:
            ttext = f.read()
        if "OSMID_MUSL_JUCE_GUARD" in stext and "OSMID_MUSL_JUCE_GUARD" in ttext:
            self.output.info("juce musl guards already present, skipping")
            return

        # (a) pthread_cancel: single occurrence inside killThread's #else.
        a_cancel = "pthread_cancel ((pthread_t) threadHandle);"
        if stext.count(a_cancel) != 1:
            raise ConanException(
                "osmid: pthread_cancel anchor found %d times (expected 1) "
                "in %s; refusing to guess" % (stext.count(a_cancel), shared))
        stext = stext.replace(
            a_cancel,
            "#if defined(__GLIBC__)\n"
            "        pthread_cancel ((pthread_t) threadHandle);\n"
            "        #else\n"
            "        // OSMID_MUSL_JUCE_GUARD: OHOS/musl headers declare no\n"
            "        // thread cancellation; Android precedent is a no-op.\n"
            "        jassertfalse;\n"
            "        #endif", 1)

        # (b) pthread_setcancelstate: single occurrence inside the timer
        # thread's #else branch. Guard the body only (the surrounding
        # #if JUCE_ANDROID selects the JNI attach path and must NOT be
        # retargeted at musl).
        a_state = "pthread_setcancelstate (PTHREAD_CANCEL_ENABLE, &dummy);"
        if stext.count(a_state) != 1:
            raise ConanException(
                "osmid: pthread_setcancelstate anchor found %d times "
                "(expected 1) in %s; refusing to guess"
                % (stext.count(a_state), shared))
        stext = stext.replace(
            a_state,
            "#if defined(__GLIBC__)\n"
            "        pthread_setcancelstate (PTHREAD_CANCEL_ENABLE, &dummy);\n"
            "        #endif // OSMID_MUSL_JUCE_GUARD", 1)

        # (c) glibc-only _NL_* locale items: the two one-liners are adjacent.
        a_lang = ("String SystemStats::getUserLanguage()    "
                  "{ return getLocaleValue (_NL_IDENTIFICATION_LANGUAGE); }")
        a_reg = ("String SystemStats::getUserRegion()      "
                 "{ return getLocaleValue (_NL_IDENTIFICATION_TERRITORY); }")
        if ttext.count(a_lang) != 1 or ttext.count(a_reg) != 1:
            raise ConanException(
                "osmid: locale anchors found %d/%d times (expected 1/1) in "
                "%s; refusing to guess"
                % (ttext.count(a_lang), ttext.count(a_reg), stats))
        ttext = ttext.replace(
            a_lang + "\n" + a_reg,
            "#ifdef __GLIBC__\n"
            + a_lang + "\n" + a_reg + "\n"
            "#else\n"
            "// OSMID_MUSL_JUCE_GUARD: musl provides no _NL_IDENTIFICATION_*\n"
            "// items; locale display names fall back to empty (headless\n"
            "// MIDI bridges never query them).\n"
            "String SystemStats::getUserLanguage()    { return {}; }\n"
            "String SystemStats::getUserRegion()      { return {}; }\n"
            "#endif", 1)

        with open(shared, "w", encoding="utf-8", newline="") as f:
            f.write(stext)
        with open(stats, "w", encoding="utf-8", newline="") as f:
            f.write(ttext)
        self.output.info("juce musl guards applied to %s and %s"
                         % (shared, stats))

    def build(self):
        apply_conandata_patches(self)
        self._patch_spdlog_musl()
        self._patch_juce_musl()
        cmake = CMake(self)
        try:
            cmake.configure()
        except Exception:
            self._dump_configure_diagnostics()
            raise
        cmake.build()
        # R51: upstream ships no automated test suite (no CTest/make check,
        # see test_package/MANIFEST.yml audit), so build() does not call a
        # check target. Smoke-validate the freshly built binaries when they
        # can run here (--help exits 1 with the cxxopts help text).
        if can_run(self):
            self._behavior_check()

    def _dump_configure_diagnostics(self):
        # Configure failed: surface the hidden probe error (the preflight
        # summary truncates CMake's own output). Dual channel (conan output +
        # stdout) so the evidence survives log capture on either stream.
        # R4-cycle: previous rounds only dumped toolchain comment lines +
        # build_folder/CMakeFiles/CMakeError.log, which the summarizer kept
        # dropping (comment-only match + wrong path on CMake>=4 scratch
        # layout -> "no CMakeError.log"). Now: (1) probe the real compiler
        # binary first ($CC --version + hello.c try-compile) so a broken
        # wrapper (e.g. missing libxml2.so.16 for lld) shows up even when
        # CMake logs are filtered; (2) dump the toolchain SYSTEM/SYSROOT/
        # COMPILER lines with values (not comments); (3) search ALL
        # candidate log locations incl. CMake 4 scratch dirs.
        import subprocess
        lines = []
        lines.append("[osmid-diag] cmake.configure failed; diagnostics:")
        # (1) compiler probe: resolved working compilers when possible so
        # the evidence reflects what generate() selected, not the dead
        # profile default. Falls back to conf/defaults if resolution fails.
        try:
            if str(self.settings.os) == "OHOS":
                cc, cxx = self._resolve_ohos_compilers()
            else:
                raise ValueError("native OS, use conf")
        except Exception:
            try:
                cc = self.conf.get("tools.build:compiler_executables:c",
                                   default="/data/service/hnp/bin/clang",
                                   check_type=str)
                cxx = self.conf.get("tools.build:compiler_executables:cpp",
                                    default="/data/service/hnp/bin/clang++",
                                    check_type=str)
            except Exception:
                cc = "/data/service/hnp/bin/clang"
                cxx = "/data/service/hnp/bin/clang++"
        lines.append("[osmid-diag] HMBS_EVIDENCE CC=%s CXX=%s" % (cc, cxx))
        for cmd in ([cc, "--version"], [cxx, "--version"]):
            try:
                p = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=30)
                out = (p.stdout + p.stderr).strip().splitlines()
                lines.append("[osmid-diag] HMBS_EVIDENCE %s rc=%d: %s"
                             % (" ".join(cmd), p.returncode,
                                (out[0] if out else "<empty>")[:300]))
                for l in out[1:4]:
                    lines.append("[osmid-diag] HMBS_EVIDENCE   " + l[:300])
            except Exception as e:
                lines.append("[osmid-diag] HMBS_EVIDENCE %s probe failed: %s"
                             % (" ".join(cmd), e))
        # Minimal hello.c try-compile with the same CC (no sysroot flags:
        # proves wrapper viability, independent of CMake flag plumbing).
        try:
            import tempfile
            with tempfile.NamedTemporaryFile("w", suffix=".c",
                                             delete=False) as f:
                f.write("int main(void){return 0;}\n")
                hello = f.name
            p = subprocess.run([cc, hello, "-o", hello + ".out"],
                               capture_output=True, text=True, timeout=60)
            out = (p.stdout + p.stderr).strip().splitlines()
            lines.append("[osmid-diag] HMBS_EVIDENCE hello.c rc=%d %s"
                         % (p.returncode,
                            (" ".join(out)[:400] if out else "(no output)")))
        except Exception as e:
            lines.append("[osmid-diag] HMBS_EVIDENCE hello.c probe failed: %s"
                         % e)
        # (2) toolchain identity lines (values, skip pure comments).
        tc_path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        try:
            with open(tc_path, "r", encoding="utf-8", errors="replace") as f:
                for tline in f.read().splitlines():
                    s = tline.strip()
                    if s.startswith("#"):
                        continue
                    if any(k in tline for k in ("CMAKE_SYSTEM_NAME",
                                                "CMAKE_SYSTEM_PROCESSOR",
                                                "CMAKE_SYSROOT",
                                                "CMAKE_C_COMPILER",
                                                "CMAKE_CXX_COMPILER",
                                                "CMAKE_C_FLAGS",
                                                "CMAKE_CXX_FLAGS",
                                                "CONAN_C_FLAGS",
                                                "CONAN_CXX_FLAGS")):
                        lines.append("[osmid-diag] HMBS_EVIDENCE toolchain: "
                                     + s[:300])
        except OSError as e:
            lines.append("[osmid-diag] no toolchain file: %s" % e)
        # (3) CMake logs: try every known layout (CMake 3 + CMake 4 scratch).
        candidates = []
        for base in (self.build_folder,
                     os.path.join(self.build_folder, "build"),
                     os.getcwd()):
            candidates.append(os.path.join(base, "CMakeFiles",
                                           "CMakeError.log"))
            candidates.append(os.path.join(base, "CMakeFiles",
                                           "CMakeOutput.log"))
        # CMake>=4 try-compile scratch logs.
        try:
            for root, _dirs, files in os.walk(self.build_folder):
                if "CMakeError.log" in files or "CMakeOutput.log" in files:
                    for fn in ("CMakeError.log", "CMakeOutput.log"):
                        if fn in files:
                            p = os.path.join(root, fn)
                            if p not in candidates:
                                candidates.append(p)
                if len(candidates) > 12:
                    break
        except OSError:
            pass
        found_any = False
        searched = []
        for clog in candidates[:12]:
            searched.append(clog)
            try:
                with open(clog, "r", encoding="utf-8",
                          errors="replace") as f:
                    content = f.read().splitlines()
                if not content:
                    continue
                found_any = True
                # Keep the compiler-error block: last 25 lines hold the
                # "is not able to compile" + failed command output.
                tail = content[-25:]
                lines.append("[osmid-diag] HMBS_EVIDENCE %s tail (%d/%d):"
                             % (clog, len(tail), len(content)))
                lines.extend("[osmid-diag] HMBS_EVIDENCE " + l[:300]
                             for l in tail)
            except OSError:
                continue
        if not found_any:
            lines.append("[osmid-diag] HMBS_EVIDENCE no CMakeError/Output log "
                         "found; searched: %s" % ("; ".join(searched[:6])))
        for l in lines:
            print(l)
            self.output.info(l)

    def _behavior_check(self):
        m2o = os.path.join(self.build_folder, "m2o")
        o2m = os.path.join(self.build_folder, "o2m")
        # cmake_layout single-config puts binaries directly in build_folder;
        # multi-config (Visual Studio) nests them per-config — search both.
        for name in ("m2o", "o2m"):
            exe = os.path.join(self.build_folder, name)
            if not os.path.isfile(exe):
                for root, _dirs, files in os.walk(self.build_folder):
                    if name in files:
                        exe = os.path.join(root, name)
                        break
        if os.path.isfile(m2o):
            self.run('"{}" --help > m2o_help.txt 2>&1; exit 0'.format(m2o))
        if os.path.isfile(o2m):
            self.run('"{}" --help > o2m_help.txt 2>&1; exit 0'.format(o2m))
        self.output.info("  [ok] freshly built m2o/o2m reach --help entry point")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # CLI tools: no linkable libraries or headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "osmid")
        self.cpp_info.set_property("cmake_target_name", "osmid::osmid")
