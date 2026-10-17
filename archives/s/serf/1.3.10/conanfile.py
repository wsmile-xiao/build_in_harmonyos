#!/usr/bin/env python3
"""Conan recipe — serf 1.3.10 (SCons).

Serf is a high-performance C-based HTTP client library built upon the
Apache Portable Runtime (APR). Upstream builds with SCons: `scons` builds
libserf-1 (static + shared) and `scons check` runs the upstream suite —
5 serf_response fixture cases plus the CuTest suites (context, buckets,
ssl, auth) in test_all.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class SerfConan(ConanFile):
    name = "serf"
    version = "1.3.10"
    description = ("High-performance C-based HTTP client library "
                   "built upon the Apache Portable Runtime (APR).")
    license = "Apache-2.0"
    homepage = "https://serf.apache.org/"
    url = "https://github.com/apache/serf"
    topics = ("apache", "http", "client", "apr")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # SCons 4.10.1 as an isolated pip install (gpsd/3.26 precedent).
    # Not a tool_requires: no scons recipe is published in ohpcd.
    _SCONS_VERSION = "4.10.1"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "serf recipe is validated for Linux/OHOS, not %s" % self.settings.os)

    def requirements(self):
        # apr-util/1.6.3 has no conan recipe in ohpcd
        # (archives/a/apr-util/1.6.3 ships only manifest/notes/patches, and no
        # merged recipe in the repo requires any apr-util), so it cannot be
        # resolved from the remote. It is built privately from official
        # sources (see _build_apr_util()) instead of being required here.
        # SCons mandates APU when the APR major version is < 2 (apr 1.7.6),
        # so the private sub-build is mandatory, not optional.
        self.requires("apr/1.7.6", transitive_headers=True, transitive_libs=True)
        # expat/2.8.2 is required by many merged recipes (wayland, pulseaudio,
        # polkit, exempi, ...) so it is published; the private apr-util build
        # consumes it via --with-expat (apr-util 1.6.x ships no bundled expat).
        self.requires("expat/2.8.2")
        self.requires("zlib/1.3.1")
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"]["serf"], strip_root=True)
        apu = self.conan_data["sources"]["apr-util"]
        get(self, apu["url"], sha256=apu.get("sha256"),
            destination=os.path.join(self.source_folder, "apr-util"),
            strip_root=True)

    def _hmbs_tmpdir(self):
        # HMBS injects a writable TMPDIR (HarmonyOS PC has read-only /tmp).
        # Prefer it; fall back to a build-folder dir that is always writable.
        # Previous preflight flagged [readonly_tmp]; pip/SCons must never
        # assume /tmp is writable.
        # Write-probe every candidate (coinor-vol/1.5.4 lesson): makedirs or
        # isdir alone is not proof on HMDFS/CI workers (E046: chmod/X_OK
        # ignored); only makedirs + open(w) + unlink proves writability.
        # Candidates: HMBS task-private dirs first, then build folder.
        # NOTE: HMBS_AUTOCONF_MKTEMP_FALLBACK is a "1" flag, never a path
        # (cxxtools/3.0.0 lesson) — do not treat it as a directory.
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            val = (os.environ.get(key, "") or "").strip()
            if not val:
                continue
            try:
                os.makedirs(val, exist_ok=True)
                probe = os.path.join(val, ".hmbs-write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                try:
                    tempfile.tempdir = None
                except Exception:
                    pass
                return val
            except OSError:
                continue
        fallback = os.path.join(self.build_folder, "_tmp")
        os.makedirs(fallback, exist_ok=True)
        try:
            probe = os.path.join(fallback, ".hmbs-write-probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.unlink(probe)
        except OSError as exc:
            raise ConanException(
                "no writable tmpdir (build fallback %s unusable: %r)" % (fallback, exc))
        try:
            tempfile.tempdir = None
        except Exception:
            pass
        return fallback

    def _apu_prefix(self):
        # Private install prefix for the vendored apr-util sub-build.
        # build_folder is always writable (see _hmbs_tmpdir).
        return os.path.join(self.build_folder, "apu")

    def _patch_apr_util(self, src):
        # Python port of archives/a/apr-util/1.6.3/patches/* for the private
        # sub-build (same upstream version 1.6.3): E007 __OHOS__ LIBC
        # detection, E072 ohos-linux triplet, E011 umask 022 for HMDFS.
        # Pure-Python string edits so no external `patch` binary is needed
        # (and HMDFS ignores chmod, so invoking scripts via `sh` matters more
        # than exec bits). Absent patterns are warnings, never fatal.
        def _edit(path, old, new, count=1):
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                data = handle.read()
            if old not in data:
                self.output.warning("apr-util patch pattern absent in %s; skipping" % path)
                return
            data = data.replace(old, new, count)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(data)
            self.output.info("patched %s" % path)

        _edit(os.path.join(src, "build", "config.guess"),
              "#if defined(__ANDROID__)\n\tLIBC=android\n",
              "#if defined(__ANDROID__)\n\tLIBC=android\n#elif defined(__OHOS__)\n\tLIBC=ohos\n")
        sub_path = os.path.join(src, "build", "config.sub")
        with open(sub_path, "r", encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
        inserted = False
        for idx, line in enumerate(lines):
            if "basic_os=linux-android" in line:
                end = idx
                while end < len(lines) and lines[end].strip() != ";;":
                    end += 1
                if end < len(lines):
                    block = lines[idx:end + 1]
                    indent = block[0][:len(block[0]) - len(block[0].lstrip())]
                    lines[end + 1:end + 1] = [
                        "\n",
                        "%sohos-linux)\n" % indent,
                        "%sbasic_machine=$field1-unknown\n" % indent,
                        "%sbasic_os=linux-ohos\n" % indent,
                        "%s;;\n" % indent,
                    ]
                    inserted = True
                break
        if not inserted:
            self.output.warning("apr-util config.sub ohos-linux pattern absent; skipping")
        else:
            with open(sub_path, "w", encoding="utf-8", newline="") as handle:
                handle.writelines(lines)
            self.output.info("patched %s" % sub_path)
        cfg_path = os.path.join(src, "configure")
        with open(cfg_path, "r", encoding="utf-8", errors="replace") as handle:
            cfg = handle.read()
        if "umask 077" not in cfg:
            self.output.warning("apr-util configure umask pattern absent; skipping")
        else:
            cfg = cfg.replace("umask 077", "umask 022")
            with open(cfg_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(cfg)
            self.output.info("patched %s (umask)" % cfg_path)

    @staticmethod
    def _autotools_arch(arch):
        return {"armv8": "aarch64"}.get(str(arch), str(arch))

    def _apu_triplets(self):
        # Old (2021) config.guess cannot recognize the HongMeng kernel, so
        # configure dies with "cannot guess build type". Pass explicit
        # --build/--host to bypass config.guess entirely (zzuf/owfs/bacula
        # precedent in this repo). The preflight builds natively on the
        # device, so build == host. The linux-gnu vendor string is accepted
        # by stock config.sub without extra patching.
        host_arch = self._autotools_arch(self.settings.arch)
        if str(self.settings.os) == "OHOS":
            host = "%s-unknown-linux-gnu" % host_arch
        else:
            host = "%s-pc-linux-gnu" % host_arch
        try:
            build_arch = self._autotools_arch(self.settings_build.arch)
        except Exception:
            build_arch = host_arch
        try:
            build_os = str(self.settings_build.os)
        except Exception:
            build_os = str(self.settings.os)
        if build_os == "OHOS":
            build = "%s-unknown-linux-gnu" % build_arch
        elif build_os == "Linux":
            build = "%s-pc-linux-gnu" % build_arch
        else:
            build = host
        return build, host

    def _resolve_apr_build_dir(self, apr_pkg, sh, env):
        # Preflight 2026-09-20: apr-util configure died with
        #   configure[4671]: cd: //build-1: No such file or directory
        #   cp: cannot stat '/apr_rules.mk'
        # i.e. `apr-1-config --installbuilddir` returned a directory that
        # does not exist on this worker (conan cache relocation: the APR
        # binary came from the remote with build-time absolute paths), so
        # `cp $APR_BUILD_DIR/apr_rules.mk build/rules.mk` silently produced
        # nothing and `make` then failed on the missing rules.mk.
        # Resolve the true apr_rules.mk location up front; configure's only
        # use of APR_BUILD_DIR is that single cp (not AC_SUBST'd), so a
        # post-configure copy from the validated location fully replicates
        # healthy behaviour without wrapper scripts (no exec-bit/HMDFS risk).
        candidates = [os.path.join(apr_pkg, "bin", "apr-1-config"),
                      os.path.join(apr_pkg, "apr-1-config")]
        apr_config = next((c for c in candidates if os.path.isfile(c)), None)
        if apr_config is None:
            listing = []
            try:
                listing = sorted(os.listdir(apr_pkg))[:20]
            except OSError:
                pass
            raise ConanException(
                "apr-1-config not found under %s (top: %s)" % (apr_pkg, listing))
        reported = ""
        try:
            proc = subprocess.run(
                [sh, apr_config, "--installbuilddir"],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120)
            reported = (proc.stdout or "").strip().splitlines()[-1].strip() \
                if (proc.stdout or "").strip() else ""
            self.output.info("apr-1-config --installbuilddir -> %r (exit %d)"
                             % (reported, proc.returncode))
        except Exception as exc:
            self.output.warning("apr-1-config --installbuilddir failed: %r" % exc)
        if reported:
            rules = os.path.join(reported, "apr_rules.mk")
            if os.path.isfile(rules) and os.path.getsize(rules) > 0:
                self.output.info("APR build dir validated: %s" % reported)
                return apr_config, reported, reported
            self.output.warning(
                "apr-1-config reported %r but apr_rules.mk missing there; "
                "searching %s" % (reported, apr_pkg))
        found = ""
        try:
            hits = []
            for root, _dirs, files in os.walk(apr_pkg):
                if "apr_rules.mk" in files:
                    hits.append(root)
                    if len(hits) >= 10:
                        break
            self.output.info("apr_rules.mk search hits: %s" % hits)
            # Prefer the default `apr` layout location (<prefix>/build-1).
            for hit in hits:
                if os.path.basename(hit) == "build-1":
                    found = hit
                    break
            found = found or (hits[0] if hits else "")
        except Exception as exc:
            self.output.warning("apr_rules.mk search failed: %r" % exc)
        if not found:
            raise ConanException(
                "APR build dir unusable (reported %r) and no apr_rules.mk "
                "found under %s" % (reported, apr_pkg))
        self.output.info("APR build dir fallback: %s (reported was %r)"
                         % (found, reported))
        return apr_config, found, reported

    def _find_apr_libtool(self, apr_pkg, apr_build_dir):
        # The relocated apr-1-config reports '//build-1', so apr-util
        # Makefiles end up invoking '//build-1/libtool' (preflight
        # 2026-09-20: '/data/service/hnp/bin/bash: //build-1/libtool:
        # No such file or directory'). The real libtool ships alongside
        # apr_rules.mk inside the apr package; locate it explicitly.
        candidates = []
        if apr_build_dir:
            candidates.append(os.path.join(apr_build_dir, "libtool"))
        try:
            for root, _dirs, files in os.walk(apr_pkg):
                if "libtool" in files:
                    p = os.path.join(root, "libtool")
                    if p not in candidates:
                        candidates.append(p)
                    if len(candidates) >= 10:
                        break
        except OSError:
            pass
        for cand in candidates:
            try:
                if os.path.isfile(cand) and os.path.getsize(cand) > 0:
                    self.output.info("APR libtool candidate: %s" % cand)
                    return cand
            except OSError:
                continue
        self.output.warning("APR libtool not found under %s (tried %s)"
                            % (apr_pkg, candidates))
        return ""

    def _repair_apr_relocation(self, src, apr_pkg, apr_build_dir,
                               bogus_build_dir):
        # Full relocation repair (superset of the previous round's
        # rules.mk-only copy): apr-1-config from the remote cache reports
        # build-time absolute paths ('//build-1', '-I//include') that do
        # not exist on this worker. configure bakes them into every
        # generated Makefile (LIBTOOL via APR_BUILD_DIR, CFLAGS via
        # apr_includedir), so fixing only build/rules.mk still leaves
        # `bash //build-1/libtool` failing. Rewrite every generated file.
        real_include = os.path.join(apr_pkg, "include")
        real_lib = os.path.join(apr_pkg, "lib")
        subs = []
        if bogus_build_dir and bogus_build_dir != apr_build_dir:
            subs.append((bogus_build_dir, apr_build_dir))
        # The '-I//include' token in the preflight compile line shows the
        # same relocation affects includedir/libdir (bogus prefix '//').
        for bogus, real in (("//include", real_include),
                            ("//lib", real_lib)):
            if bogus not in [s for s, _ in subs]:
                subs.append((bogus, real))
        total_files = 0
        total_repl = 0
        for root, _dirs, files in os.walk(src):
            for fn in files:
                if fn in (".git",):
                    continue
                path = os.path.join(root, fn)
                # Only generated build files can contain the baked paths;
                # skip large binaries and sources to keep the pass cheap.
                try:
                    if os.path.getsize(path) > 1024 * 1024:
                        continue
                except OSError:
                    continue
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="strict") as handle:
                        data = handle.read()
                except (OSError, UnicodeDecodeError, ValueError):
                    continue
                orig = data
                for old, new in subs:
                    if old and old in data:
                        data = data.replace(old, new)
                if data != orig:
                    try:
                        with open(path, "w", encoding="utf-8",
                                  newline="") as handle:
                            handle.write(data)
                        total_files += 1
                        total_repl += 1
                    except OSError as exc:
                        self.output.warning("relocation repair write failed %s: %r"
                                            % (path, exc))
        self.output.info("APR relocation repair: %d files rewritten (subs=%s)"
                         % (total_files, subs))
        # Verify the libtool path the build will actually exec.
        libtool = os.path.join(apr_build_dir, "libtool")
        try:
            ok = os.path.isfile(libtool) and os.path.getsize(libtool) > 0
        except OSError:
            ok = False
        if not ok:
            found = self._find_apr_libtool(apr_pkg, apr_build_dir)
            if found and os.path.dirname(found) != apr_build_dir:
                self.output.warning(
                    "real libtool is %s, not %s; build files now point at %s"
                    % (found, libtool, apr_build_dir))

    def _probe_usable_install(self, sh, tmpdir, env):
        # Preflight 2026-09-21: apr-util `make install` died with
        #   libtool: install: <runtime>/bin/install -c -m 755
        #     .libs/libaprutil-1.a <prefix>/lib/libaprutil-1.a
        #   chmod: cannot access '<prefix>/lib/libaprutil-1.a':
        #     No such file or directory
        # i.e. the configure-time INSTALL program (HMBS runtime shim on
        # PATH) ran without error but produced no destination file, so
        # libtool's follow-up chmod failed. Probe candidates up front by
        # really copying a file with `-c -m 755` and verifying the
        # destination exists and is non-empty; return the first that works.
        # Candidates: HMBS_INSTALL shim (if a file), system install
        # binaries, then PATH lookup. Empty string means no candidate
        # passed (caller falls back to manual Python copy).
        import tempfile as _tf
        probe_src = None
        try:
            fd, probe_src = _tf.mkstemp(dir=tmpdir, prefix="hmbs-install-probe-")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("hmbs-install-probe")
        except OSError as exc:
            self.output.warning("install probe source creation failed: %r" % exc)
            return ""
        ordered = []
        for key in ("HMBS_INSTALL",):
            cand = (os.environ.get(key, "") or env.get(key, "") or "").strip()
            if cand and cand not in ordered:
                ordered.append(cand)
        for cand in ("/system/bin/install", "/bin/install", "/usr/bin/install"):
            if cand not in ordered:
                ordered.append(cand)
        try:
            which_install = shutil.which("install")
        except Exception:
            which_install = None
        if which_install and which_install not in ordered:
            ordered.append(which_install)
        # The runtime shim that just failed goes last (still usable for
        # `install -d` in some workers, but never preferred for files).
        try:
            path_install = shutil.which("install")
            if path_install and path_install not in ordered:
                ordered.append(path_install)
        except Exception:
            pass
        for cand in ordered:
            try:
                if not cand or not os.path.isfile(cand):
                    continue
            except Exception:
                continue
            dest = probe_src + ".dest-%s" % os.path.basename(cand or "install")
            try:
                if os.path.isfile(dest):
                    os.unlink(dest)
            except OSError:
                pass
            try:
                proc = subprocess.run(
                    [cand, "-c", "-m", "755", probe_src, dest],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60)
                ok = (proc.returncode == 0 and os.path.isfile(dest)
                      and os.path.getsize(dest) > 0)
                self.output.info("install probe %r -> exit %d exists=%s" % (
                    cand, proc.returncode, os.path.isfile(dest)))
                try:
                    if os.path.isfile(dest):
                        os.unlink(dest)
                except OSError:
                    pass
                if ok:
                    try:
                        os.unlink(probe_src)
                    except OSError:
                        pass
                    self.output.info("usable INSTALL: %s" % cand)
                    return cand
            except Exception as exc:
                self.output.warning("install probe %r failed: %r" % (cand, exc))
                continue
        try:
            os.unlink(probe_src)
        except OSError:
            pass
        self.output.warning("no usable install program found (tried %s)" % ordered)
        return ""

    def _device_shell(self):
        # configure/config.status must run under a device shell. Prefer the
        # HMBS-injected SHELL/CONFIG_SHELL when present on disk
        # (cyrus-sasl-gs2/2.1.28 + kyoto-tycoon/0.9.56 precedent).
        for cand in (os.environ.get("CONFIG_SHELL"),
                     os.environ.get("SHELL"),
                     "/bin/sh", "/system/bin/sh"):
            if cand and os.path.isfile(cand):
                return cand
        return "/bin/sh"

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory created
        # by mktemp on the current device filesystem cannot be written by
        # autoconf afterwards. When HMBS injects
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during the configure
        # step only so calls for "./conf*" fail and autoconf falls back to
        # its `mkdir` path. All other mktemp calls delegate to the real
        # binary; TMPDIR itself stays writable.
        # (cyrus-sasl-login/2.1.28 + kyoto-tycoon/0.9.56 precedent.)
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!{sh}\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /system/bin/mktemp /bin/mktemp "
            "/usr/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        ).format(sh=self._device_shell())
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def _dump_config_log(self, src):
        # Evidence for the next round: the preflight summary truncates
        # aggressively, so emit the decisive config.log section as WARN
        # lines (myman/4.0.116 + kyoto-tycoon/0.9.56 precedent).
        log = os.path.join(src, "config.log")
        try:
            with open(log, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.read().splitlines()
        except OSError as exc:
            self.output.warning("configure failed and config.log unreadable: %r" % exc)
            return
        self.output.warning("configure failed; config.log (%d lines total)" % len(lines))
        key = None
        for i, line in enumerate(lines):
            if "cannot create executables" in line or "failed program was" in line:
                key = i
        if key is not None:
            lo = max(0, key - 40)
            hi = min(len(lines), key + 10)
            self.output.warning("config.log error section [%d:%d]:" % (lo, hi))
            for line in lines[lo:hi]:
                self.output.warning("config.log| %s" % line)
        hits = [l for l in lines
                if ("unable to make temporary file" in l or "Read-only file system" in l
                    or "can't fork" in l or "temporary file" in l
                    or "error:" in l or "cannot find" in l)]
        for line in hits[:30]:
            self.output.warning("config.log| %s" % line)
        for line in lines[-30:]:
            self.output.warning("config.log| %s" % line)

    def _build_apr_util(self):
        # apr-util has no conan recipe in ohpcd, but serf's SCons build
        # mandates APU when the APR major version is < 2. Build it privately
        # as a static library from official sources into _apu_prefix().
        # Only libaprutil-1.a is merged into the serf package (headers stay
        # private: serf.h exposes no apr-util headers). expat comes from the
        # direct expat/2.8.2 requirement (apr-util 1.6.x ships no bundled
        # expat, verified against the upstream tarball).
        src = os.path.join(self.source_folder, "apr-util")
        prefix = self._apu_prefix()
        if not os.path.isfile(os.path.join(src, "configure")):
            raise ConanException("vendored apr-util sources missing in %s" % src)
        self._patch_apr_util(src)
        tmpdir = self._hmbs_tmpdir()
        env = self._scons_env()
        # _scons_env already write-probed TMPDIR; keep both in sync.
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        env["CC"] = self._tool("c", ("clang", "cc", "gcc"))
        cflags = []
        if self.options.get_safe("fPIC"):
            # Static apr-util objects may end up inside shared libserf.
            cflags.append("-fPIC")
        if str(self.settings.build_type) == "Debug":
            cflags.append("-g")
        else:
            cflags.append("-O2")
        env["CFLAGS"] = " ".join(cflags)
        sh = self._device_shell()
        env["SHELL"] = sh
        env["CONFIG_SHELL"] = sh
        # E011/HMDFS: autoconf's `umask 077 && mktemp -d ./confXXXXXX`
        # yields an owner-unwritable dir on setgid filesystems; the configure
        # text patch already rewrites it to 022, and the process umask is
        # pinned here as well so every child (configure/make) inherits it.
        try:
            os.umask(0o022)
        except OSError:
            pass
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1 (if injected): shadow mktemp for
        # "./conf*" so autoconf falls back to its mkdir path.
        mktemp_shim = self._mktemp_fallback_shim_for_ohos(tmpdir)
        if mktemp_shim:
            env["PATH"] = mktemp_shim + os.pathsep + env.get("PATH", "")
            self.output.info("apr-util configure mktemp shim: %s" % mktemp_shim)
        self.output.info("apr-util writable tmpdir: %s" % tmpdir)
        make = ((os.environ.get("HMBS_MAKE", "") or "").strip()
                or shutil.which("make") or "make")
        apr_pkg = self.dependencies["apr"].package_folder
        expat_pkg = self.dependencies["expat"].package_folder
        apr_config, apr_build_dir, apr_bogus_dir = self._resolve_apr_build_dir(apr_pkg, sh, env)
        apu_build, apu_host = self._apu_triplets()
        self.output.info("Private apr-util triplets: build=%s host=%s"
                         % (apu_build, apu_host))
        self.output.info("Private apr-util apr-config: %s builddir: %s"
                         % (apr_config, apr_build_dir))
        # NOTE: apr-util configure understands neither --disable-shared nor
        # --enable-static (preflight warned "unrecognized options"); it
        # always builds via libtool and we pick libaprutil-1.a afterwards.
        try:
            subprocess.run([sh, "configure", "--prefix=%s" % prefix,
                            "--build=%s" % apu_build, "--host=%s" % apu_host,
                            "--with-apr=%s" % apr_config,
                            "--with-expat=%s" % expat_pkg],
                           cwd=src, env=env, check=True)
        except subprocess.CalledProcessError:
            self._dump_config_log(src)
            raise
        # configure's only use of APR_BUILD_DIR is
        # `cp $APR_BUILD_DIR/apr_rules.mk build/rules.mk` (not AC_SUBST'd);
        # with a relocated apr-1-config that cp silently fails while
        # configure still exits 0, so repair the copy from the validated
        # location before make.
        rules_dst = os.path.join(src, "build", "rules.mk")
        rules_ok = (os.path.isfile(rules_dst)
                    and os.path.getsize(rules_dst) > 0)
        if not rules_ok:
            rules_src = os.path.join(apr_build_dir, "apr_rules.mk")
            if not (os.path.isfile(rules_src)
                    and os.path.getsize(rules_src) > 0):
                raise ConanException(
                    "apr_rules.mk missing at both %s and validated %s"
                    % (rules_dst, rules_src))
            os.makedirs(os.path.join(src, "build"), exist_ok=True)
            shutil.copyfile(rules_src, rules_dst)
            self.output.info("repaired build/rules.mk from %s" % rules_src)
        # Second-round fix: configure bakes the bogus APR paths into every
        # generated Makefile (LIBTOOL=//build-1/libtool, -I//include), so
        # the rules.mk-only copy still leaves `bash //build-1/libtool`
        # failing. Rewrite all baked occurrences to the validated layout.
        self._repair_apr_relocation(src, apr_pkg, apr_build_dir, apr_bogus_dir)
        # HNP bash (make default SHELL) cannot getcwd on the HMFS-backed
        # conan cache (shell-init/job-working-directory errors), while the
        # HMBS-injected /bin/sh tolerates it (configure via sh showed no
        # such errors). Pin make recipes to that shell; cwd stays at src.
        env["SHELL"] = sh
        subprocess.run([make, "--jobs=1", "SHELL=%s" % sh], cwd=src, env=env, check=True)
        # Pre-create the private prefix so `make install` never depends on
        # `install -d` (the same shim family that just failed for files).
        for subdir in ("bin", "lib", "include"):
            try:
                os.makedirs(os.path.join(prefix, subdir), exist_ok=True)
            except OSError:
                pass
        usable_install = self._probe_usable_install(sh, tmpdir, env)
        install_args = [make, "install", "SHELL=%s" % sh]
        first_used_override = False
        if usable_install:
            # Override the configure-baked INSTALL (runtime shim) for both
            # the top-level Makefile and libtool --mode=install lines.
            install_args.append("INSTALL=%s -c" % usable_install)
            install_args.append("MKDIR_P=mkdir -p")
            first_used_override = True
        try:
            subprocess.run(install_args, cwd=src, env=env, check=True)
        except subprocess.CalledProcessError:
            # Fallback: the device install shim produced no file while
            # reporting success (2026-09-21 evidence). Retry once with the
            # probed install if the first attempt used the baked one, else
            # stage the built archive + apu-1-config + headers by hand so a
            # shim-only failure never blocks serf. Full `make install`
            # layout is preserved: lib/*.a, bin/apu-1-config, include/*.
            self.output.warning("make install failed; trying install fallback")
            retried = False
            if not first_used_override:
                if not usable_install:
                    usable_install = self._probe_usable_install(sh, tmpdir, env)
                if usable_install:
                    try:
                        subprocess.run(
                            [make, "install", "SHELL=%s" % sh,
                             "INSTALL=%s -c" % usable_install,
                             "MKDIR_P=mkdir -p"],
                            cwd=src, env=env, check=True)
                        retried = True
                    except subprocess.CalledProcessError as exc2:
                        self.output.warning("retry with INSTALL=%s also failed: %r"
                                            % (usable_install, exc2))
            if not retried:
                built_lib = os.path.join(src, ".libs", "libaprutil-1.a")
                if not os.path.isfile(built_lib):
                    # Some apr-util trees keep the archive at top level.
                    alt = os.path.join(src, "libaprutil-1.a")
                    built_lib = alt if os.path.isfile(alt) else built_lib
                if not os.path.isfile(built_lib):
                    self._dump_config_log(src)
                    raise
                self.output.warning(
                    "staging apr-util by hand from %s" % built_lib)
                try:
                    os.makedirs(os.path.join(prefix, "lib"), exist_ok=True)
                    shutil.copyfile(
                        built_lib,
                        os.path.join(prefix, "lib", "libaprutil-1.a"))
                except OSError as exc:
                    raise ConanException(
                        "manual apr-util lib staging failed: %r" % exc)
                # apu-1-config + headers: replicate `make install` layout.
                for cand in (os.path.join(src, "apu-1-config"),
                             os.path.join(src, "apu-1-config.out")):
                    if os.path.isfile(cand):
                        try:
                            os.makedirs(os.path.join(prefix, "bin"),
                                        exist_ok=True)
                            shutil.copyfile(
                                cand,
                                os.path.join(prefix, "bin", "apu-1-config"))
                            break
                        except OSError:
                            pass
                for hdr_root in (os.path.join(src, "include"),):
                    if os.path.isdir(hdr_root):
                        try:
                            shutil.copytree(
                                hdr_root,
                                os.path.join(prefix, "include"),
                                dirs_exist_ok=True)
                        except OSError as exc:
                            self.output.warning(
                                "manual header staging failed: %r" % exc)
                self.output.warning("manual apr-util staging done")
        if not os.path.isfile(os.path.join(prefix, "bin", "apu-1-config")):
            raise ConanException(
                "apu-1-config not found after private apr-util build in %s" % prefix)
        if not os.path.isfile(os.path.join(prefix, "lib", "libaprutil-1.a")):
            raise ConanException(
                "libaprutil-1.a not found after private apr-util install in %s/lib "
                "(install shim produced no file?)" % prefix)
        self.output.info("Private apr-util built at %s" % prefix)

    def generate(self):
        # Isolated SCons install, scoped to this build only (no system-wide
        # pollution, no network calls inside build()). Uses the community
        # pip index already configured on the worker.
        tmpdir = self._hmbs_tmpdir()
        # Propagate the writable temp root to every child process (pip and
        # SCons inherit os.environ via _scons_env()).
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        cache_dir = os.path.join(tmpdir, "pip-cache")
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError:
            cache_dir = tmpdir
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)
        self.run(
            "python3 -m pip install --quiet --no-input "
            "--cache-dir=\"%s\" --target=\"%s\" scons==%s" % (
                cache_dir, scons_prefix, self._SCONS_VERSION),
            env="build",
        )
        # Fork-pressure hygiene (libarchive-tools/3.8.8 precedent): pip
        # leaves wheels/sdists under cache_dir; on the constrained device
        # a full cache plus two source archives (serf bz2 + apr-util gz)
        # plus compiler processes exhausts memory and the next tar child
        # fails with "Cannot fork: Out of memory". Drop the cache now that
        # SCons is installed; _scons_env itself is kept (build needs it).
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
            os.makedirs(cache_dir, exist_ok=True)
            self.output.info("cleaned pip cache dir %s" % cache_dir)
        except OSError as exc:
            self.output.warning("pip cache cleanup failed %s: %r"
                                % (cache_dir, exc))
        # OHOS has no /bin/sh: point the SCons POSIX platform at the
        # system shell (same fix as gpsd/3.26).
        self.run(
            "PYTHONPATH=\"%s\" python3 -c \""
            "import SCons.Platform.posix as m;"
            "f=m.__file__;"
            "s=open(f).read();"
            "old=\\\"env['SHELL']          = 'sh'\\\";"
            "new=\\\"env['SHELL']          = '/system/bin/sh'\\\";"
            "open(f,'w').write(s.replace(old,new) if old in s else s);"
            "print('patched', f if old in s else '(noop)')"
            "\"" % scons_prefix,
            env="build",
        )
        vb = VirtualBuildEnv(self)
        vb.generate()
        env = Environment()
        env.define_path("PYTHONPATH", scons_prefix)
        env.vars(self).save_script("scons_env")

    def _tool(self, key, fallbacks):
        # R33: compilers come from Conan conf, never from shell env vars.
        # The conf value may point at a path missing on this worker, so
        # validate executability and fall back to PATH lookup.
        try:
            execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except ConanException:
            execs = {}
        configured = (execs.get(key) if execs else None) or None
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        if configured:
            self.output.warning(
                "tools.build:compiler_executables[%s]=%s not usable; "
                "falling back to PATH lookup" % (key, configured))
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        return fallbacks[0]

    def _ar_ranlib(self, cc):
        # Preflight 2026-09-21 (round 2): SCons died with
        #   /system/bin/sh: ar: inaccessible or not found
        #   scons: *** [libserf-1.a] Error 127
        # CC is absolute (/.../.harmonybrew/bin/clang) so compilation works,
        # but SCons invokes the archiver as bare `ar` through /system/bin/sh
        # whose PATH lacks the toolchain dir. Resolve explicit AR/RANLIB:
        # env override first, then the CC directory, then PATH lookup.
        # Probes are best-effort (`--version`); a missing file is skipped,
        # an existing file is accepted even if the probe fails (device shells
        # may report odd exit codes).
        def _probe(cand):
            try:
                if not cand or not os.path.isfile(cand):
                    return False
                if os.path.getsize(cand) <= 0:
                    return False
            except OSError:
                return False
            try:
                proc = subprocess.run(
                    [cand, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60)
                self.output.info("archiver probe %r -> exit %d" % (cand, proc.returncode))
            except Exception as exc:
                self.output.info("archiver probe %r could not run: %r" % (cand, exc))
            return True

        cc_dir = ""
        try:
            if cc and os.path.isabs(cc):
                cc_dir = os.path.dirname(cc)
        except Exception:
            cc_dir = ""
        ar_names = ("llvm-ar", "aarch64-linux-ohos-ar",
                    "aarch64-unknown-linux-ohos-ar", "ar")
        ranlib_names = ("llvm-ranlib", "aarch64-linux-ohos-ranlib",
                        "aarch64-unknown-linux-ohos-ranlib", "ranlib")
        ar = ""
        for key in ("AR", "HMBS_AR"):
            cand = (os.environ.get(key, "") or "").strip()
            if cand and _probe(cand):
                ar = cand
                break
        if not ar and cc_dir:
            for name in ar_names:
                cand = os.path.join(cc_dir, name)
                if _probe(cand):
                    ar = cand
                    break
        if not ar:
            for name in ar_names:
                try:
                    found = shutil.which(name)
                except Exception:
                    found = None
                if found and _probe(found):
                    ar = found
                    break
        ranlib = ""
        for key in ("RANLIB", "HMBS_RANLIB"):
            cand = (os.environ.get(key, "") or "").strip()
            if cand and _probe(cand):
                ranlib = cand
                break
        if not ranlib and cc_dir:
            for name in ranlib_names:
                cand = os.path.join(cc_dir, name)
                if _probe(cand):
                    ranlib = cand
                    break
        if not ranlib:
            for name in ranlib_names:
                try:
                    found = shutil.which(name)
                except Exception:
                    found = None
                if found and _probe(found):
                    ranlib = found
                    break
        # Last resort: llvm-ranlib is often just llvm-ar `s`; if only AR was
        # found, reuse it for RANLIB only when the name is a generic `ar`
        # family binary is not safe, so leave RANLIB empty instead.
        if ar:
            self.output.info("usable AR: %s" % ar)
        else:
            self.output.warning("no usable AR found (cc_dir=%r)" % cc_dir)
        if ranlib:
            self.output.info("usable RANLIB: %s" % ranlib)
        else:
            self.output.warning("no usable RANLIB found (cc_dir=%r)" % cc_dir)
        return ar, ranlib

    def _scons_env(self):
        env = dict(os.environ)
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        old = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = scons_prefix + (os.pathsep + old if old else "")
        # [readonly_tmp] hard gate: never let SCons/check.py/pip fall back
        # to read-only /tmp. Write-probe HMBS task-private dirs first
        # (coinor-vol/1.5.4 lesson: isdir/makedirs alone is not proof).
        tmpdir = ""
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = (env.get(key, "") or "").strip()
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs-write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                tmpdir = cand
                break
            except OSError:
                continue
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "_tmp")
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                tmpdir = self.build_folder
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        try:
            tempfile.tempdir = None
        except Exception:
            pass
        # Fork-pressure guard (libarchive-tools/3.8.8 precedent): the
        # device failed with "tar (child): Cannot fork: Out of memory".
        # Keep every child single-job / single-thread so a tar/bzip2 child
        # never competes with parallel compilers or threaded compressors.
        # setdefault only: never override an already-exported test env.
        env.setdefault("MAKEFLAGS", "-j1")
        env.setdefault("XZ_OPT", "-T1")
        env.setdefault("XZ_DEFAULTS", "-T 1")
        # SCons archiver round-4 (2026-09-21): SConstruct declares no
        # AR/RANLIB options, so command-line AR=... is reported as
        # "unknown variables" and ignored, and SCons executes archive
        # commands with env['ENV']['PATH'] (not the process PATH), so
        # process-PATH shims never take effect. Fix inside SConstruct
        # (see _patch_sconstruct_archiver): honor ARGUMENTS/environ
        # AR/RANLIB and propagate caller PATH into ENV['PATH'].
        # Here only prepend dirname(CC) to the process PATH (data still
        # lives in TMPDIR/build folders) and export resolved AR/RANLIB
        # into the process env for the SConstruct patch to consume.
        try:
            _cc_probe = self._tool("c", ("clang", "cc", "gcc"))
            _cc_dir = os.path.dirname(_cc_probe) if os.path.isabs(_cc_probe) else ""
            if _cc_dir and os.path.isdir(_cc_dir):
                _path = env.get("PATH", "")
                _parts = _path.split(os.pathsep) if _path else []
                if _cc_dir not in _parts:
                    env["PATH"] = _cc_dir + (os.pathsep + _path if _path else "")
                    self.output.info("prepended CC dir to PATH: %s" % _cc_dir)
            _ar_probe, _ranlib_probe = self._ar_ranlib(_cc_probe)
            if _ar_probe:
                env["AR"] = _ar_probe
                env["HMBS_AR"] = _ar_probe
            if _ranlib_probe:
                env["RANLIB"] = _ranlib_probe
                env["HMBS_RANLIB"] = _ranlib_probe
        except Exception as exc:
            self.output.warning("CC dir PATH prepend failed: %r" % exc)
        # Static-only gate (round-5): upstream SConstruct unconditionally
        # builds BOTH libserf-1.a and libserf-1.so via
        # env.Default(lib_static, lib_shared, pkgconfig), even for a static
        # (shared=False) package. The shared link absorbs the conan zlib
        # static archive, but archives/z/zlib/1.3.1 builds `--static`
        # WITHOUT -fPIC, so ld.lld fails on aarch64 with
        #   relocation R_AARCH64_ADR_PREL_PG_HI21 ... against symbol
        #   'z_errmsg'; recompile with -fPIC
        # (preflight 2026-09-21). Upstream `scons check` test programs link
        # explicitly against the STATIC lib (serflib = lib_static), so
        # skipping the shared object for a static package loses no test
        # coverage. A shared=True package still builds the shared lib and
        # still requires a PIC zlib (E541: zlib should stay static-only but
        # use PIC objects); that is zlib's own fix, not vendored here.
        try:
            shared_opt = self.options.get_safe("shared")
            static_only = (not shared_opt) if shared_opt is not None else True
        except Exception:
            static_only = True
        env["HMBS_SERF_STATIC_ONLY"] = "1" if static_only else "0"
        return env

    def _patch_sconstruct_archiver(self):
        # Round-4 root-cause fix: serf SConstruct.opts lists only
        # PREFIX/LIBDIR/APR/APU/OPENSSL/ZLIB/GSSAPI/DEBUG/APR_STATIC/
        # CC/CFLAGS/LIBS/LINKFLAGS/CPPFLAGS -- no AR/RANLIB. Hence the
        # round-2/3 `AR=/.../llvm-ar` argv entries were unknown vars
        # (SCons prints "Warning: Used unknown variables: AR, RANLIB")
        # and env.StaticLibrary kept using bare `ar` resolved via
        # env['ENV']['PATH'] (SCons default, missing the harmonybrew
        # toolchain dir) through /system/bin/sh -> Error 127.
        # Patch SConstruct once per source tree (idempotent marker) to:
        #  1) copy ARGUMENTS AR/RANLIB (else AR/HMBS_AR environ) into
        #     env['AR']/env['RANLIB'] before StaticLibrary is defined;
        #  2) propagate the caller process PATH into env['ENV']['PATH']
        #     so any remaining bare tool names resolve identically.
        # Pure-Python string edit: no external `patch` binary, no exec
        # bits (HMDFS ignores chmod), same pattern as _patch_apr_util.
        path = os.path.join(self.source_folder, "SConstruct")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                data = handle.read()
        except OSError as exc:
            raise ConanException("cannot read SConstruct %s: %r" % (path, exc))
        if "HMBS_OHOS_ARCHIVER" in data:
            self.output.info("SConstruct archiver patch already applied")
            self._patch_sconstruct_static_only()
            return
        anchor = "env = Environment(variables=opts,"
        if anchor not in data:
            raise ConanException(
                "SConstruct archiver anchor not found; refusing to patch")
        fix = (
            "env = Environment(variables=opts,\n"
            "                  tools=('default', 'textfile',),\n"
            "                  CPPPATH=['.', ],\n"
            "                  )\n"
            "# --- HMBS_OHOS_ARCHIVER (serf/1.3.10 round-4): SConstruct has no\n"
            "# --- AR/RANLIB options, so honour explicit overrides here.\n"
            "try:\n"
            "    for _hmbs_k in ('AR', 'RANLIB'):\n"
            "        _hmbs_v = ARGUMENTS.get(_hmbs_k, '')\n"
            "        if not _hmbs_v:\n"
            "            _hmbs_v = os.environ.get(_hmbs_k, '') or os.environ.get('HMBS_' + _hmbs_k, '')\n"
            "        if _hmbs_v:\n"
            "            env[_hmbs_k] = _hmbs_v\n"
            "    _hmbs_path = os.environ.get('PATH', '')\n"
            "    if _hmbs_path:\n"
            "        try:\n"
            "            _hmbs_env = env.get('ENV', {})\n"
            "            _hmbs_old = _hmbs_env.get('PATH', '')\n"
            "            if _hmbs_old and _hmbs_old not in _hmbs_path:\n"
            "                _hmbs_env['PATH'] = _hmbs_path + os.pathsep + _hmbs_old\n"
            "            else:\n"
            "                _hmbs_env['PATH'] = _hmbs_path\n"
            "            env['ENV'] = _hmbs_env\n"
            "        except Exception:\n"
            "            pass\n"
            "except Exception:\n"
            "    pass\n"
        )
        old_block = (
            "env = Environment(variables=opts,\n"
            "                  tools=('default', 'textfile',),\n"
            "                  CPPPATH=['.', ],\n"
            "                  )\n"
        )
        data = data.replace(old_block, fix, 1)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(data)
        except OSError as exc:
            raise ConanException("cannot write SConstruct %s: %r" % (path, exc))
        self.output.info("patched SConstruct with HMBS_OHOS_ARCHIVER")
        self._patch_sconstruct_static_only()
        self._patch_sconstruct_popen()

    def _patch_sconstruct_static_only(self):
        # Round-6 (2026-09-21): for a static (shared=False) package,
        # suppress the shared object entirely so `scons` / `scons check` /
        # `scons install` never attempt the shared link that absorbs the
        # non-PIC conan zlib static archive (archives/z/zlib/1.3.1 builds
        # `--static` without -fPIC by design, R26 system same-name rule, so
        # ld.lld fails on aarch64 with relocation R_AARCH64_ADR_PREL_PG_HI21
        # against symbol 'z_errmsg'; preflight 2026-09-21 evidence).
        # Root cause of round-5 rev2 still failing: 1.3.10 links every test
        # program via tenv.Prepend(LIBS=[LIBNAMESTATIC], LIBPATH=[thisdir])
        # instead of an explicit serflib file path, so SCons resolves
        # -lserf-1 against BOTH lib_static (libserf-1.a) and lib_shared
        # (libserf-1.so*) targets and builds both for `scons check` even
        # though Default was already patched. Suppressing only Default and
        # install-lib therefore still leaves the shared link in the check
        # graph. The fix guards SharedLibrary creation itself behind
        # HMBS_SERF_STATIC_ONLY (set in _scons_env): static builds get
        # lib_shared = [] so no shared node exists to depend on; shared
        # builds keep the original behaviour (still requires a PIC zlib).
        # Upstream test programs link the static archive, so `scons check`
        # coverage is unchanged. Pure-Python edits, idempotent via the
        # HMBS_SERF_NO_SHARED_TARGET marker.
        path = os.path.join(self.source_folder, "SConstruct")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                data = handle.read()
        except OSError as exc:
            raise ConanException("cannot read SConstruct %s: %r" % (path, exc))
        if "HMBS_SERF_NO_SHARED_TARGET" in data:
            self.output.info("SConstruct static-only patch already applied")
            return
        # Upgrade path: round-5 marker without the target guard (fresh
        # preflight sources never hit this; local rebuilds might).
        if "HMBS_SERF_STATIC_ONLY" in data:
            self.output.info("SConstruct has round-5 patch; upgrading to target guard")
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    raw = handle.read()
            except OSError as exc:
                raise ConanException("cannot re-read SConstruct %s: %r" % (path, exc))
            raise ConanException(
                "SConstruct round-5 patch present without target guard; "
                "wipe the source tree (conan source) and rebuild")
        shared_pat = re.compile(
            r"lib_static\s*=\s*env\.StaticLibrary\(LIBNAMESTATIC,\s*SOURCES\)\s*\n"
            r"lib_shared\s*=\s*env\.SharedLibrary\(LIBNAME,\s*SOURCES\s*\+\s*SHARED_SOURCES\)")
        new_shared = (
            "lib_static = env.StaticLibrary(LIBNAMESTATIC, SOURCES)\n"
            "# --- HMBS_SERF_NO_SHARED_TARGET (serf/1.3.10 round-6): static\n"
            "# --- package must not create the shared node (non-PIC libz.a).\n"
            "_hmbs_static_only = (os.environ.get('HMBS_SERF_STATIC_ONLY', '') == '1')\n"
            "if _hmbs_static_only:\n"
            "  lib_shared = []\n"
            "else:\n"
            "  lib_shared = env.SharedLibrary(LIBNAME, SOURCES + SHARED_SOURCES)"
        )
        m_shared = shared_pat.search(data)
        if not m_shared:
            raise ConanException(
                "SConstruct static-only anchor (SharedLibrary) not found; "
                "refusing to patch")
        data = (data[:m_shared.start()] + new_shared + data[m_shared.end():])
        self.output.info("patched SConstruct SharedLibrary for static-only")
        default_pat = re.compile(
            r"env\.Default\s*\(\s*lib_static\s*,\s*lib_shared\s*,\s*pkgconfig\s*\)")
        new_default = (
            "if _hmbs_static_only:\n"
            "  env.Default(lib_static, pkgconfig)\n"
            "else:\n"
            "  env.Default(lib_static, lib_shared, pkgconfig)"
        )
        m_default = default_pat.search(data)
        if m_default:
            data = (data[:m_default.start()] + new_default
                    + data[m_default.end():])
            self.output.info("patched SConstruct Default for static-only")
        else:
            self.output.warning(
                "SConstruct Default anchor not found; "
                "static-only Default patch skipped")
        install_pat = re.compile(
            r"install_static\s*=\s*env\.Install\(libdir,\s*lib_static\)\s*\n"
            r"install_shared\s*=\s*env\.InstallVersionedLib\(libdir,\s*lib_shared\)")
        new_install = (
            "install_static = env.Install(libdir, lib_static)\n"
            "if _hmbs_static_only:\n"
            "  install_shared = []\n"
            "else:\n"
            "  install_shared = env.InstallVersionedLib(libdir, lib_shared)"
        )
        m_install = install_pat.search(data)
        if m_install:
            data = (data[:m_install.start()] + new_install
                    + data[m_install.end():])
            self.output.info("patched SConstruct install_shared for static-only")
        else:
            self.output.warning(
                "SConstruct install_shared anchor not found; "
                "static-only install patch skipped")
        alias_pat = re.compile(
            r"env\.Alias\s*\(\s*['\"]install-lib['\"]\s*,\s*"
            r"\[\s*install_static\s*,\s*install_shared\s*,?\s*\]\s*\)")
        new_alias = (
            "if _hmbs_static_only:\n"
            "  env.Alias('install-lib', [install_static])\n"
            "else:\n"
            "  env.Alias('install-lib', [install_static, install_shared])"
        )
        m_alias = alias_pat.search(data)
        if m_alias:
            data = (data[:m_alias.start()] + new_alias
                    + data[m_alias.end():])
            self.output.info("patched SConstruct install-lib for static-only")
        else:
            self.output.warning(
                "SConstruct install-lib anchor variants not found; "
                "dumping candidates for diagnosis")
            for line in data.splitlines():
                if "install-lib" in line or "install_static" in line:
                    self.output.warning("[sconstruct] %s" % line.strip())
            raise ConanException(
                "SConstruct static-only anchor (install-lib) not found; "
                "refusing to patch")
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(data)
        except OSError as exc:
            raise ConanException("cannot write SConstruct %s: %r" % (path, exc))
        self.output.info("patched SConstruct with HMBS_SERF_NO_SHARED_TARGET")
        self._patch_sconstruct_popen()

    def _patch_sconstruct_popen(self):
        # CI #54842 (2026-09-22): SCons died while reading SConscript files
        #   Warning: Used unknown variables: AR, RANLIB
        #   Checking for GNU-compatible C compiler...yes
        #   TypeError: can't concat str to bytes:
        #     File ".../src/SConstruct", line 418:
        #       apr_libs = os.popen(env.subst(
        #         '$APR --link-libtool --libs')).read().strip()
        #     File "<frozen codecs>", line 321:
        # Upstream 1.3.10 captures `apr-1-config/apu-1-config
        # --link-libtool --libs` via os.popen(...).read(). On the CI
        # worker's python3 that read() raises TypeError inside the codecs
        # layer (bytes/str concat), aborting the whole build before any
        # compilation. Capture via subprocess with explicit bytes->str
        # decode instead; on any failure return '' (the pkg-config LIBS
        # line degrades, the build itself proceeds). Pure-Python string
        # edit, idempotent via the HMBS_POPEN_PY3 marker.
        path = os.path.join(self.source_folder, "SConstruct")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                data = handle.read()
        except OSError as exc:
            raise ConanException("cannot read SConstruct %s: %r" % (path, exc))
        if "HMBS_POPEN_PY3" in data:
            self.output.info("SConstruct popen patch already applied")
            return
        old_block = (
            "  if CALLOUT_OKAY:\n"
            "    apr_libs = os.popen(env.subst("
            "'$APR --link-libtool --libs')).read().strip()\n"
            "    apu_libs = os.popen(env.subst("
            "'$APU --link-libtool --libs')).read().strip()\n"
        )
        if old_block not in data:
            raise ConanException(
                "SConstruct popen anchor not found; refusing to patch")
        fix = (
            "  if CALLOUT_OKAY:\n"
            "    # --- HMBS_POPEN_PY3 (serf/1.3.10 CI #54842): os.popen read\n"
            "    # --- raises TypeError inside codecs on this worker; use\n"
            "    # --- subprocess with explicit decode so config-script\n"
            "    # --- output can never abort SCons startup.\n"
            "    import subprocess as _hmbs_subprocess\n"
            "    def _hmbs_cfg_output(_hmbs_cmd):\n"
            "      try:\n"
            "        if isinstance(_hmbs_cmd, bytes):\n"
            "          _hmbs_cmd = _hmbs_cmd.decode('utf-8', 'replace')\n"
            "        _hmbs_cmd = str(_hmbs_cmd)\n"
            "        _hmbs_proc = _hmbs_subprocess.run(\n"
            "            _hmbs_cmd, shell=True,\n"
            "            stdout=_hmbs_subprocess.PIPE,\n"
            "            stderr=_hmbs_subprocess.DEVNULL, timeout=120)\n"
            "        _hmbs_out = _hmbs_proc.stdout or b''\n"
            "        if isinstance(_hmbs_out, bytes):\n"
            "          _hmbs_out = _hmbs_out.decode('utf-8', 'replace')\n"
            "        return str(_hmbs_out).strip()\n"
            "      except Exception:\n"
            "        return ''\n"
            "    apr_libs = _hmbs_cfg_output("
            "env.subst('$APR --link-libtool --libs'))\n"
            "    apu_libs = _hmbs_cfg_output("
            "env.subst('$APU --link-libtool --libs'))\n"
        )
        data = data.replace(old_block, fix, 1)
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(data)
        except OSError as exc:
            raise ConanException("cannot write SConstruct %s: %r" % (path, exc))
        self.output.info("patched SConstruct with HMBS_POPEN_PY3")

    def _scons_args(self):
        # Aggregate the dependency closure (conan-center serf precedent):
        # apr/expat/openssl/zlib include + lib dirs reach the compiler
        # via CPPFLAGS/LINKFLAGS; APR/OPENSSL/ZLIB point at the package
        # roots so SConstruct picks up bin/apr-1-config + include/lib.
        # APU instead points at the private apr-util prefix built in
        # _build_apr_util() (SConstruct resolves bin/apu-1-config from it).
        incs = []
        libdirs = []
        libs = []
        for _req, _dep in self.dependencies.items():
            pkg = getattr(_dep, "package_folder", "") or ""
            try:
                infos = [_dep.cpp_info] + list(_dep.cpp_info.components.values())
            except Exception:
                infos = [_dep.cpp_info]
            for _info in infos:
                for p in getattr(_info, "includedirs", []):
                    a = p if os.path.isabs(p) else os.path.join(pkg, p)
                    if a not in incs:
                        incs.append(a)
                for p in getattr(_info, "libdirs", []):
                    a = p if os.path.isabs(p) else os.path.join(pkg, p)
                    if a not in libdirs:
                        libdirs.append(a)
                for lib in getattr(_info, "libs", []):
                    if lib not in libs:
                        libs.append(lib)
        cc = self._tool("c", ("clang", "cc", "gcc"))
        ar, ranlib = self._ar_ranlib(cc)
        cflags = []
        if self.options.get_safe("fPIC"):
            cflags.append("-fPIC")
        if str(self.settings.build_type) == "Debug":
            cflags.append("-g")
        else:
            cflags.append("-O2")
        # NOTE: cmd is a list executed without shell, so values must NOT be
        # shell-quoted. Previous esc() wrapped every value in double quotes,
        # making SCons see DEBUG='"False"' (with literal quotes) and die with
        # "Error converting option: 'DEBUG' / Invalid value for boolean
        # variable: '\"False\"'" (preflight 2026-09-21). Pass KEY=value raw;
        # single argv elements already preserve embedded spaces, and flag
        # paths need no inner single quotes either.
        args = {
            "APR": self.dependencies["apr"].package_folder,
            "APU": self._apu_prefix(),
            "OPENSSL": self.dependencies["openssl"].package_folder,
            "ZLIB": self.dependencies["zlib"].package_folder,
            "PREFIX": self.package_folder,
            "LIBDIR": os.path.join(self.package_folder, "lib"),
            "DEBUG": "True" if str(self.settings.build_type) == "Debug" else "False",
            "APR_STATIC": "True" if not self.dependencies["apr"].options.shared else "False",
            "CC": cc,
            "CFLAGS": " ".join(cflags),
            "LINKFLAGS": " ".join("-L%s" % d for d in libdirs),
            "CPPFLAGS": " ".join("-I%s" % d for d in incs),
            "LIBS": " ".join(libs),
        }
        # Explicit archiver so SCons never relies on bare `ar` lookup under
        # /system/bin/sh (round-2 Error 127). Only set when resolved; an
        # empty AR would override SCons defaults with a broken value.
        if ar:
            args["AR"] = ar
        if ranlib:
            args["RANLIB"] = ranlib
        python3 = shutil.which("python3") or "python3"
        cmd = [python3, "-m", "SCons", "-Y", self.source_folder, "--jobs=1"]
        cmd += ["%s=%s" % (k, v) for k, v in args.items()]
        return cmd, args

    def build(self):
        apply_conandata_patches(self)
        self._patch_sconstruct_archiver()
        self._build_apr_util()
        cmd, _args = self._scons_args()
        self.output.info("Building serf: %s" % " ".join(cmd))
        subprocess.run(cmd, cwd=self.source_folder,
                       env=self._scons_env(), check=True)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Upstream suite entry: `scons check` builds the 6 test programs and
        # runs build/check.py, which executes each test/testcases/*.response
        # fixture through serf_response and then the CuTest test_all binary
        # (suites: context, buckets, ssl, auth). check.py exits non-zero on
        # the first failure, so a zero exit means every fixture passed.
        case_dir = os.path.join(self.source_folder, "test", "testcases")
        fixtures = sorted(glob.glob(os.path.join(case_dir, "*.response")))
        non_empty = [f for f in fixtures
                     if os.path.isfile(f) and os.path.getsize(f) > 0]
        if len(non_empty) != len(fixtures) or not fixtures:
            # Falsifiability guard (toybox tar-B lesson): empty or missing
            # fixtures would let every case "pass" against empty input.
            raise ConanException(
                "upstream serf fixtures missing or empty in %s "
                "(found %d, non-empty %d)" % (case_dir, len(fixtures), len(non_empty)))
        cmd, _args = self._scons_args()
        check_cmd = cmd + ["check"]
        self.output.info("Running upstream serf suite: %s" % " ".join(check_cmd))
        try:
            proc = subprocess.run(
                check_cmd, cwd=self.source_folder, env=self._scons_env(),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=1800)
        except Exception as exc:
            raise ConanException("upstream test harness could not run: %r" % exc)
        output = proc.stdout or ""
        for line in output.splitlines()[-40:]:
            self.output.info("[upstream] %s" % line)
        # Fixture evidence: one "== Testing <case> ==" line per fixture.
        tested = re.findall(r"^== Testing (.+) ==$", output, re.M)
        # Unit evidence: CuTest prints one '.'/'F' char per test, then
        # "OK (N tests)" on success or "Runs: N Passes: M Fails: K".
        dots = re.findall(r"^[.F]+$", output, re.M)
        unit_chars = "".join(dots)
        unit_total = len(unit_chars)
        unit_failed = unit_chars.count("F")
        ok_match = re.search(r"OK \((\d+) tests?\)", output)
        tally = re.search(r"Runs:\s*(\d+)\s+Passes:\s*(\d+)\s+Fails:\s*(\d+)", output)
        if ok_match is not None:
            unit_ok = int(ok_match.group(1))
            if unit_total and unit_total != unit_ok:
                raise ConanException(
                    "CuTest progress chars (%d) disagree with OK (%d); "
                    "refusing to certify" % (unit_total, unit_ok))
            unit_total = unit_total or unit_ok
        elif tally is not None:
            runs, passes, fails = (int(tally.group(1)), int(tally.group(2)),
                                   int(tally.group(3)))
            unit_total = unit_total or runs
            unit_failed = unit_failed or fails
        discovered = len(fixtures) + unit_total
        self.output.info(
            "Upstream tally: fixtures=%d tested=%d unit_total=%d unit_failed=%d" % (
                len(fixtures), len(tested), unit_total, unit_failed))
        if proc.returncode != 0:
            status = "failed"
        elif len(tested) < len(fixtures) or unit_total <= 0 or unit_failed > 0:
            status = "failed"
        else:
            status = "passed"
        executed = len(tested) + (unit_total - unit_failed)
        passed = executed if status == "passed" else 0
        failed = (len(fixtures) - len(tested)) + unit_failed
        if status != "passed":
            failed = max(failed, 1)
        marker = {
            "status": status,
            "framework": "scons-check",
            "command": "python3 -m SCons check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if status != "passed":
            marker["reason"] = "output tail: %s" % " | ".join(output.splitlines()[-5:])
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker)
        print(line, flush=True)
        self.output.info(line)
        sys.stdout.flush()
        try:
            result_path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
        except OSError as exc:
            raise ConanException("failed to persist upstream_test_result.json: %s" % exc)
        if status != "passed":
            raise ConanException(
                "upstream serf suite failed "
                "(fixtures tested %d/%d, unit_total=%d unit_failed=%d)" % (
                    len(tested), len(fixtures), unit_total, unit_failed))

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        cmd, _args = self._scons_args()
        install_cmd = cmd + ["install"]
        self.output.info("Installing serf: %s" % " ".join(install_cmd))
        subprocess.run(install_cmd, cwd=self.source_folder,
                       env=self._scons_env(), check=True)
        # Merge the privately built apr-util static library so consumers
        # (and test_package) can link -laprutil-1 without a remote apr-util
        # package. Headers must be merged too: the installed
        # include/serf-1/serf.h does `#include <apr_uri.h>` (an apr-util
        # header), so consumers fail with `fatal error: 'apr_uri.h' file
        # not found` unless the vendored headers ship in this package
        # (preflight 2026-09-21 test_package evidence).
        libdir = os.path.join(self.package_folder, "lib")
        apu_lib_dir = os.path.join(self._apu_prefix(), "lib")
        if not os.path.isfile(os.path.join(apu_lib_dir, "libaprutil-1.a")):
            raise ConanException(
                "private libaprutil-1.a missing in %s "
                "(apr-util sub-build did not run?)" % apu_lib_dir)
        copy(self, "libaprutil-1.a", src=apu_lib_dir,
             dst=libdir, keep_path=False)
        apu_inc = os.path.join(self._apu_prefix(), "include")
        if not os.path.isdir(apu_inc):
            raise ConanException(
                "private apr-util include dir missing in %s "
                "(apr-util sub-build did not install headers?)" % apu_inc)
        inc_dst = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dst, exist_ok=True)
        staged = 0
        for root, _dirs, files in os.walk(apu_inc):
            for fn in files:
                if not fn.endswith(".h"):
                    continue
                src_path = os.path.join(root, fn)
                rel = os.path.relpath(src_path, apu_inc)
                # Preserve the upstream layout (e.g. include/apr-1/*.h) so
                # both <apr_uri.h> and <apr-1/apr_uri.h> styles keep working.
                dst_path = os.path.join(inc_dst, rel)
                try:
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copyfile(src_path, dst_path)
                    staged += 1
                except OSError as exc:
                    raise ConanException(
                        "failed to stage apr-util header %s: %r" % (src_path, exc))
                # Flatten one level as well: apr-util may install under
                # include/apr-1/, but serf.h uses flat `#include <apr_uri.h>`.
                flat_path = os.path.join(inc_dst, fn)
                if dst_path != flat_path and not os.path.isfile(flat_path):
                    try:
                        shutil.copyfile(src_path, flat_path)
                        staged += 1
                    except OSError as exc:
                        raise ConanException(
                            "failed to flatten apr-util header %s: %r" % (src_path, exc))
        if staged == 0:
            raise ConanException(
                "no apr-util headers staged from %s" % apu_inc)
        apu_uri = os.path.join(inc_dst, "apr_uri.h")
        if not os.path.isfile(apu_uri):
            raise ConanException(
                "apr_uri.h missing after staging from %s "
                "(staged %d files)" % (apu_inc, staged))
        self.output.info(
            "staged %d private apr-util headers (apr_uri.h ok) from %s"
            % (staged, apu_inc))
        # SCons always builds both archives; keep only the selected linkage.
        # The private libaprutil-1.a is always kept (static by design).
        if os.path.isdir(libdir):
            for fn in os.listdir(libdir):
                path = os.path.join(libdir, fn)
                if not os.path.isfile(path):
                    continue
                if self.options.shared and fn.endswith(".a") and fn != "libaprutil-1.a":
                    os.unlink(path)
                elif not self.options.shared and fn.endswith(".so"):
                    os.unlink(path)
        # Ship the persisted upstream result so test_package can re-emit the
        # identical HMBS_UPSTREAM_TEST_RESULT marker even when conan skips
        # build() on a cached binary ("Already installed!").
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_path):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=res_dir, keep_path=False)
        else:
            self.output.warning("upstream_test_result.json not found in build "
                                "folder; package will lack upstream evidence")

    def package_info(self):
        # libaprutil-1 is the privately built static apr-util merged in
        # package(): consumers need it for serf's undefined apr-util symbols
        # (e.g. apr_uri_*). expat reaches consumers transitively via requires.
        self.cpp_info.libs = ["serf-1", "aprutil-1"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "serf-1"),
                                     os.path.join("include", "apr-1")]
        self.cpp_info.set_property("cmake_file_name", "serf")
        self.cpp_info.set_property("cmake_target_name", "serf::serf")
        self.cpp_info.set_property("pkg_config_name", "serf-1")
