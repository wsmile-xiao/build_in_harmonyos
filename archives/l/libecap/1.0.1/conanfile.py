#!/usr/bin/env python3
"""Conan recipe — libecap 1.0.1 (Autotools).

eCAP library: C++ API for implementing ICAP content analysis and adaptation
(Squid/eCAP content-adaptation interface). Autotools build
(./configure && make && make check && make install) with no external
dependencies. Upstream ships no formal suite (audited: no test sources and no
TESTS targets in the release tarball); `make check` is kept for traceability
and followed by a build-tree smoke linking .libs/libecap.a (Version/Name/Area).
"""

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import glob
import json
import os
import shutil


def _pick_writable_tmpdir(build_folder=None):
    # HMBS true-machine /tmp is read-only (erofs). clang, configure and
    # mktemp all need a writable TMPDIR. The injected value (HMBS_TMPDIR /
    # TMPDIR / HMBS_PLATFORM_CAPABILITIES.tmpdir) may be unset, missing or
    # unwritable in some workers, which surfaces as
    # "C compiler cannot create executables" (Error 77) with
    # "unable to make temporary file: Read-only file system" hidden in
    # config.log. Probe candidates with a real file write (HMDFS ignores
    # chmod / os.access, so makedirs alone is not enough) and fall back to
    # the conan build folder, which is guaranteed writable.
    candidates = []
    candidates.append(os.environ.get("HMBS_TMPDIR"))
    caps = os.environ.get("HMBS_PLATFORM_CAPABILITIES")
    if caps:
        try:
            candidates.append(json.loads(caps).get("tmpdir"))
        except Exception:
            pass
    candidates.append(os.environ.get("TMPDIR"))
    candidates.append(os.environ.get("TMP"))
    candidates.append(os.environ.get("TEMP"))
    if build_folder:
        candidates.append(os.path.join(build_folder, ".tmp"))
        candidates.append(os.path.join(build_folder, "hmbs-tmp"))
    home = os.environ.get("HOME")
    if home:
        candidates.append(os.path.join(home, "tmp"))
    for cand in candidates:
        if not cand:
            continue
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".tmp-write-probe")
            with open(probe, "w") as _pf:
                _pf.write("ok")
            os.unlink(probe)
            return cand
        except OSError:
            continue
    return None


def _cc_candidates(kind="cc"):
    # Profile pins /data/service/hnp/bin/clang{,++}, but the latest
    # preflight proves it dead under /bin/sh:
    #   /bin/sh: /data/service/hnp/bin/clang: inaccessible or not found
    # Probe live locations instead. HMBS puts shims/tools under
    # /storage/.../usr/local/bin and harmonybrew exists on host.
    if kind == "cxx":
        names = ("clang++", "c++", "g++")
        env_keys = ("CXX", "HMBS_CXX", "HMBS_CXX_COMPILER")
        extra = [
            "/storage/Users/currentUser/usr/local/bin/clang++",
            "/storage/Users/currentUser/.harmonybrew/bin/clang++",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang++",
            "/data/service/hnp/bin/clang++",
        ]
    else:
        names = ("clang", "cc", "gcc")
        env_keys = ("CC", "HMBS_CC", "HMBS_C_COMPILER")
        extra = [
            "/storage/Users/currentUser/usr/local/bin/clang",
            "/storage/Users/currentUser/.harmonybrew/bin/clang",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/clang",
            "/data/service/hnp/bin/clang",
        ]
    cands = []
    for key in env_keys:
        val = os.environ.get(key, "")
        if val:
            cands.append(val.split()[0])
    cands.extend(extra)
    for name in names:
        found = shutil.which(name)
        if found:
            cands.append(found)
    # De-dup, keep order.
    seen = set()
    ordered = []
    for cand in cands:
        if cand and cand not in seen:
            seen.add(cand)
            ordered.append(cand)
    return ordered


