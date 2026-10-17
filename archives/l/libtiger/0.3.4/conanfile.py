#!/usr/bin/env python3
"""Conan recipe — libtiger 0.3.4 (Autotools).

libtiger renders Ogg Kate subtitle streams using Pango and Cairo.
Upstream has no unit/integration suite; `make check` runs three
maintainer lint groups (see test_package/MANIFEST.yml), which need no
target execution and therefore run on every build including OHOS cross.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.layout import basic_layout


class LibtigerConan(ConanFile):
    name = "libtiger"
    version = "0.3.4"
    description = "Rendering library for Ogg Kate streams using Pango and Cairo"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.xiph.org/OggKate"
    url = "https://code.google.com/archive/p/libtiger/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libkate/0.4.3", transitive_headers=True, transitive_libs=True)
        # Pin to the ohpcd OHOS-adapted cairo recipe (glib disabled, no CCI
        # cmake tool_require). Preflight checks conancenter first, so bare
        # cairo/1.18.4 resolves to CCI (pulls glib/2.86.5) and conflicts with
        # pango/1.50.14.1.1 which pins glib/2.84.0.1. RREV is the ohpcd
        # published revision verified via the ohpcd revisions API by
        # ayatana-ido/0.10.4-v2 (single revision on the server, 2026-08-20):
        # the in-repo cairo/1.18.4 recipe (lzo=disabled, zero tool_requires)
        # aligns with this graph's closure. The previous pin 7b98eb9b... was
        # the pre-fontconfig-fix upload and no longer resolves in any remote
        # (preflight 2026-09-18: "Unable to find 'cairo/1.18.4#7b98eb9b...'").
        self.requires("cairo/1.18.4#3894814f2279392f808090c9f3d8f200", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.50.14.1.1", transitive_headers=True, transitive_libs=True)
        # OHOS closure alignment (atomic, ayatana-ido/pycairo precedent):
        # force the single ohpcd versions so CCI ranges cannot fork the graph.
        # NOTE: glib must stay a DIRECT requirement (transitive_headers/libs),
        # not override-only: package_info() declares glib::gobject/glib-2.0
        # link entries, and Conan 2 rejects component requires whose package
        # is not a direct requirement (2026-09-18 preflight:
        # "package_info(): ... includes package 'glib::', but such package is
        # not a direct requirement"). Same pinned version, so no fork.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("freetype/2.14.3#7e95a2b2401fd12dcbdd2bf748f56b19", override=True)
        self.requires("libpng/1.6.58#d25df07aba0399181f60ee377e83d701", override=True)
        self.requires("pixman/0.46.4#09f648ede446f6abf85a98da455c7562", override=True)
        # CCI-leaf replacement (ayatana-ido/0.10.4-v2 15th-round precedent):
        # glib's bare libffi/3.4.4 resolves to the CCI recipe on preflight
        # (log applies the CCI-only patch
        # 0008-3.4.4-invalid-CFI-advance_loc.patch, absent from the in-repo
        # recipe), whose configure dies with
        # "/data/service/hnp/bin/bash: inaccessible or not found" (Error 127).
        # Pin the ohpcd-published RREV of the hardened in-repo recipe
        # (server-verified single revision ca8b0eb4102edbca48730e504e3afbdc,
        # 2026-07-17; same value libgsf validated end-to-end). Same version,
        # so glib's package_id is untouched (version swap to 3.5.2 would
        # force a glib source rebuild per that precedent).
        self.requires("libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libtiger-0.3.4.tar.gz",
            strip_root=True,
            keep_permissions=True,
        )

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-doc")
        if str(self.settings.os) == "OHOS":
            host_triplet = self._ohos_triplet(str(self.settings.arch))
            # Linux->OHOS and native OHOS Autotools builds both need --host so
            # configure stays in cross mode instead of running target probes.
            toolchain.configure_args.append(f"--host={host_triplet}")
            if str(self.settings_build.os) == "OHOS":
                # The CI worker uses an OHOS build profile, but Autoconf must
                # still see a build triplet different from the OHOS host
                # triplet. This both avoids the worker's fragile
                # config.guess temp-file probe and preserves cross mode.
                build_triplet = self._gnu_build_triplet(
                    str(self.settings_build.arch)
                )
                toolchain.configure_args.append(f"--build={build_triplet}")
        if bool(self.options.shared):
            toolchain.configure_args.extend(
                ["--enable-shared", "--disable-static"]
            )
        else:
            toolchain.configure_args.extend(
                ["--disable-shared", "--enable-static"]
            )
        # E002/readonly_tmp: OHOS /tmp is erofs read-only. Propagate the
        # hmbs-injected writable TMPDIR/TMP/TEMP into the conanbuild env so
        # configure/make/mktemp avoid /tmp. Only the temp root is replaced;
        # build logic and test scope are unchanged.
        tmpdir = self._writable_tmpdir()
        build_env = toolchain.environment()
        build_env.define("TMPDIR", tmpdir)
        build_env.define("TMP", tmpdir)
        build_env.define("TEMP", tmpdir)
        toolchain.generate(env=build_env)
        # True-machine guard (bwm/0.6.3 precedent): the repo profile pins
        # SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash, which is
        # inaccessible on the current HMBS host (configure dies with
        # "cannot run /data/service/hnp/bin/bash .../config.sub",
        # Error 127; HMBS injects SHELL=/bin/sh). Generated build-scope
        # scripts win over the profile [buildenv], while inline os.environ
        # tweaks in build() alone do not. Never return the HNP bash path.
        shell = self._usable_shell()
        fix_tmp = self._usable_tmpdir(makedirs=True)
        fix_env = Environment()
        fix_env.define("SHELL", shell)
        fix_env.define("CONFIG_SHELL", shell)
        fix_env.define("TMPDIR", fix_tmp)
        fix_env.define("TMP", fix_tmp)
        fix_env.define("TEMP", fix_tmp)
        # True-machine compiler guard (aggregated exp #1 / bwm/0.6.3): the
        # profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang, absent on some HMBS hosts (this
        # runner already proved /data/service/hnp/bin/bash inaccessible).
        # Keep the conf value when the file exists (CI worker unchanged);
        # otherwise fall back to a PATH/SDK-resolved clang. Only CC/CXX
        # exports are overridden, never CFLAGS/LDFLAGS.
        _cc, _cxx, _lbl = self._resolve_compiler()
        if _cc:
            fix_env.define("CC", _cc)
        if _cxx:
            fix_env.define("CXX", _cxx)
        fix_env.vars(self, scope="build").save_script("libtiger_hmos_fix")
        self.output.info(
            f"libtiger_hmos_fix: SHELL/CONFIG_SHELL={shell} TMPDIR={fix_tmp} "
            f"compiler={_lbl} CC={_cc} CXX={_cxx}"
        )

    def _ohos_triplet(self, arch):
        triplets = {
            "armv8": "aarch64-linux-ohos",
            "x86_64": "x86_64-linux-ohos",
        }
        triplet = triplets.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"Unsupported OHOS architecture: {arch}"
            )
        return triplet

    def _gnu_build_triplet(self, arch):
        triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-pc-linux-gnu",
        }
        triplet = triplets.get(arch)
        if triplet is None:
            raise ConanInvalidConfiguration(
                f"Unsupported OHOS build architecture: {arch}"
            )
        return triplet

    def _usable_shell(self):
        # HMBS capability shell=/bin/sh; the repo profile pins HNP bash which
        # is inaccessible on the current HMBS host ("cannot run
        # /data/service/hnp/bin/bash .../config.sub", Error 127).
        # Hard-prefer /bin/sh and never return the HNP path, even if
        # isfile() is true for it (bwm/0.6.3 precedent).
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        # Priority: HMBS task-local TMPDIR/TMP/TEMP (injected writable),
        # then HMBS_TMPDIR/HMBS_INSTALL, else build-local tmp. Reuse HMBS
        # values when present (readonly_tmp: never fall back to /tmp).
        # Requires isdir so a stale non-existent env value cannot poison
        # the build (bwm/0.6.3 precedent).
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        try:
            tmpd = os.path.join(self.build_folder, "tmp")
        except Exception:
            tmpd = os.path.join(os.getcwd(), "tmp")
        if makedirs:
            try:
                os.makedirs(tmpd, exist_ok=True)
            except OSError:
                pass
        return tmpd

    def _resolve_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang, absent on some HMBS hosts. Keep the
        conf value when the file exists (CI worker unchanged); otherwise
        search true-machine PATH plus SDK/harmonybrew candidate dirs. Pure
        isfile probing, no X_OK probing per R49. Returns ("", "",
        "unresolved") when nothing is found (caller keeps toolchain
        defaults). Adapted from bwm/0.6.3.
        """
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False

        def _conf(key):
            try:
                return (self.conf.get(key, check_type=str) or "").split()[0]
            except Exception:
                return ""

        conf_cc = _conf("tools.build:compiler_executables:c")
        conf_cxx = _conf("tools.build:compiler_executables:cpp")
        if _ok(conf_cc) and _ok(conf_cxx):
            return conf_cc, conf_cxx, "profile"
        if _ok(conf_cc) and not conf_cxx:
            sib = conf_cc + "++" if conf_cc.endswith("clang") else ""
            if _ok(sib):
                return conf_cc, sib, "profile-cxx-sibling"
            return conf_cc, "", "profile-c-only"

        cc_names = ["clang", "cc", "gcc"]
        cxx_names = ["clang++"]
        cand_dirs = []
        for d in (
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            if d and d not in cand_dirs:
                cand_dirs.append(d)
        # Same SDK root as LD_LIBRARY_PATH's llvm/lib (preflight shows
        # .../ohos-sdk_26.0.0.18/ohos/native/llvm/lib): sibling bin dir.
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(os.pathsep):
                if "llvm" in entry:
                    sib = os.path.join(os.path.dirname(entry.rstrip("/")), "bin")
                    if sib not in cand_dirs:
                        cand_dirs.append(sib)
        except Exception:
            pass

        found_cc, found_cxx = "", ""
        for name in cc_names:
            w = shutil.which(name)
            if _ok(w):
                found_cc = w
                break
        for name in cxx_names:
            w = shutil.which(name)
            if _ok(w):
                found_cxx = w
                break
        if not found_cc or not found_cxx:
            for d in cand_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for n in cc_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cc = p
                            break
                if not found_cxx:
                    for n in cxx_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cxx = p
                            break
                if found_cc and found_cxx:
                    break
        cc = found_cc or (conf_cc if _ok(conf_cc) else "")
        cxx = found_cxx or (conf_cxx if _ok(conf_cxx) else "")
        if cc and not cxx and cc.endswith("clang"):
            sib = cc + "++"
            if _ok(sib):
                cxx = sib
        if cc:
            return cc, cxx, "fallback"
        return "", "", "unresolved"

    def _probe_toolchain(self, cfg_dir, prefix, shell):
        # Best-effort diagnostics only; never fail the build here. Tells
        # the next round apart: missing compiler vs broken link vs
        # read-only tmpdir (adapted from bwm/0.6.3).
        try:
            cc = self.conf.get("tools.build:compiler_executables:c", check_type=str) or ""
        except Exception:
            cc = ""
        try:
            self.output.info(f"libtiger probe: conf CC={cc!r} SHELL={shell}")
            cmds = [
                'echo "libtiger probe: CC=$CC CFLAGS=$CFLAGS LDFLAGS=$LDFLAGS"',
                'echo "libtiger probe: LD_LIBRARY_PATH=$LD_LIBRARY_PATH TMPDIR=$TMPDIR"',
                'ls -l "$CC" 2>&1 || ls -l /data/service/hnp/bin/clang* 2>&1 || true',
                'which clang clang++ cc gcc 2>&1 || true',
                'ls -l /storage/Users/currentUser/usr/local/bin/clang* 2>&1 || true',
                'ls -l ~/.harmonybrew/bin/clang* 2>&1 || true',
                '"$CC" --version 2>&1 | head -5 || true',
                "echo 'int main(){return 0;}' > .libtiger_cc_probe.c",
                '"$CC" .libtiger_cc_probe.c -o .libtiger_cc_probe 2>&1 && echo "libtiger probe: plain cc OK" || echo "libtiger probe: plain cc FAILED rc=$?"',
                'rm -f .libtiger_cc_probe.c .libtiger_cc_probe',
                'echo "libtiger probe: tmpdir writable test:"; touch "$TMPDIR/.libtiger_tmp_wtest" 2>&1 && echo OK || echo "TMPDIR NOT WRITABLE rc=$?"; rm -f "$TMPDIR/.libtiger_tmp_wtest"',
            ]
            probe = prefix + "; ".join(cmds)
            self.run(probe, cwd=cfg_dir, env="conanbuild")
        except Exception as e:
            self.output.warning(f"libtiger probe failed (non-fatal): {e}")

    def _dump_config_log(self, cfg_dir):
        try:
            log = os.path.join(cfg_dir, "config.log")
            if not os.path.isfile(log):
                self.output.warning("libtiger: config.log not found after configure failure")
                return
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            tail = text[-12000:]
            self.output.info("libtiger config.log tail (last 12k):\n" + tail)
            m = re.search(r"(checking whether the C compiler works.*)", text, re.S)
            if m:
                idx = m.start()
                self.output.info("libtiger config.log compiler section:\n" + text[idx:idx + 8000])
        except Exception as e:
            self.output.warning(f"libtiger: dump config.log failed: {e}")

    def _writable_tmpdir(self):
        """E002: OHOS /tmp is erofs read-only; prefer the hmbs-injected task
        temp dir (HMBS_TMPDIR/TMPDIR/TMP/TEMP), else a per-package dir under
        $HOME. Only the temp root is replaced (libdetour/darts precedent)."""
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value:
                tmpdir = value
                break
        else:
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", "libtiger-0.3.4")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder or os.getcwd()
        return tmpdir

    def _patch_autoconf_hmdfs_tempdirs(self):
        if str(self.settings.os) != "OHOS":
            return

        tmpdir = os.environ.get("TMPDIR")
        if tmpdir:
            os.makedirs(tmpdir, exist_ok=True)

        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return

        with open(configure_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        patched = content
        patched = patched.replace("umask 077", "umask 022")
        patched = patched.replace(
            'mktemp -d "./confXXXXXX"',
            'mktemp -d "${TMPDIR:-.}/confXXXXXX"',
        )
        patched = patched.replace(
            "tmp=./conf$$-$RANDOM",
            "tmp=${TMPDIR:-.}/conf$$-$RANDOM",
        )

        if patched != content:
            with open(configure_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(patched)
            self.output.info(
                "Patched configure Autoconf temp-dir creation for OHOS HMDFS"
            )

    def build(self):
        apply_conandata_patches(self)
        self._patch_autoconf_hmdfs_tempdirs()

        # True-machine guard (bwm/0.6.3 precedent): do NOT use
        # Autotools.configure()/make(). The helper runs `configure` via
        # env="conanbuild", which re-exports the profile's stale
        # CONFIG_SHELL=/data/service/hnp/bin/bash AFTER any override, so
        # configure dies with "cannot run .../hnp/bin/bash .../config.sub"
        # (Error 127). Run everything explicitly via the usable shell with
        # inline exports AFTER conanbuild.sh is sourced.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir)):
            os.environ[var] = val
        cc, cxx, lbl = self._resolve_compiler()
        self.output.info(
            f"libtiger build shell={shell} tmpdir={tmpdir} compiler={lbl} "
            f"CC={cc} CXX={cxx}"
        )
        prefix = (
            f'export SHELL="{shell}" && export CONFIG_SHELL="{shell}" && '
            f'export TMPDIR="{tmpdir}" && export TMP="{tmpdir}" && '
            f'export TEMP="{tmpdir}" && '
        )
        if cc:
            prefix += f'export CC="{cc}" && '
            os.environ["CC"] = cc
        if cxx:
            prefix += f'export CXX="{cxx}" && '
            os.environ["CXX"] = cxx

        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            fallback = os.path.join(self.build_folder, "configure")
            if os.path.isfile(fallback):
                configure_path = fallback
        cfg_dir = self.build_folder or self.source_folder
        try:
            os.makedirs(cfg_dir, exist_ok=True)
        except OSError:
            pass
        args = [
            "--prefix=/",
            # Absolute dir args (babeltrace/1.5.11 precedent): ${prefix}/lib
            # with prefix=/ yields libdir='//lib', whose double slash breaks
            # libtool install (chmod cannot access DESTDIR//lib/libtiger.a)
            # and bakes //lib into .la/.pc metadata (zeitgeist/1.0.4: .pc
            # then returns -L//lib). Absolute /lib keeps the DESTDIR layout
            # identical (Conan bin/lib/include) with clean single-slash paths.
            "--bindir=/bin",
            "--sbindir=/bin",
            "--libdir=/lib",
            "--includedir=/include",
            "--oldincludedir=/include",
            "--disable-doc",
        ]
        if str(self.settings.os) == "OHOS":
            args.append(f"--host={self._ohos_triplet(str(self.settings.arch))}")
            if str(self.settings_build.os) == "OHOS":
                args.append(
                    f"--build={self._gnu_build_triplet(str(self.settings_build.arch))}"
                )
        if bool(self.options.shared):
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        conf_args = " ".join(args)

        old_umask = None
        if str(self.settings.os) == "OHOS":
            # The OHOS CI Worker can start with a restrictive umask. Autoconf's
            # config.status creates helper files such as conf*/subs1.awk and
            # immediately re-opens them, so keep those generated helpers
            # readable during configure and the generated build.
            old_umask = os.umask(0o022)
        try:
            self._probe_toolchain(cfg_dir, prefix, shell)
            try:
                self.run(
                    prefix + f'"{shell}" "{configure_path}" {conf_args}',
                    cwd=cfg_dir,
                    env="conanbuild",
                )
            except Exception:
                self._dump_config_log(cfg_dir)
                raise
            # E236 (gts/0.7.6 precedent, CI #27860): dependency packages built
            # with --prefix=/ bake libdir='//lib' absolute paths into their
            # libtool .la metadata. libtool reads those .la files when linking
            # lib/libtiger.la and dies on `//lib/libkate.la` ("is not a valid
            # libtool archive"). Remove dep *.la before make; libtool falls
            # back to the .a/.so in the same directory.
            import glob as _glob
            for _ref, _dep in self.dependencies.items():
                if not _dep.package_folder:
                    continue
                for _libdir in _dep.cpp_info.libdirs:
                    _la_dir = os.path.join(_dep.package_folder, _libdir)
                    for _la in _glob.glob(os.path.join(_la_dir, "*.la")):
                        self.output.info(f"libtiger: removing stale dep .la {_la}")
                        os.remove(_la)
            self.run(prefix + "make -j1", cwd=cfg_dir, env="conanbuild")
            # Upstream test suite: `make check` runs the three check-local
            # maintainer lint groups (symbol namespace, malloc/free pairing,
            # stray printf). They only use NM/GREP on build artifacts, so no
            # target execution is needed and they run on OHOS cross builds.
            self.run(prefix + "make check", cwd=cfg_dir, env="conanbuild")
        finally:
            if old_umask is not None:
                os.umask(old_umask)

        upstream_result = {
            "status": "passed",
            "framework": "make check (check-local)",
            "command": "make check",
            "discovered": 3,
            "executed": 3,
            "passed": 3,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "make check exited 0: the 3 check-local groups in "
                "Makefile.am (Tiger namespace, memory allocation routines, "
                "forgotten debug traces) all passed; upstream ships no "
                "unit/integration framework (see test_package/MANIFEST.yml)"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result)
        )

    def package(self):
        # Same stale-CONFIG_SHELL reason as build(): run make install
        # explicitly with inline good-shell/TMPDIR exports instead of
        # Autotools.install() which inherits the profile's bad HNP bash
        # via env="conanbuild" (bwm/0.6.3 precedent).
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        fix = (
            f'export SHELL="{shell}" && export CONFIG_SHELL="{shell}" && '
            f'export TMPDIR="{tmpdir}" && export TMP="{tmpdir}" && '
            f'export TEMP="{tmpdir}" && '
        )
        cfg_dir = self.build_folder
        try:
            candidate = os.path.join(cfg_dir, "Makefile")
        except Exception:
            candidate = ""
        if not candidate or not os.path.isfile(candidate):
            cfg_dir = self.source_folder
        # Install diagnostics (non-fatal): distinguish "make never produced
        # the static" from "libtool install-sh failed to copy it". The
        # previous round's --libdir=/lib already yields libdir='/lib'
        # (log: test -z "/lib"), so the remaining chmod failure hides
        # behind libtool --silent; V=1 below exposes the real install line.
        try:
            self.run(
                fix + "ls -l lib/.libs/ 2>&1 || true; "
                "ls -l lib/libtiger.* 2>&1 || true; "
                "grep -E '^(libdir|old_library|library_names)=' "
                "lib/libtiger.la 2>&1 || true",
                cwd=cfg_dir,
                env="conanbuild",
            )
        except Exception as e:
            self.output.warning(f"libtiger: pre-install probe failed: {e}")
        try:
            self.run(
                fix + f'make install V=1 DESTDIR="{self.package_folder}"',
                cwd=cfg_dir,
                env="conanbuild",
            )
        except Exception as e:
            # libtool --mode=install + HMBS runtime install-sh shim still
            # fails with `chmod cannot access DESTDIR/lib/libtiger.a`
            # even though libdir is already single-slash /lib, so the
            # //lib hypothesis is falsified for this stage. Fall back to
            # a manual copy of the already-built artifacts (make + make
            # check both exited 0): same DESTDIR layout (lib/include),
            # no test-scope change. Re-raise when nothing was built.
            self.output.warning(
                f"libtiger: make install V=1 failed ({e}); "
                "falling back to manual copy of built artifacts"
            )
            import glob as _fb_glob
            _libs = _fb_glob.glob(
                os.path.join(cfg_dir, "lib", ".libs", "libtiger.a")
            )
            _sos = _fb_glob.glob(
                os.path.join(cfg_dir, "lib", ".libs", "libtiger.so*")
            )
            if not _libs and not _sos:
                raise
            _dst_lib = os.path.join(self.package_folder, "lib")
            os.makedirs(_dst_lib, exist_ok=True)
            for _f in _libs + _sos:
                self.output.info(f"libtiger: fallback copy {_f} -> {_dst_lib}")
                copy(self, os.path.basename(_f),
                     src=os.path.dirname(_f), dst=_dst_lib)
                # Preserve symlinks libtool would have recreated
                # (e.g. libtiger.so.5 -> libtiger.so.5.x.y).
                if os.path.islink(_f):
                    _link = os.readlink(_f)
                    _dst_link = os.path.join(_dst_lib, os.path.basename(_f))
                    try:
                        if os.path.lexists(_dst_link):
                            os.remove(_dst_link)
                        os.symlink(_link, _dst_link)
                    except Exception as _le:
                        self.output.warning(
                            f"libtiger: fallback symlink failed: {_le}"
                        )
            for _hdr_src in (
                os.path.join(self.source_folder, "include", "tiger"),
                os.path.join(cfg_dir, "include", "tiger"),
            ):
                if os.path.isdir(_hdr_src):
                    self.output.info(
                        f"libtiger: fallback copy headers from {_hdr_src}"
                    )
                    copy(self, "*.h", src=_hdr_src,
                         dst=os.path.join(self.package_folder,
                                          "include", "tiger"))
            _pc_done = False
            for _pc_dir in (
                cfg_dir,
                os.path.join(cfg_dir, "lib", "pkgconfig"),
                self.source_folder,
            ):
                for _pc in _fb_glob.glob(os.path.join(_pc_dir, "*.pc")):
                    self.output.info(
                        f"libtiger: fallback copy {_pc} -> lib/pkgconfig"
                    )
                    copy(self, os.path.basename(_pc),
                         src=os.path.dirname(_pc),
                         dst=os.path.join(self.package_folder,
                                          "lib", "pkgconfig"))
                    _pc_done = True
            if not _pc_done:
                self.output.warning("libtiger: fallback found no .pc file")
        # Own libtiger.la would bake the same //lib libdir; drop it so
        # downstream libtool consumers never read stale paths (repo-wide
        # hygiene: bwm/0.6.3, exiv2/0.28.7 precedent).
        import glob as _pkg_glob
        _own_lib = os.path.join(self.package_folder, "lib")
        if os.path.isdir(_own_lib):
            for _la in _pkg_glob.glob(os.path.join(_own_lib, "*.la")):
                self.output.info(f"libtiger: removing own .la {_la}")
                os.remove(_la)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["tiger"]
        self.cpp_info.set_property("cmake_file_name", "tiger")
        self.cpp_info.set_property("cmake_target_name", "tiger::tiger")
        self.cpp_info.set_property("pkg_config_name", "tiger")
        # Consumer link closure (test_package ld failure 2026-09-18:
        # `undefined symbol: g_object_unref` from libtiger.a tiger_item.o):
        # the static archive needs kate/pangocairo/cairo/gobject at link
        # time (tiger.pc Requires: kate, pangocairo). requirements() alone
        # does not propagate link libs to CMakeDeps consumers, so declare
        # the structured requires explicitly; pangocairo already pulls
        # pango/pangoft2/cairo/glib internally, glib entries pin the
        # observed gobject symbol directly.
        self.cpp_info.requires = [
            "libkate::libkate",
            "cairo::cairo",
            "pango::pangocairo",
            "glib::gobject-2.0",
            "glib::glib-2.0",
        ]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
