#!/usr/bin/env python3
"""Conan recipe — cntlm 0.94.0 (Makefile)"""

import os
import subprocess

from conan import ConanFile
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches


class CntlmConan(ConanFile):
    name = "cntlm"
    version = "0.94.0"
    description = "NTLM/NTLMv2 authenticating HTTP proxy with tunneling support"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/versat/cntlm"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tmpdir(self):
        # E002: OHOS /tmp is read-only (erofs). Prefer HMBS-injected writable
        # dirs, including the autoconf mktemp fallback dir when provided.
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.environ.get(key)
            if val and val != "0" and val != "/tmp":
                return val
        return os.path.join(self.build_folder, "tmp")

    def _conan_cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang") if isinstance(compilers, dict) else "clang"
        return cc

    def generate(self):
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        cc = self._conan_cc()
        # E002: OHOS /tmp is read-only (erofs). Toolchain (clang driver,
        # make $(shell ...), /bin/sh command substitution) needs a writable
        # temp dir. Prefer the HMBS-injected TMPDIR/TMP/TEMP, fall back to a
        # build-folder private tmp dir. Defined via conanbuild script so both
        # configure and make inherit it.
        tmpdir = self._resolve_tmpdir()
        env = Environment()
        env.define("CC", cc)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # NOTE: use a distinct script name so the aggregated conanbuild.sh
        # from VirtualBuildEnv (PATH to HMBS tools) is extended, not replaced.
        env.vars(self).save_script("conanbuild_cntlm_tmpdir")

    def _synthesize_cntlm_config(self, cc, tmpdir):
        """Reproduce upstream ./configure outputs without running it.

        Upstream configure is a /bin/sh script that (a) uses command
        substitution ($(which ...), $(./config/...)) which forces /bin/sh to
        create /tmp/shXXXXXX temp files (read-only erofs on OHOS), and (b)
        compiles AND executes 9 probe programs (./config/<name>). Probe
        execution is what dies with Signal 9 on the preflight worker, and
        even a successful run would still trip the read-only /tmp shell
        temp files. TMPDIR export alone cannot fix either: dash ignores
        TMPDIR for its internal temp files.

        This helper writes the same two artifacts (configure-stamp and
        config/config.h) in pure Python: stamp carries the Conan CC so the
        Makefile's `CC := $(shell head -n 1 $(STAMP))` resolves without
        re-probing (stamp presence also disables the Makefile's
        `_ := $(shell ./configure)` auto-probe line), and config.h carries
        one `#define config_<name> <rc>` per probe with Linux/OHOS-audited
        values. Each probe is still COMPILED (not executed) with the real
        CC to prove headers/link work; a compile failure yields 0, matching
        upstream's `RET=no` path. Values for risky probes default to the
        safe (fallback-enabled) side: claiming 1 when the symbol is missing
        would break the link, while claiming 0 only enables upstream's
        bundled replacement.
        """
        src = self.source_folder
        stamp = os.path.join(src, "configure-stamp")
        try:
            with open(stamp, "w", encoding="utf-8", newline="\n") as f:
                f.write(cc + "\n")
        except OSError as exc:
            raise RuntimeError(f"cannot write configure-stamp: {exc}")

        # Audited expectations for Linux aarch64 / OHOS (LE, POSIX libc):
        # endian=1 (LE returns 1), gethostname=0 (rc=!strlen -> 0 when a
        # hostname exists, the normal Linux value), socklen_t=1, strdup=1,
        # the rest 0 (no BSD/GSS/Annex-K symbols on glibc/OHOS libc, so
        # upstream compiles fall back to bundled replacements; gss probe
        # additionally lacks headers and -ldl in its compile line).
        audited = {
            "endian": 1,
            "gethostname": 0,
            "socklen_t": 1,
            "strdup": 1,
            "arc4random_buf": 0,
            "strlcat": 0,
            "strlcpy": 0,
            "memset_s": 0,
            "gss": 0,
        }
        cflags = [
            "-std=c99", "-D__BSD_VISIBLE", "-D_ALL_SOURCE",
            "-D_XOPEN_SOURCE=600", "-D_POSIX_C_SOURCE=200112",
            "-D_ISOC99_SOURCE", "-D_REENTRANT", "-D_BSD_SOURCE",
            "-D_DEFAULT_SOURCE", "-D_DARWIN_C_SOURCE",
        ]
        probe_dir = os.path.join(src, "config")
        scratch = os.path.join(self.build_folder, "tmp", "probe")
        os.makedirs(scratch, exist_ok=True)
        results = {}
        run_env = dict(os.environ)
        run_env["TMPDIR"] = tmpdir
        run_env["TMP"] = tmpdir
        run_env["TEMP"] = tmpdir
        for name, want in audited.items():
            cfile = os.path.join(probe_dir, name + ".c")
            exe = os.path.join(scratch, name)
            rc_val = 0
            try:
                if os.path.isfile(cfile):
                    proc = subprocess.run(
                        [cc] + cflags + ["-o", exe, cfile],
                        cwd=src, env=run_env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, timeout=120,
                    )
                    if proc.returncode == 0:
                        rc_val = want
                    else:
                        rc_val = 0
                else:
                    rc_val = 0
            except Exception as exc:
                self.output.warning(f"probe compile {name} failed ({exc}); using 0")
                rc_val = 0
            finally:
                try:
                    if os.path.exists(exe):
                        os.remove(exe)
                except OSError:
                    pass
            results[name] = rc_val
            self.output.info(f"cntlm probe {name}: config_{name}={rc_val}")

        cfg_path = os.path.join(probe_dir, "config.h")
        lines = ["#ifndef CONFIGURE_CONFIG_H", "#define CONFIGURE_CONFIG_H", ""]
        for name in audited:
            lines.append(f"#define config_{name} {results[name]}")
        lines += ["", "#endif // CONFIGURE_CONFIG_H", ""]
        try:
            with open(cfg_path, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(lines))
        except OSError as exc:
            raise RuntimeError(f"cannot write config/config.h: {exc}")

    def _fix_u_char_portability(self):
        # Upstream config.c (5x) and utils.c (2x) cast ctype arguments with
        # the BSD typedef (u_char). OHOS libc under -std=c99 does not
        # provide u_char (glibc exposes it only via _BSD_SOURCE /
        # _DEFAULT_SOURCE; utils.c already includes <sys/types.h> yet still
        # fails), and config.c does not include <sys/types.h> at all. A
        # declarative conandata patch was tried first but the worker's
        # Conan patch parser rejected the stream ("patch stream is
        # incomplete"), so do the equivalent replacement procedurally in
        # Python: u_char is always typedef-compatible with unsigned char,
        # and the ctype casts only need an unsigned-char value. Sweep all
        # C sources/headers so un-audited files with the same idiom are
        # covered without enumerating them.
        fixed = []
        src = self.source_folder
        for root, _, files in os.walk(src):
            for fn in files:
                if not fn.endswith((".c", ".h")):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="strict") as f:
                        text = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                if "(u_char)" in text:
                    text = text.replace("(u_char)", "(unsigned char)")
                    try:
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(text)
                    except OSError as exc:
                        raise RuntimeError(f"cannot fix u_char in {path}: {exc}")
                    fixed.append(os.path.relpath(path, src))
        if fixed:
            self.output.info(f"cntlm u_char portability fix applied to: {', '.join(sorted(fixed))}")

    def build(self):
        apply_conandata_patches(self)
        self._fix_u_char_portability()
        # E002: ensure the writable tmp dir exists in this process and is
        # exported, so clang temp files never fall back to read-only /tmp.
        tmpdir = self._resolve_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        cc = self._conan_cc()
        # Do NOT run upstream ./configure: its $(...) substitutions need
        # writable /tmp/sh*.tmp (read-only erofs) and its probe execution
        # dies with Signal 9 on the worker. Synthesize its two outputs
        # (configure-stamp + config/config.h) in Python instead; stamp
        # presence also stops make from auto-running ./configure via
        # `_ := $(shell ./configure)`.
        self._synthesize_cntlm_config(cc, tmpdir)
        make = (
            os.environ.get("HMBS_MAKE")
            or self.conf.get("user.hmbs:make_path", default=None)
            or "make"
        )
        self.run(f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}" {make} CC="{cc}" -j1')

    def package(self):
        copy(self, "cntlm", self.source_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "cntlm.1", os.path.join(self.source_folder, "doc"), os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "cntlm.conf", os.path.join(self.source_folder, "doc"), os.path.join(self.package_folder, "share", "doc", "cntlm"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
