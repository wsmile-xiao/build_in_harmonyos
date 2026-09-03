#!/usr/bin/env python3
"""Conan recipe - nymphcast 0.2-alpha0 (Makefile).

NymphCast is an audio/video casting system. This recipe builds the
nymphcast_server receiver application from the upstream Makefile
(src/server/Makefile).

Upstream has no CMakeLists.txt - only GNU Make. The Makefile supports
TOOLCHAIN=clang and uses clang.mk (GPP=clang++, GCC=clang).

Source is fetched from the official git repo pinned to the immutable
commit behind the v0.2-alpha0 tag (git commits are content-addressed, so
no sha256 is needed and the source is reproducible). The gitcode mirror
mirrors the official GitHub repo.

Dependencies: nymphrpc, libnymphcast and sdl2_image are published on
ohpcd (nymphrpc/v0.1.1, libnymphcast/v0.2.1, sdl2_image/2.6.0) and are
declared in requirements(). FFmpeg is pinned to 6.1.6 because the
upstream ffplay fork (src/server/ffplay) uses the legacy avfft.h /
av_rdft API which was removed in FFmpeg 7+.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy
from conan.tools.scm import Git


class NymphcastConan(ConanFile):
    name = "nymphcast"
    version = "0.2-alpha0"
    description = "Audio/video casting and streaming receiver application"
    license = "BSD-3-Clause"
    homepage = "https://github.com/MayaPosch/NymphCast"
    url = "https://github.com/MayaPosch/NymphCast"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    _HNP_BIN = "/data/service/hnp/bin"

    def _resolve_make(self):
        # Resolve make from PATH first (the CI profile buildenv adds
        # /data/service/hnp/bin to PATH for build scripts); fall back to
        # the standard OHOS toolchain directory (git/clang also live
        # there). NOTE: tools.build:make_executable is NOT registered by
        # the OHOS-adapted Conan 2.29.1, so self.conf.get() raises
        # ConanException -- do not use it here.
        import shutil
        found = shutil.which("make")
        if found:
            return found
        return os.path.join(self._HNP_BIN, "make")

    def requirements(self):
        self.requires("poco/1.15.3")
        self.requires("ffmpeg/6.1.6")  # upstream ffplay fork uses legacy avfft.h API (removed in FFmpeg 7+)
        self.requires("nymphrpc/v0.1.1")
        self.requires("libnymphcast/v0.2.1")
        self.requires("sdl2_image/2.6.0")
        self.requires("sdl2/2.30.10")
        self.requires("freetype/2.14.3")
        self.requires("curl/8.15.0")
        self.requires("freeimage/3.18.0")
        self.requires("rapidjson/1.1.0")
        # force=True: openssl must be BOTH a direct dependency (so its
        # package_folder resolves for include collection) AND force the
        # version over the conflicting transitive pins (poco 3.5.6 vs
        # curl 3.5.6.1). override=True alone makes it override-only and
        # Conan 2 exposes package_folder=None for override nodes.
        self.requires("openssl/3.5.6.1", force=True)

    def source(self):
        source = self.conan_data["sources"]
        # exports_sources ("patches/*") is copied into the source folder, so it
        # is not empty; clone into a subdir and move the tree up.
        tmp = os.path.join(self.source_folder, ".src_tmp")
        git = Git(self)
        git.clone(
            url=source["git"],
            target=tmp,
            args=["--depth", "1", "--branch", source["tag"]],
        )
        for entry in os.listdir(tmp):
            src = os.path.join(tmp, entry)
            dst = os.path.join(self.source_folder, entry)
            if os.path.isdir(dst):
                import shutil
                shutil.rmtree(dst)
            elif os.path.exists(dst):
                os.remove(dst)
            os.rename(src, dst)
        os.rmdir(tmp)
        # Verify the immutable commit behind the tag.
        head_file = os.path.join(self.source_folder, ".git", "HEAD")
        with open(head_file, encoding="utf-8") as handle:
            actual_commit = handle.read().strip()
        tag = source["tag"]
        expected = source["commit"]
        if actual_commit != expected:
            raise ConanInvalidConfiguration(
                "Tag " + tag + " resolved to " + actual_commit + ", expected " + expected
            )

    def _iter_deps(self):
        seen = set()
        for dep in self.dependencies.values():
            name = dep.ref.name
            if name in seen:
                continue
            seen.add(name)
            yield name, dep

    def _collect_includes(self):
        flags = []
        for dep_name, dep in self._iter_deps():
            base = getattr(dep, "package_folder", None)
            if base:
                # include root (handles components with empty top-level cpp_info)
                inc = os.path.join(base, "include")
                if os.path.isdir(inc) and inc not in flags:
                    flags.append("-I" + inc)
                # SDL2 headers live under include/SDL2/; GUI stack uses
                # <SDL_joystick.h> (no SDL2/ prefix). Inject the subdir too.
                if dep_name == "sdl2":
                    sub = os.path.join(inc, "SDL2")
                    if os.path.isdir(sub) and sub not in flags:
                        flags.append("-I" + sub)
                # freetype2 headers live under include/freetype2/
                # (ft2build.h is included as <ft2build.h> by the GUI stack).
                if dep_name == "freetype":
                    sub = os.path.join(inc, "freetype2")
                    if os.path.isdir(sub) and sub not in flags:
                        flags.append("-I" + sub)
            elif dep_name == "openssl":
                # openssl is a direct requirement (force=True), so its
                # package_folder should be resolved; fall back to scanning the
                # local cache if Conan still reports None for the node.
                inc = self._openssl_include_from_dep(dep) or self._openssl_include_from_cache()
                if inc and inc not in flags:
                    flags.append("-I" + inc)
        return flags

    def _openssl_include_from_dep(self, dep):
        # openssl is declared with force=True, so it is a direct requirement
        # and its package_folder should be set. Resolve the include root from
        # the dependency node itself (preferred over cache scanning).
        base = getattr(dep, "package_folder", None)
        if base:
            inc = os.path.join(base, "include")
            if os.path.isfile(os.path.join(inc, "openssl", "opensslv.h")):
                return inc
        return None

    def _openssl_include_from_cache(self):
        # Fallback: scan the local cache for an openssl package include root.
        # Conan 2 reports package_folder=None for override-only dependency
        # nodes; this recipe declares openssl with force=True so the direct
        # node normally resolves, but if a Conan version changes that behavior
        # the cache scan keeps the build working. The ~/.conan2/p layout is
        # Conan 2.x specific -- re-check on Conan 3 upgrades.
        try:
            cache_root = os.path.join(
                os.path.expanduser("~"), ".conan2", "p")
            if not os.path.isdir(cache_root):
                return None
            for entry in os.listdir(cache_root):
                if not entry.startswith("opens"):
                    continue
                inc = os.path.join(cache_root, entry, "p", "include")
                if os.path.isfile(os.path.join(inc, "openssl", "opensslv.h")):
                    return inc
        except Exception:
            pass
        return None

    def _collect_libdirs(self):
        flags = []
        for dep_name, dep in self._iter_deps():
            if dep.package_folder:
                base = dep.package_folder
                lib = os.path.join(base, "lib")
                if os.path.isdir(lib) and lib not in flags:
                    flags.append("-L" + lib)
            # Makefile derives -lSDL2 from `sdl2-config --libs`, which does
            # not exist on OHOS. sdl2 package exposes libSDL2.a directly.
            if dep_name == "sdl2":
                flags.append("-lSDL2")
        return flags

    def build(self):
        apply_conandata_patches(self)

        include_flags = " ".join(self._collect_includes())
        libdir_flags = " ".join(self._collect_libdirs())

        # The compat header (patch 0004) lives in src/server/. Sub-makes
        # (e.g. angelscript) run from other CWDs, so make the server source
        # dir an explicit include root for the `-include ohos_pthread_compat.h`
        # injection to resolve from any sub-make.
        server_dir = os.path.join(self.source_folder, "src", "server")
        if os.path.isdir(server_dir):
            include_flags += " -I" + server_dir

        # lcdapi uses GNU pthread cancellation API; OHOS pthread.h lacks the
        # declarations (symbols exist in device libc). Inject the compat header
        # into every TU so lcdapi sources compile.
        compat = "-include ohos_pthread_compat.h"
        cxx_flags = include_flags + " " + compat
        env_prefix = ("CFLAGS=" + repr(include_flags) + " CXXFLAGS=" + repr(cxx_flags)
                      + " PLATFORM_LDFLAGS=" + repr(libdir_flags))
        make = self._resolve_make()
        self.run(env_prefix + " " + make + " -C src/server TOOLCHAIN=clang -j1")

        # Upstream tests (howard-hinnant-date precedent): build and run the
        # compilable src/test binaries + client under a controlled dummy-SDL
        # env, recording evidence. Script tests are recorded as blocked
        # because upstream test_server is build-blocked (stale nymphrpc API).
        self._build_and_run_upstream_tests(include_flags, libdir_flags)

    def _resolve_cxx(self):
        import shutil
        found = shutil.which("clang++")
        if found:
            return found
        return os.path.join(self._HNP_BIN, "clang++")

    def _test_ld_library_path(self):
        libs = []
        for _, dep in self._iter_deps():
            base = getattr(dep, "package_folder", None)
            if base:
                lib = os.path.join(base, "lib")
                if os.path.isdir(lib) and lib not in libs:
                    libs.append(lib)
        try:
            import subprocess
            out = subprocess.check_output(
                [os.path.join(self._HNP_BIN, "clang"),
                 "--print-file-name=libc++_shared.so"],
                text=True).strip()
            d = os.path.dirname(out)
            if d and d not in libs:
                libs.append(d)
        except Exception:
            pass
        return ":".join(libs)

    def _build_and_run_upstream_tests(self, include_flags, libdir_flags):
        # Upstream src/test binaries built/run inside build() under a
        # controlled dummy-SDL env (howard-hinnant-date precedent). Real exit
        # codes are recorded; known upstream defects are reported, never faked
        # as PASS (H3). Script tests fail because test_server is build-blocked
        # by the upstream stale pre-2021 nymphrpc API (verified upstream).
        cxx = self._resolve_cxx()
        src = self.source_folder
        wt = os.path.join(src, ".upstream-tests")
        objd = os.path.join(wt, "obj")
        bind = os.path.join(wt, "bin")
        logd = os.path.join(wt, "logs")
        for d in (objd, bind, logd):
            os.makedirs(d, exist_ok=True)
        ldpath = self._test_ld_library_path()
        envpre = ("SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy LC_ALL=C "
                  "LANG=C LD_LIBRARY_PATH=" + ldpath)
        tinc = include_flags + " -Isrc/server/ffplay -Isrc/server -Isrc"
        cpp = "-std=c++17 -g3 -O0 -pthread " + tinc
        ffplay = ["audio_renderer", "clock", "decoder", "frame_queue",
                  "packet_queue", "player", "sdl_renderer", "stream_handler",
                  "subtitle_handler", "video_renderer"]
        objs = []
        for name in ffplay:
            o = os.path.join(objd, name + ".o")
            self.run(cxx + " -c -o " + o + " src/server/ffplay/" + name
                     + ".cpp " + cpp + " -DTESTING")
            objs.append(o)

        def _cc(out, srcf, extra=""):
            self.run(cxx + " -c -o " + out + " " + srcf + " " + cpp + extra)
            return out

        db = _cc(os.path.join(objd, "databuffer.o"), "src/server/databuffer.cpp")
        tf = _cc(os.path.join(objd, "test_ffplay.o"),
                 "src/test/test_ffplay_local_file.cpp", " -DTESTING")
        sg = _cc(os.path.join(objd, "ohos_server_glue.o"),
                 "src/test/ohos_server_glue.cpp")
        fg = _cc(os.path.join(objd, "ohos_ffplay_globals.o"),
                 "src/test/ohos_ffplay_globals.cpp")
        sc = _cc(os.path.join(objd, "screensaver.o"), "src/server/screensaver.cpp")
        ct = _cc(os.path.join(objd, "chronotrigger.o"),
                 "src/server/chronotrigger.cpp")
        ts = _cc(os.path.join(objd, "test_screensaver.o"),
                 "src/test/test_screensaver.cpp")

        tlibs = (libdir_flags + " -lPocoFoundation -lPocoNet -lswscale -lavcodec "
                 "-lavdevice -lavformat -lavutil -lswresample -lavfilter "
                 "-lSDL2_image -ltiff -lwebp -pthread")

        ffbin = os.path.join(bind, "test_ffplay_local_file")
        self.run(cxx + " -o " + ffbin + " " + " ".join(objs + [db, tf, sg])
                 + " " + tlibs)
        ssbin = os.path.join(bind, "test_screensaver")
        self.run(cxx + " -o " + ssbin + " " + " ".join(
            [sc, ct, ts, fg, sg] + objs + [db]) + " " + tlibs)

        # client
        ncc = os.path.join(objd, "NymphCastClient.o")
        self.run(cxx + " -c -o " + ncc + " src/client/NymphCastClient.cpp "
                 + "-std=c++17 -g3 -pthread " + include_flags + " -Isrc/client"
                 + " -D__VERSION=\\\"v0.1-release.20220408\\\"")
        sa = os.path.join(objd, "sarge.o")
        self.run(cxx + " -c -o " + sa + " src/client/sarge.cpp "
                 + "-std=c++17 -g3 -pthread " + include_flags + " -Isrc/client")
        cbin = os.path.join(bind, "nymphcast_client")
        self.run(cxx + " -o " + cbin + " " + ncc + " " + sa + " "
                 + libdir_flags + " -lnymphcast -lnymphrpc -lPocoNet -lPocoUtil "
                 + "-lPocoFoundation -lPocoJSON -pthread")

        def _run(tag, cwd, cmdline, timeout):
            log = os.path.join(logd, tag + ".log")
            exitf = os.path.join(logd, tag + ".exit")
            self.run("cd " + cwd + " && " + envpre + " timeout " + str(timeout)
                     + " " + cmdline + " > " + log + " 2>&1; echo $? > " + exitf,
                     ignore_errors=True)
            rc = "?"
            if os.path.isfile(exitf):
                with open(exitf) as fh:
                    rc = fh.read().strip()
            self.output.info("upstream-test %s exit=%s (see %s)" % (tag, rc, log))
            return rc

        # Run under the controlled env. test_screensaver: upstream test never
        # calls setDataPath, so only the "abort, no images" path runs (exit 0).
        _run("test_screensaver", bind, "./test_screensaver", 120)

        # test_ffplay_local_file needs a media file named exactly as the test
        # hardcodes (Big_Buck_Bunny_1080_10s_30MB.mp4). Generate a short MPEG
        # with the ffmpeg binary from the ffmpeg dependency, then run it.
        rund = os.path.join(wt, "run-ffplay")
        os.makedirs(rund, exist_ok=True)
        media = os.path.join(rund, "Big_Buck_Bunny_1080_10s_30MB.mp4")
        ffmpeg_bin = None
        for dep_name, dep in self._iter_deps():
            if dep_name == "ffmpeg":
                cand = os.path.join(dep.package_folder, "bin", "ffmpeg")
                if os.path.isfile(cand):
                    ffmpeg_bin = cand
                    break
        if ffmpeg_bin:
            self.run("cd " + rund + " && " + envpre + " " + ffmpeg_bin
                     + " -y -f lavfi -i testsrc=duration=8:size=320x224:rate=30"
                     + " -f lavfi -i sine=frequency=440:duration=8"
                     + " -c:v mpeg1video -c:a mp2 Big_Buck_Bunny_1080_10s_30MB.mp4"
                     + " > " + os.path.join(logd, "ffmpeg-gen.log") + " 2>&1",
                     ignore_errors=True)
            if os.path.isfile(media):
                _run("test_ffplay_local_file", rund, ffbin, 150)
            else:
                self.output.warning("upstream-tests: media generation failed; "
                                    "test_ffplay_local_file not run")
        else:
            self.output.warning("upstream-tests: ffmpeg binary not found; "
                                "test_ffplay_local_file not run")

        # Script tests need test_server, which upstream cannot build (stale
        # pre-2021 nymphrpc API, verified). Stage the layout the scripts
        # expect (bin/test_server absent, client binary present) and record the
        # resulting failure as evidence -- never a fake PASS.
        std = os.path.join(wt, "scripts")
        os.makedirs(os.path.join(std, "bin"), exist_ok=True)
        cli = os.path.join(wt, "client", "bin")
        os.makedirs(cli, exist_ok=True)
        import shutil
        shutil_copy = shutil.copy
        shutil_copy(cbin, os.path.join(cli, "nymphcast_client"))
        if os.path.isfile(media):
            shutil_copy(media, os.path.join(cli, "amv_test.mpg"))
        for script in ("test_file_seeking.sh", "test_file_transfer.sh"):
            sp = os.path.join(src, "src", "test", script)
            shutil_copy(sp, os.path.join(std, script))
            _run(script, std, "sh " + script, 60)

        # Evidence summary (for CI log and downstream review).
        ev = os.path.join(wt, "upstream-tests-summary.txt")
        with open(ev, "w") as fh:
            fh.write("test_screensaver,test_ffplay_local_file,"
                     "test_file_seeking.sh,test_file_transfer.sh\n")
            for tag in ("test_screensaver", "test_ffplay_local_file",
                        "test_file_seeking.sh", "test_file_transfer.sh"):
                ef = os.path.join(logd, tag + ".exit")
                if os.path.isfile(ef):
                    with open(ef) as e:
                        fh.write(tag + "=" + e.read().strip() + "\n")
                else:
                    fh.write(tag + "=not-run\n")
        self.output.info("upstream-tests evidence: " + ev)

    def package(self):
        server_dir = os.path.join(self.source_folder, "src", "server")
        # The Makefile emits the binary under bin/<triple>/nymphcast_server
        # (TARGET_BIN includes the toolchain triple). Match it recursively and
        # flatten into package bin/ so the executable is on the conanrun PATH.
        copy(self, "**/nymphcast_server", os.path.join(server_dir, "bin"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.ini", server_dir, os.path.join(self.package_folder, "etc", "nymphcast"))
        copy(self, "*.jpg", server_dir, os.path.join(self.package_folder, "share", "nymphcast", "wallpapers"))
        src_apps = os.path.join(server_dir, "apps")
        if os.path.isdir(src_apps):
            copy(self, "*", src_apps, os.path.join(self.package_folder, "share", "nymphcast", "apps"))

    def package_info(self):
        self.cpp_info.libs = []