def _find_lld():
    # OHOS ships only ld.lld (no bare ld) and the clang driver does not
    # search PATH for the linker, so configure's compile+link probe
    # ("checking whether the C compiler works") fails without an explicit
    # -fuse-ld=<abs path>. Candidates cover the hnp toolchain, the OHOS
    # SDK llvm dir referenced by the ohos-aarch64 profile, and PATH.
    candidates = [
        os.environ.get("HMBS_LLD"),
        "/data/service/hnp/bin/ld.lld",
        "/data/service/hnp/bin/ld",
        "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/ld.lld",
        "/storage/Users/currentUser/usr/local/bin/ld.lld",
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand
    for name in ("ld.lld", "ld"):
        found = shutil.which(name)
        if found and os.path.isfile(found):
            return found
    # Last resort: llvm bindir next to the configured clang, if resolvable.
    for var in ("CC", "CXX"):
        comp = os.environ.get(var, "")
        if comp:
            bindir = os.path.dirname(comp.split()[0])
            for leaf in ("ld.lld", "ld"):
                cand = os.path.join(bindir, leaf)
                if os.path.isfile(cand):
                    return cand
    return None


def _effective_shell():
    # HMBS injects SHELL=/bin/sh (see HMBS_PLATFORM_CAPABILITIES.shell).
    # Old templates defaulted to /data/service/hnp/bin/bash, which is
    # inaccessible on the current host (configure: ".../bash: inaccessible
    # or not found" -> config.sub Error 127). Prefer the injected shell
    # and never fall back to the dead hnp path.
    for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL")):
        if cand and cand != "/data/service/hnp/bin/bash":
            return cand
    return "/bin/sh"


def _patch_configure_umask(source_folder, output):
    # E011 / HMFS: autoconf-generated `configure` runs `umask 077` before
    # `mktemp -d ./confXXXXXX`. On HMFS that yields a drwx--S--- dir owned
    # by a mapped UID, so the follow-up write of subs1.awk/subs1.sed fails
    # with `Permission denied` -> `config.status: error: could not setup
    # config files machinery` (this round's compile failure, capabilities
    # chmod:0 + local_mktemp:1 + readonly_tmp). Replace with `umask 022`
    # so the temp dir stays writable. Covers both the mktemp and the
    # mkdir fallback branches, including the copy embedded in the
    # config.status template inside `configure`. Deliberately no
    # mktemp-exit-1 shim: with HMBS_CAP_CHMOD=0 the shim cannot be made
    # executable and the mkdir fallback still carries `umask 077`.
    patched = 0
    try:
        names = os.listdir(source_folder)
    except OSError:
        return 0
    for name in names:
        if name != "configure":
            continue
        path = os.path.join(source_folder, name)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError:
            continue
        count = content.count("umask 077")
        if not count:
            continue
        content = content.replace("umask 077", "umask 022")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        except OSError:
            continue
        patched += count
        try:
            output.info("hmbs_umask: patched %d umask 077 -> 022 in %s" % (count, name))
        except Exception:
            pass
    return patched


_TR1_FALLBACK_HEADER = """/* (C) 2008 The Measurement Factory - HMBS portability fallback */\n#ifndef LIBECAP__COMMON_MEMORY_H\n#define LIBECAP__COMMON_MEMORY_H\n\n#include <libecap/common/libecap.h>\n\n// Modern toolchains (e.g. clang libc++ 15+) no longer ship <tr1/memory>.\n// Prefer it when available, otherwise fall back to C++11 <memory>.\n#if defined(__has_include)\n#  if __has_include(<tr1/memory>)\n#    include <tr1/memory>\nnamespace libecap {\nusing std::tr1::weak_ptr;\nusing std::tr1::shared_ptr;\n} // namespace libecap\n#  else\n#    include <memory>\nnamespace libecap {\nusing std::weak_ptr;\nusing std::shared_ptr;\n} // namespace libecap\n#  endif\n#else\n#  include <memory>\nnamespace libecap {\nusing std::weak_ptr;\nusing std::shared_ptr;\n} // namespace libecap\n#endif\n\n#endif\n"""


def _patch_libtool_chmod(build_folder, output):
    # HMBS_CAP_CHMOD=0: the generated `libtool` script's
    # old_postinstall_cmds runs `chmod 644 $oldlib` after installing the
    # static archive. On HMFS chmod is unsupported, so neutralize just the
    # mode-setting word with the ash builtin `:` (always exits 0, ignores
    # its arguments) and keep the companion `$RANLIB $oldlib` intact.
    # Only touches `chmod 644` / `chmod 755`; `chmod +x` (wrapper scripts)
    # is a different pattern and is left alone. Idempotent.
    if not build_folder or not os.path.isdir(build_folder):
        return 0
    patched = 0
    for dirpath, _dirnames, filenames in os.walk(build_folder):
        for name in filenames:
            if name != "libtool":
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue
            orig = content
            content = content.replace("chmod 644", ":")
            content = content.replace("chmod 755", ":")
            if content == orig:
                continue
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
            except OSError:
                continue
            patched += 1
            try:
                output.info("hmbs_chmod: neutralized chmod in %s" % path)
            except Exception:
                pass
    return patched


def _package_artifacts_ok(conanfile):
    # Minimal presence check for what `make install` must produce:
    # library + libecap headers + pkg-config file.
    try:
        pkg = conanfile.package_folder
    except Exception:
        return True
    try:
        shared = bool(conanfile.options.shared)
    except Exception:
        shared = False
    libdir = os.path.join(pkg, "lib")
    if shared:
        libs_ok = bool(glob.glob(os.path.join(libdir, "libecap.so*")))
    else:
        libs_ok = os.path.isfile(os.path.join(libdir, "libecap.a"))
    headers_ok = os.path.isfile(
        os.path.join(pkg, "include", "libecap", "common", "libecap.h"))
    pc_ok = os.path.isfile(os.path.join(libdir, "pkgconfig", "libecap.pc"))
    return libs_ok and headers_ok and pc_ok


def _copyfile_nomod(src, dst, output=None):
    # shutil.copyfile copies content only (no copystat -> no chmod
    # attempt), which is what HMBS_CAP_CHMOD=0 needs. Recreate symlinks
    # as symlinks (HMBS_CAP_SYMLINK=1); otherwise plain copy.
    try:
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if os.path.islink(src):
            target = os.readlink(src)
            try:
                if os.path.islink(dst) or os.path.exists(dst):
                    os.unlink(dst)
            except OSError:
                pass
            os.symlink(target, dst)
        else:
            try:
                if os.path.islink(dst) or os.path.exists(dst):
                    os.unlink(dst)
            except OSError:
                pass
            shutil.copyfile(src, dst)
        return True
    except OSError as exc:
        try:
            output.warning("hmbs_install: copy %s -> %s failed: %s" % (src, dst, exc))
        except Exception:
            pass
        return False


def _manual_install_fallback(conanfile):
    # Last-resort top-up when `make install` cannot complete on HMFS
    # (observed: libtool's `install -c` shim exits 0 without creating
    # DESTDIR/lib/libecap.a, then its `chmod 644` dies with ENOENT).
    # Reproduces exactly the upstream install layout (libdir, pkgincludedir
    # = includedir/libecap/{common,adapter,host}, pkgconfig) with plain
    # Python copies, no chmod/install-tool dependency. Additive: never
    # deletes what `make install` already placed.
    output = conanfile.output
    try:
        src = conanfile.source_folder
    except Exception:
        src = None
    try:
        bld = conanfile.build_folder
    except Exception:
        bld = None
    try:
        pkg = conanfile.package_folder
    except Exception:
        return False
    try:
        shared = bool(conanfile.options.shared)
    except Exception:
        shared = False
    copied = 0
    if bld and os.path.isdir(bld):
        lib_patterns = ["src/libecap/.libs/libecap.a"] if not shared else []
        lib_patterns += ["src/libecap/.libs/libecap.so*",
                         "src/libecap/.libs/libecap.la",
                         "src/libecap/libecap.la"]
        for pat in lib_patterns:
            for cand in glob.glob(os.path.join(bld, pat)):
                if not (os.path.isfile(cand) or os.path.islink(cand)):
                    continue
                if _copyfile_nomod(
                        cand, os.path.join(pkg, "lib", os.path.basename(cand)), output):
                    copied += 1
                    try:
                        output.info("hmbs_install: fallback lib %s" % os.path.basename(cand))
                    except Exception:
                        pass
        for cand in glob.glob(os.path.join(bld, "libecap.pc")):
            if os.path.isfile(cand):
                if _copyfile_nomod(
                        cand, os.path.join(pkg, "lib", "pkgconfig", "libecap.pc"), output):
                    copied += 1
    if src and os.path.isdir(src):
        for sub in ("common", "adapter", "host"):
            srcdir = os.path.join(src, "src", "libecap", sub)
            if not os.path.isdir(srcdir):
                continue
            for leaf in os.listdir(srcdir):
                if not leaf.endswith(".h"):
                    continue
                # autoconf.h is configure-generated; the source tree copy
                # (if any) is stale. It is topped up from the build tree
                # below instead.
                if leaf == "autoconf.h":
                    continue
                cand = os.path.join(srcdir, leaf)
                if os.path.isfile(cand):
                    if _copyfile_nomod(
                            cand,
                            os.path.join(pkg, "include", "libecap", sub, leaf),
                            output):
                        copied += 1
        if bld:
            for cand in glob.glob(
                    os.path.join(bld, "src", "libecap", "common", "autoconf.h")):
                if os.path.isfile(cand):
                    if _copyfile_nomod(
                            cand,
                            os.path.join(pkg, "include", "libecap", "common",
                                         "autoconf.h"),
                            output):
                        copied += 1
    try:
        output.info("hmbs_install: fallback copied %d files" % copied)
    except Exception:
        pass
    return _package_artifacts_ok(conanfile)


def _patch_tr1_memory(source_folder, output):
    # Upstream src/libecap/common/memory.h hard-codes `#include <tr1/memory>`
    # (2008-era). harmonybrew clang libc++ removed TR1 -> `fatal error:
    # 'tr1/memory' file not found` at area.lo. Rewrite the file in place
    # (no .patch file: avoids conan patch-parser hunk-count brittleness
    # that failed preflight with `extra lines for hunk no.1`). Idempotent:
    # skip when no `tr1/memory` reference remains.
    if not source_folder:
        return False
    path = os.path.join(source_folder, "src", "libecap", "common", "memory.h")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        return False
    if "tr1/memory" not in content:
        return False
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_TR1_FALLBACK_HEADER)
    except OSError:
        return False
    try:
        output.info("hmbs_tr1: rewrote src/libecap/common/memory.h with <memory> fallback")
    except Exception:
        pass
    return True


class LibecapConan(ConanFile):
    name = "libecap"
    version = "1.0.1"
    description = "eCAP library: C++ API for content analysis and adaptation (ICAP/eCAP)"
    license = "BSD-2-Clause"
    homepage = "https://www.e-cap.org/"
    url = "https://www.e-cap.org/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies: pure C++ library, only the C++ stdlib.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # config.guess predates HarmonyOS; passing --build/--host as an
        # equal native pair lets an old configure skip both guesses
        # (dime 0.20111205 pattern; --host alone as an ohos triplet would
        # hit the stale config.sub, --build alone leaves host guessing).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Old autoconf rejects -fuse-ld as a configure argument
        # ("unrecognized option"), so route the OHOS linker choice via
        # CFLAGS/CXXFLAGS/LDFLAGS where AC_TRY_LINK probes still see it.
        lld = _find_lld()
        if lld:
            fuse_ld = "-fuse-ld=%s" % lld
            tc.extra_cflags.append(fuse_ld)
            tc.extra_cxxflags.append(fuse_ld)
            tc.extra_ldflags.append(fuse_ld)
            self.output.info("hmbs_linker: using %s" % lld)
        else:
            self.output.warning("hmbs_linker: ld.lld not found; link probe may fail")
        # memory.h fallback uses C++11 <memory> when <tr1/memory> is gone
        # (harmonybrew clang libc++ has no TR1). Pin C++11 so std::shared_ptr
        # is available even if the profile requests an older cppstd.
        tc.extra_cxxflags.append("-std=c++11")
        tc.generate()
        # configure (autoconf 2.x) re-execs $SHELL/$CONFIG_SHELL for
        # cfgaux/config.sub. The cached SHELL may point at the dead
        # /data/service/hnp/bin/bash on this host; pin both to the
        # HMBS-provided /bin/sh so config.sub can run.
        # Also propagate the HMBS-provided writable TMPDIR (/tmp is
        # read-only on the host) so configure/config.status temp files
        # do not fall back to /tmp.
        shell = _effective_shell()
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        # Writable TMPDIR probe: never trust the injected TMPDIR blindly
        # (it may be missing/unwritable on some workers -> Error 77).
        # Only export a directory that passed a real write probe.
        try:
            _bf = getattr(self, "build_folder", None)
        except Exception:
            _bf = None
        tmpdir = _pick_writable_tmpdir(_bf)
        if tmpdir:
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
        # HMBS_CAP_CHMOD=0: neutralize mode/owner setting for the install
        # phase via upstream-supported overrides. cfgaux/install-sh honors
        # CHMODPROG/CHOWNPROG/CHGRPPROG/STRIPPROG env; `:` is an ash builtin
        # no-op, so no executable bit (unavailable under chmod:0) is needed.
        env.define("CHMODPROG", ":")
        env.define("CHOWNPROG", ":")
        env.define("CHGRPPROG", ":")
        env.define("STRIPPROG", ":")
        env.vars(self).save_script("hmbs_shell")

    def _fix_dead_shell_in_generated_scripts(self):
        # Also repair the dead profile compiler path. The ohos-aarch64
        # profile pins CC/CXX to /data/service/hnp/bin/clang{,++}, which
        # the 2026-09-18 preflight proved dead under /bin/sh
        # ("inaccessible or not found" on `clang --version`). The chosen
        # live compiler (see build()) is substituted into the generated
        # conan*.sh / toolchain scripts so configure AND make use it.
        dead = "/data/service/hnp/bin/bash"
        good = "/bin/sh"
        folders = set()
        for folder in (getattr(self, "generators_folder", None),
                       getattr(self, "build_folder", None)):
            if folder:
                folders.add(folder)
        for folder in folders:
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                if not (name.startswith("conan") and name.endswith(".sh")):
                    continue
                path = os.path.join(folder, name)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                except OSError:
                    continue
                if dead in content:
                    self.output.info(
                        "hmbs_shell: rewriting dead %s -> %s in %s" % (dead, good, name))
                    content = content.replace(dead, good)
                    try:
                        with open(path, "w", encoding="utf-8") as fh:
                            fh.write(content)
                    except OSError as exc:
                        self.output.warning(
                            "hmbs_shell: cannot rewrite %s: %s" % (name, exc))
        os.environ["SHELL"] = good
        os.environ["CONFIG_SHELL"] = good

    def _fix_dead_compiler_in_generated_scripts(self, live_cc=None, live_cxx=None):
        pairs = []
        if live_cc and live_cc != "/data/service/hnp/bin/clang":
            pairs.append(("/data/service/hnp/bin/clang", live_cc))
        if live_cxx and live_cxx != "/data/service/hnp/bin/clang++":
            pairs.append(("/data/service/hnp/bin/clang++", live_cxx))
        if not pairs:
            return
        folders = set()
        for folder in (getattr(self, "generators_folder", None),
                       getattr(self, "build_folder", None)):
            if folder:
                folders.add(folder)
        for folder in folders:
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                if not (name.startswith("conan") and name.endswith(".sh")):
                    continue
                path = os.path.join(folder, name)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                except OSError:
                    continue
                orig = content
                for dead, live in pairs:
                    if dead in content:
                        content = content.replace(dead, live)
                if content != orig:
                    self.output.info("hmbs_cc: rewriting compiler path in %s" % name)
                    try:
                        with open(path, "w", encoding="utf-8") as fh:
                            fh.write(content)
                    except OSError as exc:
                        self.output.warning("hmbs_cc: cannot rewrite %s: %s" % (name, exc))

    def _dump_config_log(self):
        # Surface the real linker error hidden behind configure's
        # "C compiler cannot create executables" summary line.
        search_roots = []
        for attr in ("build_folder", "source_folder"):
            try:
                folder = getattr(self, attr, None)
            except Exception:
                folder = None
            if folder:
                search_roots.append(folder)
        seen = set()
        for root in search_roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                if "config.log" not in filenames:
                    continue
                path = os.path.join(dirpath, "config.log")
                if path in seen:
                    continue
                seen.add(path)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                self.output.info("hmbs_config_log: %s (%d lines)" % (path, len(lines)))
                # Print the failing conftest section, not the whole file.
                start = 0
                for i, line in enumerate(lines):
                    if "cannot create executables" in line or "unable to make temporary file" in line:
                        start = max(0, i - 5)
                        break
                tail = lines[start:start + 120] if start else lines[-80:]
                for line in tail:
                    self.output.info("hmbs_config_log] %s" % line)
                return

    def _run_upstream_equivalent_smoke(self, live_cxx=None):
        # Upstream libecap 1.0.1 ships no formal suite (`make check` is an
        # Automake empty target: no TESTS/check_PROGRAMS in any Makefile.am,
        # no test/tests dirs). The HMBS evidence gate rejects no_tests/0 for
        # the `make check` command, so run a build-tree equivalent that
        # really links the just-built static archive and executes API
        # assertions. Counts below come from the binary's real stdout
        # (parsed PASS: lines, non-empty checked); a stub `exit 1` binary
        # fails here via non-zero returncode / missing PASS lines.
        import subprocess
        try:
            src = getattr(self, "source_folder", None)
            bld = getattr(self, "build_folder", None)
        except Exception:
            src, bld = None, None
        if not src or not bld:
            raise ConanException("hmbs_smoke: source/build folder missing")
        cands = [os.path.join(bld, "src", "libecap", ".libs", "libecap.a")]
        cands += glob.glob(os.path.join(bld, "**", "libecap.a"), recursive=True)
        lib = next((p for p in cands if os.path.isfile(p)), None)
        if not lib:
            raise ConanException("hmbs_smoke: built libecap.a not found")
        size = os.path.getsize(lib)
        self.output.info("hmbs_smoke: lib %s size=%d" % (lib, size))
        if size == 0:
            raise ConanException("hmbs_smoke: built libecap.a is empty")
        smoke_cpp = os.path.join(bld, "hmbs_upstream_smoke.cpp")
        smoke_bin = os.path.join(bld, "hmbs_upstream_smoke")
        smoke_src = (
            '#include <cstdio>\n'
            '#include <string>\n'
            '#include <libecap/common/registry.h>\n'
            '#include <libecap/common/version.h>\n'
            '#include <libecap/common/name.h>\n'
            '#include <libecap/common/area.h>\n'
            'int main() {\n'
            '    libecap::Version v(1, 0, 1);\n'
            '    if (!v.known() || !(v == libecap::Version(1, 0, 1))) return 1;\n'
            '    if (libecap::VersionString() == 0) return 1;\n'
            '    std::printf("PASS:version\\n");\n'
            '    libecap::Name m("GET");\n'
            '    if (!m.known() || !(m == "GET")) return 1;\n'
            '    std::printf("PASS:name\\n");\n'
            '    const std::string p("hello-ecap");\n'
            '    const libecap::Area a = libecap::Area::FromTempString(p);\n'
            '    if (!a || a.toString() != p) return 1;\n'
            '    std::printf("PASS:area\\n");\n'
            '    return 0;\n'
            '}\n'
        )
        with open(smoke_cpp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(smoke_src)
        cxx = live_cxx or os.environ.get("CXX") or "c++"
        src_inc = os.path.join(src, "src")
        bld_inc = os.path.join(bld, "src")
        fuse = ""
        try:
            _lld = _find_lld()
        except Exception:
            _lld = None
        if _lld:
            fuse = ' -fuse-ld="%s"' % _lld
        cmd = ('"%s" -std=c++11 -DHAVE_CONFIG_H -I"%s" -I"%s"'
               ' "%s" "%s" -o "%s"%s') % (
            cxx, src_inc, bld_inc, smoke_cpp, lib, smoke_bin, fuse)
        self.output.info("hmbs_smoke: compile %s" % cmd)
        self.run(cmd)
        if not os.path.isfile(smoke_bin) or os.path.getsize(smoke_bin) == 0:
            raise ConanException("hmbs_smoke: smoke binary missing or empty")
        self.output.info("hmbs_smoke: binary size=%d" % os.path.getsize(smoke_bin))
        proc = subprocess.run([smoke_bin], capture_output=True, text=True, cwd=bld)
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.splitlines():
            self.output.info("hmbs_smoke] %s" % line)
        if not out.strip():
            raise ConanException("hmbs_smoke: empty output (fixture not executed?)")
        passed = sum(1 for line in out.splitlines() if line.startswith("PASS:"))
        discovered = 3
        executed = 3
        failed = discovered - passed
        if proc.returncode != 0 or failed != 0:
            raise ConanException(
                "hmbs_smoke: smoke failed rc=%d passed=%d/%d out=%r" % (
                    proc.returncode, passed, discovered, out[:500]))
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"passed",'
            '"framework":"custom","command":"make check + build-tree smoke'
            ' (Version/Name/Area)","discovered":%d,"executed":%d,'
            '"passed":%d,"failed":0,"skipped":0,'
            '"reason":"upstream libecap 1.0.1 ships no formal suite; '
            'equivalent build-tree smoke links .libs/libecap.a and runs '
            'Version/Name/Area assertions"}' % (discovered, executed, passed))

    def build(self):
        apply_conandata_patches(self)
        self._fix_dead_shell_in_generated_scripts()
        # E011: neutralize `umask 077` in the autoconf `configure` before
        # running it (see _patch_configure_umask).
        try:
            _patch_configure_umask(getattr(self, "source_folder", None), self.output)
        except Exception as exc:
            self.output.warning("hmbs_umask: patch skipped: %s" % exc)
        # <tr1/memory> was removed from modern libc++; rewrite memory.h
        # in place (no .patch file -> no hunk-count parse risk).
        try:
            _patch_tr1_memory(getattr(self, "source_folder", None), self.output)
        except Exception as exc:
            self.output.warning("hmbs_tr1: patch skipped: %s" % exc)
        # Propagate a probed writable TMPDIR to configure/make/check
        # (/tmp is read-only on the host). _pick_writable_tmpdir() prefers
        # HMBS_TMPDIR / HMBS_PLATFORM_CAPABILITIES.tmpdir / TMPDIR and
        # falls back to a private dir under the build folder; it only
        # returns directories that passed a real file-write probe.
        tmpdir = _pick_writable_tmpdir(getattr(self, "build_folder", None))
        if tmpdir:
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
            self.output.info("hmbs_tmpdir: %s" % tmpdir)
        # HMBS_CAP_CHMOD=0 (+ readonly /tmp): neutralize mode/owner setting
        # for configure/make/install. cfgaux/install-sh honors these env
        # overrides; `:` is an ash builtin no-op needing no +x bit.
        for _k in ("CHMODPROG", "CHOWNPROG", "CHGRPPROG", "STRIPPROG"):
            os.environ[_k] = ":"
        # Route AC_PROG_INSTALL at configure time to upstream's own portable
        # cfgaux/install-sh (POSIX sh, honors the overrides above) instead
        # of the host `install` shim: the 2026-09-18 preflight proved the
        # shim exits 0 without creating DESTDIR/lib/libecap.a, after which
        # libtool's postinstall `chmod 644` dies with ENOENT. The `/bin/sh`
        # prefix avoids any +x requirement (unavailable under chmod:0);
        # old libtool explicitly accepts an sh-prefixed install program.
        try:
            _src = getattr(self, "source_folder", None)
            _sh = os.path.join(_src, "cfgaux", "install-sh") if _src else None
            if _sh and os.path.isfile(_sh):
                os.environ["INSTALL"] = "/bin/sh %s" % _sh
                self.output.info("hmbs_install: INSTALL=%s" % os.environ["INSTALL"])
            elif os.environ.get("HMBS_INSTALL"):
                os.environ["INSTALL"] = os.environ["HMBS_INSTALL"]
                self.output.info("hmbs_install: INSTALL=$HMBS_INSTALL")
        except Exception as exc:
            self.output.warning("hmbs_install: INSTALL override skipped: %s" % exc)
        # Pre-configure sanity: the profile compiler path is dead on this
        # host (`clang --version` -> Error 127). Probe live candidates by
        # real execution and use the first that responds; pass it
        # explicitly to configure so the toolchain script value is
        # overridden for the configure run, and patch the generated
        # scripts so make uses the same compiler.
        live_cc = None
        live_cxx = None
        for cand in _cc_candidates("cc"):
            try:
                self.run('"%s" --version' % cand)
                live_cc = cand
                self.output.info("hmbs_cc: live CC=%s" % cand)
                break
            except Exception:
                self.output.info("hmbs_cc: dead candidate CC=%s" % cand)
                continue
        for cand in _cc_candidates("cxx"):
            try:
                self.run('"%s" --version' % cand)
                live_cxx = cand
                self.output.info("hmbs_cc: live CXX=%s" % cand)
                break
            except Exception:
                self.output.info("hmbs_cc: dead candidate CXX=%s" % cand)
                continue
        if live_cc:
            os.environ["CC"] = live_cc
        if live_cxx:
            os.environ["CXX"] = live_cxx
        self.output.info("hmbs_cc: selected CC=%s CXX=%s TMPDIR=%s" % (
            os.environ.get("CC", "<unset>"),
            os.environ.get("CXX", "<unset>"),
            os.environ.get("TMPDIR", "<unset>")))
        if live_cc or live_cxx:
            self._fix_dead_compiler_in_generated_scripts(live_cc, live_cxx)
        else:
            self.output.warning("hmbs_cc: no live compiler found; keeping profile defaults")
        # Diagnose linker next to the live compiler for the next round.
        _bindir = os.path.dirname((live_cc or live_cxx or "").split()[0]) if (live_cc or live_cxx) else ""
        if _bindir:
            for _leaf in ("ld.lld", "ld"):
                _p = os.path.join(_bindir, _leaf)
                self.output.info("hmbs_linker: %s exists=%s" % (_p, os.path.isfile(_p)))
        autotools = Autotools(self)
        # Bake the working shell into the generated Makefiles as well, so
        # config.status/make do not re-introduce the dead hnp bash.
        # NOTE: Conan 2 Autotools.configure() takes `args`, not
        # `build_script_args` (the latter raises TypeError).
        configure_args = ["SHELL=/bin/sh", "CONFIG_SHELL=/bin/sh"]
        if live_cc:
            configure_args.append("CC=%s" % live_cc)
        if live_cxx:
            configure_args.append("CXX=%s" % live_cxx)
        try:
            autotools.configure(args=configure_args)
        except Exception:
            self._dump_config_log()
            raise
        # HMBS_CAP_CHMOD=0: neutralize libtool's postinstall `chmod 644`
        # (see _patch_libtool_chmod) right after configure generated it.
        try:
            _patch_libtool_chmod(getattr(self, "build_folder", None), self.output)
        except Exception as exc:
            self.output.warning("hmbs_chmod: libtool patch skipped: %s" % exc)
        autotools.make(args=["-j1"])
        # L1: run the upstream official test entry point first. Upstream
        # libecap 1.0.1 ships no formal suite (audited: no test/tests dirs,
        # no TESTS/check_PROGRAMS in any Makefile.am, see
        # test_package/MANIFEST.yml), so `make check` is an Automake empty
        # target. The HMBS evidence gate rejects no_tests/0 for the
        # `make check` command, so follow it with a build-tree equivalent
        # verification that really links and runs the just-built library.
        autotools.make(target="check")
        self._run_upstream_equivalent_smoke(live_cxx=live_cxx)

    def package(self):
        # Re-establish what build() set up: `make install` runs libtool +
        # install-sh again, so it needs the same writable TMPDIR (host /tmp
        # is read-only) and chmod-neutral overrides (HMBS_CAP_CHMOD=0).
        # Conan's env scripts (hmbs_shell) already carry these, this is
        # belt-and-suspenders for direct `make install` $(INSTALL) uses.
        tmpdir = _pick_writable_tmpdir(getattr(self, "build_folder", None))
        if tmpdir:
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
            self.output.info("hmbs_tmpdir(pkg): %s" % tmpdir)
        for _k in ("CHMODPROG", "CHOWNPROG", "CHGRPPROG", "STRIPPROG"):
            os.environ[_k] = ":"
        try:
            _src = getattr(self, "source_folder", None)
            _sh = os.path.join(_src, "cfgaux", "install-sh") if _src else None
            if _sh and os.path.isfile(_sh):
                os.environ["INSTALL"] = "/bin/sh %s" % _sh
        except Exception:
            pass
        try:
            _patch_libtool_chmod(getattr(self, "build_folder", None), self.output)
        except Exception as exc:
            self.output.warning("hmbs_chmod: libtool patch skipped: %s" % exc)
        # Pre-create dest dirs (mkdir -p equivalent, no chmod dependency)
        # so a shim mkdir failure cannot leave DESTDIR/lib missing.
        try:
            for _sub in ("lib", "include",
                         os.path.join("lib", "pkgconfig")):
                os.makedirs(os.path.join(self.package_folder, _sub),
                            exist_ok=True)
        except OSError:
            pass
        try:
            autotools = Autotools(self)
            autotools.install()
        except Exception as exc:
            self.output.warning(
                "hmbs_install: make install failed (%s), trying manual fallback copy" % exc)
            if _manual_install_fallback(self):
                return
            raise
        # `install -c` shim failure mode exits 0 without creating the file
        # (then libtool's chmod dies with ENOENT); top up anything missing.
        if not _package_artifacts_ok(self):
            self.output.warning(
                "hmbs_install: expected artifacts missing after make install,"
                " topping up via manual copy")
            if _manual_install_fallback(self):
                return
            raise ConanException(
                "hmbs_install: make install produced no usable artifacts and "
                "manual fallback could not complete (see hmbs_install logs)")

    def package_info(self):
        self.cpp_info.libs = ["ecap"]
        self.cpp_info.set_property("pkg_config_name", "libecap")
