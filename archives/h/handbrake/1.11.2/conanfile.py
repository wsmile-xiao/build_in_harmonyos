#!/usr/bin/env python3
"""Conan recipe for HandBrakeCLI 1.11.2 — HandBrake custom make build.

HandBrake does NOT use Autotools for its own top-level build: `./configure` is a
Python-driven custom configure (make/configure.py) that generates a `build/`
scratch dir with a GNUmakefile, then `make` in build/ builds all 33 contribs
(ffmpeg, x264, x265, libvpx, libass, dav1d, svt-av1, ...) in-tree plus the
libhb library and finally links build/HandBrakeCLI.

Adaptation highlights (see notes.md for the full matrix):
- make/config.guess patched to recognize `aarch64-unknown-linux-ohos` (E007)
- Hardware encoders disabled (--disable-nvenc/nvdec/qsv/vce/mf/libdovi/gtk/numa)
- OHOS-specific contrib fixes via per-contrib A01 patches + module.defs changes
- official release source asset used so version.txt is present without patching
- HandBrakeCLI binary self-signed (ELF codesign) so it executes on OHOS

R32: settings.os checked with in ("Linux", "OHOS").
R33: compilers come from self.conf (profile conf), never from shell vars.
R34: test_package executes the real HandBrakeCLI --version.
R38: command-line tool -> package_type="application", bindirs=["bin"].
"""
import os
import re
import glob
import shutil
import shlex
import hashlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from conan import ConanFile
from conan.tools.files import (
    copy, unzip, apply_conandata_patches, export_conandata_patches, download,
)
from conan.tools.layout import basic_layout

# Local verification speedup (opt-in): when HANDBRAKE_BUILD_CACHE points at an
# existing exploratory build tree, build() reuses its prebuilt contribs so
# `conan create` finishes in minutes instead of ~6h. The env var is NEVER set
# on CI, so conan create there always performs a full self-contained build from
# clean source (R19: 产物必须由 CI 从源码构建). No machine-specific path is
# hardcoded in the recipe.
_CACHE_ROOT = os.environ.get("HANDBRAKE_BUILD_CACHE", "").strip()

# Mirrors are used only by the custom downloader for the official source asset
# and HandBrake's upstream contrib distfiles. conandata.yml stays official-only.
_GH_MIRRORS = (
    "https://gh-proxy.com/",
    "https://mirror.ghproxy.com/",
    "https://ghproxy.com/",
    "https://moeyy.cn/gh-proxy/",
)


class HandbrakeConan(ConanFile):
    name = "handbrake"
    version = "1.11.2"
    description = "HandBrake — open-source, GPL-licensed, multiplatform video transcoder (HandBrakeCLI)"
    license = "GPL-2.0-only"
    homepage = "https://handbrake.fr"
    url = "https://github.com/HandBrake/HandBrake"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All 33 contribs (ffmpeg/x264/x265/libvpx/libass/dav1d/svt-av1/...) are
        # built in-tree by HandBrake's own build system, so there are no Conan
        # package dependencies (R36: nothing to publish beforehand).
        pass

    def build_requirements(self):
        # HandBrake's custom configure (make/configure.py) probes automake and
        # libtool with abort=True. The OHOS CI worker does not ship autotools,
        # so pull them in as build tools (same pattern as argp-standalone etc.).
        self.tool_requires("m4/1.4.19")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        if self.settings.os == "OHOS":
            # Conan automake is a Perl script and newer workers do not expose a
            # system perl at /data/service/hnp/bin/perl.
            self.tool_requires("perl/5.42.2")

    def layout(self):
        # HandBrake builds in-tree (configure creates `build/` under the source
        # root and make runs there). Keep the default conan folders.
        basic_layout(self)

    def source(self):
        # Download the official release source asset through Conan's downloader
        # so CI L0 does not reject shell-level external downloaders.  Mirrors are
        # still tried first by _download_one().
        src = self.conan_data["sources"]
        url = src.get("url")
        urls = list(url) if isinstance(url, (list, tuple)) else [url]
        sha256 = src.get("sha256")
        bases = []
        for u in urls:
            raw = u
            for prefix in _GH_MIRRORS:
                if raw.startswith(prefix):
                    raw = raw[len(prefix):]
                    break
            if raw.startswith("https://gitclone.com/github.com/"):
                raw = "https://" + raw[len("https://gitclone.com/"):]
            if raw.startswith("https://kkgithub.com/"):
                raw = "https://github.com/" + raw[len("https://kkgithub.com/"):]
            if raw not in bases:
                bases.append(raw)
        tarball = os.path.join(self.source_folder, "_handbrake-src.tar.bz2")
        reused_source = False
        try:
            self._download_one(
                "HandBrake-1.11.2-source.tar.bz2", bases, sha256, tarball,
                file_timeout=300,
            )
            unzip(self, tarball, destination=self.source_folder, strip_root=True)
            try:
                os.unlink(tarball)
            except OSError:
                pass
        except Exception as exc:
            reused_source = self._copy_cached_source()
            if not reused_source:
                raise exc
        if reused_source and self._source_already_patched():
            self.output.warning("cached HandBrake source already contains OHOS patches")
        else:
            apply_conandata_patches(self)
        self._ensure_libiconv_a02_patch()

    def _copy_cached_source(self):
        """Reuse an already-unpacked official source from this CONAN_HOME."""
        conan_home = os.environ.get("CONAN_HOME")
        if not conan_home:
            return False
        pkg_cache = os.path.join(conan_home, "p")
        if not os.path.isdir(pkg_cache):
            return False
        this_src = os.path.realpath(self.source_folder)
        candidates = []
        for version_file in glob.glob(os.path.join(pkg_cache, "handb*", "s", "version.txt")):
            src_dir = os.path.dirname(version_file)
            if os.path.realpath(src_dir) == this_src:
                continue
            if not os.path.isfile(os.path.join(src_dir, "configure")):
                continue
            candidates.append(src_dir)
        for src_dir in sorted(candidates, key=lambda p: os.path.getmtime(p), reverse=True):
            try:
                shutil.copytree(src_dir, self.source_folder, dirs_exist_ok=True)
                self.output.warning(f"reused cached HandBrake source: {src_dir}")
                return True
            except Exception as exc:
                self.output.warning(f"cached HandBrake source skipped: {src_dir}: {exc}")
        return False

    def _copy_cached_distfile(self, basename, sha256, dst):
        """Reuse a previously verified HandBrake distfile from this CONAN_HOME."""
        conan_home = os.environ.get("CONAN_HOME")
        if not conan_home:
            return False
        pkg_cache = os.path.join(conan_home, "p")
        if not os.path.isdir(pkg_cache):
            return False

        this_dst = os.path.realpath(dst)
        patterns = (
            os.path.join(pkg_cache, "b", "handb*", "b", "download", basename),
            os.path.join(pkg_cache, "b", "*", "b", "download", basename),
            os.path.join(pkg_cache, "handb*", "s", "download", basename),
        )
        candidates = []
        seen = set()
        for pattern in patterns:
            for cand in glob.glob(pattern):
                real = os.path.realpath(cand)
                if real == this_dst or real in seen or not os.path.isfile(cand):
                    continue
                seen.add(real)
                candidates.append(cand)

        for cand in sorted(candidates, key=lambda p: os.path.getmtime(p), reverse=True):
            try:
                if sha256:
                    digest = hashlib.sha256(open(cand, "rb").read()).hexdigest()
                    if digest != sha256:
                        continue
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                tmp = dst + ".tmp"
                shutil.copy2(cand, tmp)
                os.replace(tmp, dst)
                self.output.info(f"reused cached distfile: {basename}")
                return True
            except Exception as exc:
                self.output.warning(f"cached distfile skipped: {cand}: {exc}")
                try:
                    if os.path.exists(dst + ".tmp"):
                        os.unlink(dst + ".tmp")
                except OSError:
                    pass
        return False

    def _source_already_patched(self):
        checks = (
            os.path.join(self.source_folder, "make", "config.guess"),
            os.path.join(self.source_folder, "contrib", "ffmpeg", "module.defs"),
            os.path.join(self.source_folder, "make", "configure.py"),
        )
        try:
            config_guess = open(checks[0], encoding="utf-8", errors="ignore").read()
            ffmpeg_defs = open(checks[1], encoding="utf-8", errors="ignore").read()
            configure_py = open(checks[2], encoding="utf-8", errors="ignore").read()
        except OSError:
            return False
        return (
            "HarmonyOS" in config_guess
            and "--target-os=linux" in ffmpeg_defs
            and "nasm" in configure_py and "abort=False" in configure_py
        )

    def _ensure_libiconv_a02_patch(self):
        """Keep generated libiconv A02 patch complete even with source reuse."""
        path = os.path.join(
            self.source_folder, "contrib", "libiconv",
            "A02-config-status-umask-ohos.patch",
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = "\n".join((
            "--- a/configure",
            "+++ b/configure",
            "@@ -34924,12 +34924,12 @@",
            " # Create a (secure) tmp directory for tmp files.",
            " ",
            " {",
            "-  tmp=`(umask 077 && mktemp -d \"./confXXXXXX\") 2>/dev/null` &&",
            "+  tmp=`(umask 022 && mktemp -d \"./confXXXXXX\") 2>/dev/null` &&",
            "   test -d \"$tmp\"",
            " }  ||",
            " {",
            "   tmp=./conf$$-$RANDOM",
            "-  (umask 077 && mkdir \"$tmp\")",
            "+  (umask 022 && mkdir \"$tmp\")",
            " } || as_fn_error $? \"cannot create a temporary directory in .\" \"$LINENO\" 5",
            " ac_tmp=$tmp",
            " ",
            "--- a/libcharset/configure",
            "+++ b/libcharset/configure",
            "@@ -20334,12 +20334,12 @@",
            " # Create a (secure) tmp directory for tmp files.",
            " ",
            " {",
            "-  tmp=`(umask 077 && mktemp -d \"./confXXXXXX\") 2>/dev/null` &&",
            "+  tmp=`(umask 022 && mktemp -d \"./confXXXXXX\") 2>/dev/null` &&",
            "   test -d \"$tmp\"",
            " }  ||",
            " {",
            "   tmp=./conf$$-$RANDOM",
            "-  (umask 077 && mkdir \"$tmp\")",
            "+  (umask 022 && mkdir \"$tmp\")",
            " } || as_fn_error $? \"cannot create a temporary directory in .\" \"$LINENO\" 5",
            " ac_tmp=$tmp",
            "",
        ))
        try:
            current = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            current = None
        if current != content:
            open(path, "w", encoding="utf-8").write(content)
            self.output.info("refreshed libiconv A02 config.status patch")

    # ─────────────────────────────────────────────────────────────────────
    # Local verification speedup: reuse the already-built exploratory tree.
    # ─────────────────────────────────────────────────────────────────────
    def _seed_local_cache(self):
        """Copy distfile cache + prebuilt contrib/libhb/test from the exploratory
        build dir so make() skips the (very long) contrib rebuilds.

        Returns True when the cache was reused, False when a full build is needed.
        """
        # CI leaves HANDBRAKE_BUILD_CACHE unset; empty root must not resolve to
        # a relative "build/" under CWD (aireview / accidental seed).
        if not _CACHE_ROOT:
            return False
        work_build = os.path.join(_CACHE_ROOT, "build")
        if not os.path.isdir(work_build):
            return False

        # 1. contrib distfile cache -> source/download/ (skips fetch)
        dl_cache = os.path.join(_CACHE_ROOT, "download")
        if os.path.isdir(dl_cache):
            dst = os.path.join(self.source_folder, "download")
            shutil.copytree(dl_cache, dst, dirs_exist_ok=True)

        # 2. pre-built contrib/libhb/test/project -> build/
        builddir = os.path.join(self.source_folder, "build")
        for sub in ("contrib", "libhb", "test", "project"):
            src = os.path.join(work_build, sub)
            dst = os.path.join(builddir, sub)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)

        # 3. Uniform future mtime: the HandBrake make system is timestamp-driven
        #    (contrib stamps depend on other contrib install stamps, so stale
        #    mtimes cascade rebuilds). Equal mtimes keep everything "up to date".
        for sub in ("contrib", "libhb", "test", "project"):
            p = os.path.join(builddir, sub)
            if os.path.isdir(p):
                self.run(f'find "{p}" -exec touch -d "2030-01-02 03:04:05" {{}} +')
        return True

    @staticmethod
    def _host_shell():
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            shutil.which("zsh"),
            "/usr/bin/zsh",
            os.environ.get("SHELL"),
            "/bin/sh",
            "/system/bin/sh",
        ):
            if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        return "sh"

    def _set_config_shell(self):
        """Prefer zsh for Autoconf scripts on the OHOS worker."""
        make_shell = self._posix_shell()
        for shell in (
            "/usr/bin/zsh",
            shutil.which("zsh"),
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            "/bin/sh",
            "/system/bin/sh",
        ):
            if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
                os.environ["CONFIG_SHELL"] = shell
                os.environ["SHELL"] = make_shell
                self.output.info(f"CONFIG_SHELL={shell} SHELL={make_shell}")
                return shell
        return None

    @staticmethod
    def _posix_shell():
        for shell in ("/bin/sh", "/system/bin/sh", shutil.which("sh")):
            if shell and os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        return "sh"

    def _configure(self, cc, patch_tool):
        # HandBrake's top-level configure is a POSIX sh launcher that relies on
        # IFS splitting to find python on PATH; zsh does not emulate that here.
        shell = self._posix_shell()
        env_keys = (
            "PATH", "AUTOCONF", "AUTOHEADER", "AUTOMAKE", "ACLOCAL",
            "AUTOM4TE", "AUTORECONF", "AUTOUPDATE", "AUTOSCAN", "IFNAMES",
            "PERL", "M4", "PERL5LIB", "ACLOCAL_PATH", "autom4te_perllibdir",
            "AC_MACRODIR", "trailer_m4", "autom4te_buildauxdir",
            "CONFIG_SHELL", "SHELL", "LD_LIBRARY_PATH",
        )
        env_prefix = " ".join(
            f"{key}={shlex.quote(os.environ[key])}"
            for key in env_keys
            if os.environ.get(key)
        )
        cfg = (
            f'{env_prefix} "{shell}" "{os.path.join(self.source_folder, "configure")}" --force '
            "--prefix=/usr/local "
            "--disable-gtk --disable-numa "
            "--disable-nvenc --disable-nvdec --disable-qsv --disable-vce "
            "--disable-mf --disable-libdovi "
            f'--cc="{cc}" --patch="{patch_tool}"'
        )
        self.run(cfg, cwd=self.source_folder)

    @staticmethod
    def _mirror_candidates(url, include_direct=False):
        """Build download URL list with GitHub mirrors first.

        CI workers cannot reach github.com (CI #12377/#12404). Prefetch
        therefore prefers mirrors only; the original URL is optional and
        intentionally omitted by default so a dead github.com host cannot
        burn wall-clock. make still has the official URL as a trailing
        `+=` fallback after `_rewrite_contrib_fetch_urls()`.
        """
        cands = []
        # Strip a mirror prefix if the caller already passed a mirrored URL
        raw = url
        for prefix in _GH_MIRRORS:
            if raw.startswith(prefix):
                raw = raw[len(prefix):]
                break
        if raw.startswith("https://github.com/"):
            for prefix in _GH_MIRRORS:
                cands.append(prefix + raw)
            cands.append(raw.replace("https://github.com", "https://kkgithub.com"))
            cands.append("https://gitclone.com/" + raw[len("https://"):])
            if include_direct:
                cands.append(raw)
        else:
            cands.append(url)
        seen = set()
        out = []
        for u in cands:
            if u not in seen:
                seen.add(u)
                out.append(u)
        return out

    def _rewrite_contrib_fetch_urls(self):
        """Rewrite contrib module.defs FETCH.url to prefer GitHub mirrors.

        HandBrake's make downloader only uses the URLs listed in module.defs.
        Prefetch alone is not enough: when a distfile is missing, make falls
        back to github.com and burns the CI budget on timeouts (CI #13117/#13144).
        Keep the official URL as a trailing `+=` fallback.
        """
        contrib_dir = os.path.join(self.source_folder, "contrib")
        if not os.path.isdir(contrib_dir):
            return 0
        rewritten = 0
        for mod_def in sorted(glob.glob(os.path.join(contrib_dir, "*", "module.defs"))):
            try:
                text = open(mod_def, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            # Only rewrite primary `=` assignments pointing at github.com
            def _sub(match):
                nonlocal rewritten
                prefix, url = match.group(1), match.group(2)
                if not url.startswith("https://github.com/"):
                    return match.group(0)
                if any(url.startswith(m) or m + "https://github.com/" in url
                       for m in _GH_MIRRORS):
                    return match.group(0)
                mirrors = [m + url for m in _GH_MIRRORS]
                rewritten += 1
                lines = [f"{prefix} = {mirrors[0]}"]
                for m in mirrors[1:]:
                    lines.append(f"{prefix} += {m}")
                lines.append(f"{prefix} += {url}")
                return "\n".join(lines)

            new_text, n = re.subn(
                r'^([A-Z0-9_-]+\.FETCH\.url)\s*=\s*(https://github\.com/\S+)',
                _sub, text, flags=re.M,
            )
            if n and new_text != text:
                open(mod_def, "w", encoding="utf-8").write(new_text)
        if rewritten:
            self.output.info(f"rewrote FETCH.url mirrors in {rewritten} module.defs")
        return rewritten

    def _patch_contrib_autoconf_rules(self):
        """Patch contrib Autoconf rules for quirks on the OHOS worker."""
        if self.settings.os != "OHOS":
            return 0

        config_shell = os.environ.get("CONFIG_SHELL")
        make_shell = self._posix_shell()
        if not config_shell:
            return 0

        injected = 0
        py = shutil.which("python3") or shutil.which("python") or sys.executable or "python3"
        patch_code = (
            'from pathlib import Path; '
            'paths=dict.fromkeys([Path("configure")] + list(Path(".").glob("**/configure"))); '
            '[p.write_bytes(p.read_bytes().replace(b"umask 077", b"umask 022")) '
            'for p in paths if p.is_file()]; '
            'print("patched configure umask entries")'
        )
        patch_config_status = f"{shlex.quote(py)} -c {shlex.quote(patch_code)}"
        # HandBrake's default contrib Autoconf rule passes a long
        # `$(CONTRIB.build/)` prefix with a trailing slash.  On the OHOS
        # worker, /bin/expr corrupts that value while Autoconf strips the
        # trailing slash, and /bin/sh also trips over read-only /tmp paths.
        # Apply the same configure shell/prefix tuple fix to Autoconf-based
        # contribs only; CMake/Meson/custom configure modules keep their own
        # module.defs semantics.
        modules = (
            ("fdk-aac", "FDKAAC"),
            ("freetype", "FREETYPE"),
            ("fribidi", "FRIBIDI"),
            ("jansson", "JANSSON"),
            ("lame", "LAME"),
            ("libass", "LIBASS"),
            ("libgnurx", "LIBGNURX"),
            ("libiconv", "LIBICONV"),
            ("libogg", "LIBOGG"),
            ("libopus", "LIBOPUS"),
            ("libspeex", "LIBSPEEX"),
            ("libtheora", "LIBTHEORA"),
            ("libvorbis", "LIBVORBIS"),
            ("xz", "XZ"),
            ("zimg", "ZIMG"),
        )
        for module, var in modules:
            mod_def = os.path.join(self.source_folder, "contrib", module, "module.defs")
            if not os.path.isfile(mod_def):
                continue
            try:
                text = open(mod_def, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            marker = f"{var}.CONFIGURE.exe = {config_shell} ./configure"
            if marker in text:
                continue
            extra = (
                "\n"
                "# OHOS worker: Autoconf configure needs zsh to avoid /tmp shell\n"
                "# failures.  Also avoid a trailing slash in --prefix: OHOS expr\n"
                "# corrupts long strings in Autoconf's slash-stripping fallback.\n"
                f"{var}.CONFIGURE.env.CONFIG_SHELL = CONFIG_SHELL={config_shell}\n"
                f"{var}.CONFIGURE.env.SHELL = SHELL={make_shell}\n"
                f"{var}.CONFIGURE.env.args += !CONFIG_SHELL !SHELL\n"
                f"{var}.CONFIGURE.exe = {config_shell} ./configure\n"
                f"{var}.CONFIGURE.prefix = $(patsubst %/,%,$(call fn.ABSOLUTE,$(CONTRIB.build/)))\n"
                f"{var}.BUILD.extra += SHELL={make_shell}\n"
                f"{var}.INSTALL.extra += SHELL={make_shell}\n"
            )
            extra += (
                "# OHOS/HMDFS rejects Autoconf config.status temp dirs\n"
                "# created with umask 077; cover nested configure scripts too.\n"
                f"{var}.CONFIGURE.bootstrap += {patch_config_status};\n"
            )
            configure_tuple = "aarch64-unknown-linux-ohos"
            if var in ("LAME", "LIBSPEEX"):
                # LAME 3.100 and Speex 1.2.1 ship older config.sub variants
                # that reject the OHOS tuple, while the Linux aarch64 tuple
                # selects the same compiler/linker code path on this worker.
                configure_tuple = "aarch64-unknown-linux-gnu"
            extra += (
                f"{var}.CONFIGURE.extra += --build={configure_tuple} "
                f"--host={configure_tuple}\n"
            )
            open(mod_def, "a", encoding="utf-8").write(extra)
            injected += 1
        if injected:
            self.output.info(f"patched Autoconf rules for {injected} contrib module.defs")
        return injected

    def _patch_x264_rules(self):
        """Patch x264's bash configure entry point for the OHOS worker."""
        if self.settings.os != "OHOS":
            return 0

        mod_def = os.path.join(self.source_folder, "contrib", "x264", "module.defs")
        if not os.path.isfile(mod_def):
            return 0
        try:
            text = open(mod_def, encoding="utf-8", errors="ignore").read()
        except OSError:
            return 0

        make_shell = self._posix_shell()
        marker = f"X264.CONFIGURE.exe = {make_shell} ./configure"
        disable_asm_marker = "X264.CONFIGURE.extra += --disable-asm"
        if disable_asm_marker in text:
            return 0

        if marker in text:
            extra = (
                "\n"
                "# OHOS CI worker clang rejects x264's AArch64 assembler probe.\n"
                "# Keep the portable C implementation so the static library still builds.\n"
                f"{disable_asm_marker}\n"
            )
        else:
            extra = (
                "\n"
                "# OHOS worker: x264 configure has a /bin/bash shebang, but the\n"
                "# device only provides /bin/sh. Its config.sub also rejects the\n"
                "# OHOS tuple, while a Linux aarch64 tuple selects the same codepath.\n"
                f"X264.CONFIGURE.exe = {make_shell} ./configure\n"
                "X264.CONFIGURE.host = aarch64-unknown-linux-gnu\n"
                "X264.CONFIGURE.prefix = $(patsubst %/,%,$(call fn.ABSOLUTE,$(CONTRIB.build/)))\n"
                f"{disable_asm_marker}\n"
                f"X264.BUILD.extra += SHELL={make_shell}\n"
                f"X264.INSTALL.extra += SHELL={make_shell}\n"
            )

        open(mod_def, "a", encoding="utf-8").write(extra)
        self.output.info("patched x264 configure rules for OHOS")
        return 1

    def _patch_libass_fribidi_flags(self):
        """Ensure libass sees the in-tree FriBidi headers on OHOS."""
        if self.settings.os != "OHOS":
            return 0

        mod_def = os.path.join(self.source_folder, "contrib", "libass", "module.defs")
        if not os.path.isfile(mod_def):
            return 0
        try:
            text = open(mod_def, encoding="utf-8", errors="ignore").read()
        except OSError:
            return 0

        norm = text.replace("\r\n", "\n")
        ohos_fribidi_marker = (
            "ifneq (,$(filter $(HOST.system) $(HOST.systemf),darwin cygwin mingw HarmonyOS))\n"
            "    LIBASS.CONFIGURE.extra += \\\n"
            "        FRIBIDI_LIBS="
        )
        if ohos_fribidi_marker in norm or "OHOS reports HOST.system=linux" in text:
            return 0

        extra = (
            "\n"
            "# OHOS reports HOST.system=linux, so the upstream non-linux block\n"
            "# does not pass FriBidi hints; libass then misses contrib/include.\n"
            "LIBASS.CONFIGURE.extra += \\\n"
            "    FRIBIDI_LIBS=\"-L$(call fn.ABSOLUTE,$(CONTRIB.build/))lib -lfribidi\" \\\n"
            "    FRIBIDI_CFLAGS=\"-I$(call fn.ABSOLUTE,$(CONTRIB.build/))include\"\n"
        )
        open(mod_def, "a", encoding="utf-8").write(extra)
        self.output.info("patched libass FriBidi flags for OHOS")
        return 1

    def _download_one(
        self, basename, urls, sha256, dst, *,
        include_direct=True, file_timeout=300,
        max_candidates=None,
        prefer_non_github=False,
    ):
        """Download one source/contrib distfile and verify its digest."""
        if os.path.isfile(dst):
            if sha256:
                digest = hashlib.sha256(open(dst, "rb").read()).hexdigest()
                if digest == sha256:
                    return "exists"
            else:
                return "exists"

        if self._copy_cached_distfile(basename, sha256, dst):
            return "cached"

        candidates = []
        for url in urls:
            # include_direct=True: official URL as a final fallback for
            # required downloads. Optional contrib prefetch keeps this false
            # so a dead github.com host cannot consume the whole CI budget.
            candidates.extend(self._mirror_candidates(url, include_direct=include_direct))
        seen = set()
        ordered = []
        for u in candidates:
            if u not in seen:
                seen.add(u)
                ordered.append(u)
        def _rank(url):
            if any(url.startswith(prefix) for prefix in _GH_MIRRORS):
                return 0
            if ("github.com/" not in url and "kkgithub.com/" not in url
                    and "gitclone.com/" not in url):
                return 1
            if "kkgithub.com/" in url or "gitclone.com/" in url:
                return 2
            return 3
        if prefer_non_github:
            ordered = [
                url for _, url in sorted(
                    enumerate(ordered), key=lambda item: (_rank(item[1]), item[0])
                )
            ]
        if max_candidates:
            ordered = ordered[:max_candidates]

        tmp = dst + ".tmp"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        last_err = "no download attempted"
        for cand in ordered:
            try:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                download(self, cand, tmp, verify=True, retry=1)
                if sha256:
                    digest = hashlib.sha256(open(tmp, "rb").read()).hexdigest()
                    if digest != sha256:
                        os.unlink(tmp)
                        last_err = f"sha256 mismatch ({digest}) for {cand}"
                        continue
                os.replace(tmp, dst)
                return cand
            except Exception as exc:
                last_err = f"{exc} for {cand}"
                if os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                continue
        raise RuntimeError(f"{basename}: {last_err}")

    def _prefetch_contribs(self):
        """预取 contrib 源码到 download/，并改写 module.defs 镜像 URL。

        CI #13144: 串行 urllib 对大包 120s 超时把 45min 预算耗尽在 prefetch 阶段。
        改进：
          1) 先改写 module.defs，使 make 自身也走镜像（不止依赖 prefetch）
          2) 并行预取（最多 4 路），失败镜像快速跳过
          3) 对实际构建依赖，预取失败即停止；不能让 make 回退到
             HandBrake 的 urllib 下载器（新端口证书/超时失败不可控）。
        """
        self._rewrite_contrib_fetch_urls()

        contrib_dir = os.path.join(self.source_folder, "contrib")
        dl_dir = os.path.join(self.source_folder, "download")
        if not os.path.isdir(contrib_dir):
            return
        os.makedirs(dl_dir, exist_ok=True)

        jobs_by_key = {}
        for mod_def in sorted(glob.glob(os.path.join(contrib_dir, "*", "module.defs"))):
            try:
                text = open(mod_def, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            # Collect all FETCH.url assignments (= and +=)
            urls = re.findall(
                r'^[A-Z0-9_-]+\.FETCH\.url\s*\+?=\s*(\S+)', text, re.M)
            if not urls:
                continue
            sha_m = re.search(
                r'^[A-Z0-9_-]+\.FETCH\.sha256\s*=\s*([0-9a-f]{64})', text, re.M)
            base_m = re.search(
                r'^[A-Z0-9_-]+\.FETCH\.basename\s*=\s*(\S+)', text, re.M)
            # Strip mirror prefixes when deriving basename from URL
            raw = urls[0]
            for p in _GH_MIRRORS:
                if raw.startswith(p):
                    raw = raw[len(p):]
                    break
            basename = base_m.group(1) if base_m else os.path.basename(raw)
            dst = os.path.join(dl_dir, basename)
            sha256 = sha_m.group(1) if sha_m else None
            key = (basename, sha256, dst)
            entry = jobs_by_key.setdefault(key, [])
            for url in urls:
                if url not in entry:
                    entry.append(url)

        jobs = [
            (basename, urls, sha256, dst)
            for (basename, sha256, dst), urls in sorted(jobs_by_key.items())
        ]
        if not jobs:
            return

        optional = {"amf-", "fdk-aac-", "libvpl-", "nv-codec-", "libdovi-"}
        def _is_optional(basename):
            lower = basename.lower()
            return any(lower.startswith(prefix) for prefix in optional)

        fetched = 0
        failed = 0
        required_failed = []
        # Parallelism keeps the contrib set inside CI wall-clock budget without
        # hammering the flaky GitHub mirror tunnels.
        workers = min(4, len(jobs))
        self.output.info(f"prefetch {len(jobs)} contrib distfiles ({workers} workers)")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {
                pool.submit(
                    self._download_one, b, u, s, d,
                    include_direct=False, file_timeout=300, max_candidates=5,
                    prefer_non_github=True,
                ): b
                for b, u, s, d in jobs
            }
            for fut in as_completed(futs):
                basename = futs[fut]
                try:
                    result = fut.result()
                    if result == "exists":
                        self.output.info(f"prefetch {basename}: already present")
                    elif result == "cached":
                        self.output.info(f"prefetch {basename}: reused cache")
                    else:
                        self.output.info(f"prefetch {basename} <- {result}")
                        fetched += 1
                except Exception as exc:
                    failed += 1
                    if _is_optional(basename):
                        self.output.warning(f"prefetch optional {basename} failed: {exc}")
                    else:
                        required_failed.append(f"{basename}: {exc}")
                        self.output.warning(f"prefetch required {basename} failed: {exc}")
        self.output.info(
            f"prefetch done: {fetched} downloaded, "
            f"{len(jobs) - fetched - failed} cached, {failed} failed"
        )
        if required_failed:
            raise RuntimeError(
                "required contrib prefetch failed; refusing to enter make "
                "with HandBrake urllib downloader. First failures: "
                + "; ".join(required_failed[:6])
            )


    def _is_gnu_patch(self, cand):
        """True if cand is an executable GNU patch (never toybox)."""
        if not cand or not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
            return False
        try:
            out = subprocess.check_output(
                [cand, "--version"], stderr=subprocess.STDOUT, text=True, timeout=5)
        except Exception:
            return False
        if "toybox" in out.lower():
            return False
        return "GNU patch" in out or "GNU" in out

    def _resolve_gnu_patch(self, cc):
        """Locate GNU patch without hardcoding personal paths (R33 / aireview).

        CI #12716/#12753: worker PATH only has toybox `/system/bin/patch`, and
        there is no gpatch beside clang. Search PATH + compiler bindir +
        common OHOS user prefix from buildenv ($HOME/usr/local/bin).
        """
        candidates = []
        for name in ("gpatch", "patch"):
            found = shutil.which(name)
            if found:
                candidates.append(found)
        cc_abs = cc if os.path.isabs(cc) else (shutil.which(cc) or "")
        if cc_abs and os.path.isfile(cc_abs):
            bindir = os.path.dirname(os.path.realpath(cc_abs))
            for name in ("gpatch", "patch"):
                candidates.append(os.path.join(bindir, name))
        # Profile buildenv also puts $HOME/usr/local/bin on PATH for self.run,
        # but Python shutil.which may not see it — probe explicitly.
        home = os.environ.get("HOME") or os.path.expanduser("~")
        for name in ("gpatch", "patch"):
            candidates.append(os.path.join(home, "usr", "local", "bin", name))
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if self._is_gnu_patch(cand):
                return cand
        return None

    def _fetch_gnu_patch_tool(self):
        """Fetch OHOS-prebuilt GNU patch from cmd-pkgs (CI #12753).

        Worker has no GNU patch at all (only toybox). cmd-pkgs hosts the
        already-adapted `patch/2.7.6` tarball on gitcode (reachable). This is a
        build-host tool only — HandBrake itself is still built from source (R19).
        Tarball sha256 is pinned so a swapped artifact cannot silently land.
        """
        # basename -> sha256 (cmd-pkgs release assets)
        artifacts = (
            (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                "download/pkgs/patch-2.7.6-ohos-aarch64.tar.gz",
                "600d4d49b35d14aa779e86ce66ece22a63f96c3656661da89df045a7dbcfa282",
            ),
            (
                "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
                "download/pkgs/gpatch-2.8-ohos-aarch64.tar.gz",
                "f01ee6d8734306e23e7a0565f43e861a74cfb9814f5e4772d4855b527431ff94",
            ),
        )
        work = os.path.join(self.build_folder, "_host_gnu_patch")
        os.makedirs(work, exist_ok=True)
        for url, expect_sha in artifacts:
            base = os.path.basename(url)
            tarball = os.path.join(work, base)
            try:
                self.output.info(f"fetch host GNU patch <- {url}")
                self._download_one(base, [url], expect_sha, tarball, file_timeout=120)
            except Exception as exc:
                self.output.warning(f"fetch {base} failed: {exc}")
                continue
            extract_dir = os.path.join(work, base + ".d")
            if os.path.isdir(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir, exist_ok=True)
            try:
                shutil.unpack_archive(tarball, extract_dir)
            except Exception as exc:
                self.output.warning(f"unpack {base} failed: {exc}")
                continue
            # CI #12777: chmod on the extracted path can raise PermissionError
            # on HMDFS even when the binary is already executable. Copy into a
            # dir we own and tolerate chmod failure if X_OK already holds.
            local_bin = os.path.join(work, "bin")
            os.makedirs(local_bin, exist_ok=True)
            for root, _dirs, files in os.walk(extract_dir):
                for name in files:
                    if name not in ("patch", "gpatch"):
                        continue
                    src = os.path.join(root, name)
                    if not self._is_gnu_patch(src):
                        continue
                    dst = os.path.join(local_bin, name)
                    try:
                        shutil.copy2(src, dst)
                    except OSError:
                        dst = src
                    try:
                        os.chmod(dst, 0o755)
                    except OSError as exc:
                        self.output.warning(f"chmod {dst} skipped: {exc}")
                    if self._is_gnu_patch(dst):
                        self.output.info(f"using host GNU patch: {dst}")
                        return dst
        return None

    def _relax_autoconf_tmp_umask(self, script):
        data = open(script, "r", encoding="utf-8").read()
        fixed = data.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
            'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(umask 022 && mkdir "$tmp")',
        )
        if fixed != data:
            open(script, "w", encoding="utf-8").write(fixed)

    def _build_gnu_patch_tool(self, cc):
        """Build a native GNU patch host tool from the official GNU source."""
        version = "2.8"
        sha256 = "f87cee69eec2b4fcbf60a396b030ad6aa3415f192aa5f7ee84cad5e11f7f5ae3"
        urls = [
            f"https://ftp.gnu.org/gnu/patch/patch-{version}.tar.xz",
            f"https://ftpmirror.gnu.org/patch/patch-{version}.tar.xz",
        ]
        work = os.path.join(self.build_folder, "_host_gnu_patch_src")
        src = os.path.join(work, f"patch-{version}")
        prefix = os.path.join(work, "install")
        tarball = os.path.join(work, f"patch-{version}.tar.xz")
        os.makedirs(work, exist_ok=True)
        self._download_one(os.path.basename(tarball), urls, sha256, tarball)
        if os.path.isdir(src):
            shutil.rmtree(src)
        try:
            shutil.unpack_archive(tarball, work)
        except Exception:
            self.run(f'tar -xf "{tarball}" -C "{work}"')
        configure = os.path.join(src, "configure")
        if not os.path.isfile(configure):
            raise RuntimeError(f"GNU patch source did not unpack as expected: {src}")
        # OHOS HMDFS rejects writes inside mktemp dirs created under umask 077.
        self._relax_autoconf_tmp_umask(configure)

        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        make_shell = self._posix_shell()
        make = shutil.which("make") or "make"
        cc_dir = os.path.dirname(os.path.realpath(cc)) if os.path.isabs(cc) else ""
        ar = shutil.which("llvm-ar") or (os.path.join(cc_dir, "llvm-ar") if cc_dir else "")
        ranlib = shutil.which("llvm-ranlib") or (os.path.join(cc_dir, "llvm-ranlib") if cc_dir else "")
        nm = shutil.which("llvm-nm") or (os.path.join(cc_dir, "llvm-nm") if cc_dir else "")
        tmpdir = os.path.join(work, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        common_env = (
            f'CC="{cc}" '
            f'AR="{ar}" RANLIB="{ranlib}" NM="{nm}" '
            f'TMPDIR="{tmpdir}" TMPPREFIX="{os.path.join(tmpdir, "patch")}"'
        )
        configure_env = f'{common_env} CONFIG_SHELL="{shell}" SHELL="{make_shell}"'
        make_env = f'{common_env} CONFIG_SHELL="{shell}" SHELL="{make_shell}"'
        self.output.info("building host GNU patch from official GNU patch 2.8 source")
        self.run(
            f'umask 022 && {configure_env} "{shell}" "{configure}" '
            f'--prefix="{prefix}" --build=aarch64-unknown-linux-ohos '
            f'--host=aarch64-unknown-linux-ohos --disable-nls',
            cwd=src,
        )
        self.run(f'umask 022 && {make_env} "{make}" SHELL="{make_shell}" -j1', cwd=src)
        self.run(f'umask 022 && {make_env} "{make}" SHELL="{make_shell}" install', cwd=src)

        for name in ("gpatch", "patch"):
            cand = os.path.join(prefix, "bin", name)
            if self._is_gnu_patch(cand):
                self.output.info(f"using freshly built host GNU patch: {cand}")
                return cand
        raise RuntimeError("fresh GNU patch build completed but no runnable patch was installed")

    def _ensure_gnu_patch(self, cc):
        """Resolve or fetch GNU patch; never fall back to toybox."""
        found = self._resolve_gnu_patch(cc)
        if found:
            return found
        fetched = self._fetch_gnu_patch_tool()
        if fetched:
            # Keep HandBrake configure's own `find: gpatch` happy.
            bindir = os.path.dirname(fetched)
            os.environ["PATH"] = bindir + ":" + os.environ.get("PATH", "")
            return fetched
        built = self._build_gnu_patch_tool(cc)
        if built:
            bindir = os.path.dirname(built)
            os.environ["PATH"] = bindir + ":" + os.environ.get("PATH", "")
            return built
        raise RuntimeError(
            "GNU patch not available on this worker (toybox patch is not usable) "
            "and fetching patch/2.7.6 from cmd-pkgs failed"
        )

    def _pkg_config_ok(self, cand):
        if not cand or not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
            return False
        try:
            out = subprocess.check_output(
                [cand, "--version"], stderr=subprocess.STDOUT, text=True, timeout=5)
        except Exception:
            return False
        m = re.search(r"(\d+)(?:\.(\d+))?", out)
        if not m:
            return False
        return (int(m.group(1)), int(m.group(2) or "0")) >= (0, 27)

    def _install_pkg_config_wrappers(self, target):
        bindir = os.path.join(self.build_folder, "_host_pkg_config", "bin")
        os.makedirs(bindir, exist_ok=True)
        for name in ("pkg-config", "pkgconf"):
            wrap = os.path.join(bindir, name)
            with open(wrap, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(f"#!/bin/sh\nexec {shlex.quote(target)} \"$@\"\n")
            try:
                os.chmod(wrap, 0o755)
            except OSError as exc:
                self.output.warning(f"chmod {wrap} skipped: {exc}")
        os.environ["PKG_CONFIG"] = os.path.join(bindir, "pkg-config")
        os.environ["PATH"] = bindir + ":" + os.environ.get("PATH", "")
        self.output.info(f"pkg-config wrapper -> {target}")
        return os.environ["PKG_CONFIG"]

    def _build_pkgconf_tool(self, cc):
        """Build a native pkg-config-compatible host tool from pkgconf source."""
        version = "2.5.1"
        sha256 = "cd05c9589b9f86ecf044c10a2269822bc9eb001eced2582cfffd658b0a50c243"
        urls = [
            f"https://distfiles.ariadne.space/pkgconf/pkgconf-{version}.tar.xz",
            f"https://distfiles.dereferenced.org/pkgconf/pkgconf-{version}.tar.xz",
        ]
        work = os.path.join(self.build_folder, "_host_pkgconf_src")
        src = os.path.join(work, f"pkgconf-{version}")
        prefix = os.path.join(work, "install")
        tarball = os.path.join(work, f"pkgconf-{version}.tar.xz")
        os.makedirs(work, exist_ok=True)
        self._download_one(os.path.basename(tarball), urls, sha256, tarball)
        if os.path.isdir(src):
            shutil.rmtree(src)
        try:
            shutil.unpack_archive(tarball, work)
        except Exception:
            self.run(f'tar -xf "{tarball}" -C "{work}"')
        configure = os.path.join(src, "configure")
        if not os.path.isfile(configure):
            raise RuntimeError(f"pkgconf source did not unpack as expected: {src}")
        self._relax_autoconf_tmp_umask(configure)

        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        make_shell = self._posix_shell()
        make = shutil.which("make") or "make"
        cc_dir = os.path.dirname(os.path.realpath(cc)) if os.path.isabs(cc) else ""
        ar = shutil.which("llvm-ar") or shutil.which("ar") or (os.path.join(cc_dir, "llvm-ar") if cc_dir else "")
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib") or (os.path.join(cc_dir, "llvm-ranlib") if cc_dir else "")
        nm = shutil.which("llvm-nm") or shutil.which("nm") or (os.path.join(cc_dir, "llvm-nm") if cc_dir else "")
        ld = shutil.which("ld") or shutil.which("ld.lld") or (os.path.join(cc_dir, "ld.lld") if cc_dir else "")
        tmpdir = os.path.join(work, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        common_env = (
            f'CC="{cc}" LD="{ld}" AR="{ar}" RANLIB="{ranlib}" NM="{nm}" '
            f'TMPDIR="{tmpdir}" TMPPREFIX="{os.path.join(tmpdir, "pkgconf")}"'
        )
        configure_env = f'{common_env} CONFIG_SHELL="{shell}" SHELL="{make_shell}"'
        make_env = f'{common_env} CONFIG_SHELL="{shell}" SHELL="{make_shell}"'
        self.output.info("building host pkgconf 2.5.1 from source")
        self.run(
            f'umask 022 && {configure_env} "{shell}" "{configure}" '
            f'--prefix="{prefix}" --build=aarch64-unknown-linux-ohos '
            f'--host=aarch64-unknown-linux-ohos --disable-shared --enable-static',
            cwd=src,
        )
        self.run(f'umask 022 && {make_env} "{make}" SHELL="{make_shell}" -j1', cwd=src)
        self.run(f'umask 022 && {make_env} "{make}" SHELL="{make_shell}" install', cwd=src)

        for name in ("pkg-config", "pkgconf"):
            cand = os.path.join(prefix, "bin", name)
            if self._pkg_config_ok(cand):
                return cand
        raise RuntimeError("pkgconf build completed but no runnable pkg-config was installed")

    def _ensure_pkg_config(self, cc):
        for name in ("pkg-config", "pkgconf"):
            found = shutil.which(name)
            if self._pkg_config_ok(found):
                return self._install_pkg_config_wrappers(found)
        built = self._build_pkgconf_tool(cc)
        return self._install_pkg_config_wrappers(built)

    def _find_perl(self):
        candidates = []
        dep = self.dependencies.build.get("perl")
        if dep:
            for bindir in getattr(dep.cpp_info, "bindirs", []) or ["bin"]:
                path = bindir if os.path.isabs(bindir) else os.path.join(dep.package_folder, bindir)
                candidates.extend((
                    os.path.join(path, "perl"),
                    os.path.join(path, f"perl{dep.ref.version}"),
                ))
        candidates.extend((
            shutil.which("perl"),
            "/data/service/hnp/bin/perl",
            "/usr/bin/perl",
            "/bin/perl",
        ))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _perl5lib_dirs(self):
        dep = self.dependencies.build.get("perl")
        if not dep:
            return []
        root = os.path.join(dep.package_folder, "lib", "perl5")
        version = str(dep.ref.version)
        candidates = [
            os.path.join(root, version),
            os.path.join(root, version, "aarch64-linux-thread-multi"),
            os.path.join(root, "site_perl", version),
            os.path.join(root, "site_perl", version, "aarch64-linux-thread-multi"),
        ]
        return [p for p in candidates if os.path.isdir(p)]

    def _is_runnable_tool(self, path, env=None):
        """True if path can execute `--version` (direct or via perl)."""
        if not path or not os.path.isfile(path):
            return False
        run_env = os.environ if env is None else env
        try:
            r = subprocess.run(
                [path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
                env=run_env,
            )
            if r.returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
        # Conan automake is a perl script; OHOS often lacks the shebang interpreter
        # path baked into the script (ENOENT on exec). Retry via explicit perl.
        perl = self._find_perl()
        if not perl:
            return False
        try:
            r = subprocess.run(
                [perl, path, "--version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
                env=run_env,
            )
            return r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _quarantine_broken_home_autotools(self):
        """CI #14768: profile PATH puts $HOME/usr/local/bin ahead of Conan tools.

        HandBrake configure.py finds `automake` there, then version-probes it and
        dies with FileNotFoundError (broken shebang / missing perl). Move such
        stubs aside so PATH falls through to our wrappers / tool_requires.
        """
        home = os.environ.get("HOME") or os.path.expanduser("~")
        bindir = os.path.join(home, "usr", "local", "bin")
        if not os.path.isdir(bindir):
            return
        for name in ("automake", "aclocal", "automake-1.18", "aclocal-1.18"):
            path = os.path.join(bindir, name)
            if not os.path.lexists(path):
                continue
            if self._is_runnable_tool(path):
                continue
            broken = path + ".broken-ohos-ci"
            try:
                if os.path.lexists(broken):
                    os.remove(broken)
                os.rename(path, broken)
                self.output.warning(
                    f"quarantined non-runnable {name}: {path} -> {broken}"
                )
            except OSError as exc:
                self.output.warning(f"cannot quarantine {path}: {exc}")

    def _install_autotools_wrappers(self):
        """Private sh wrappers: set PERL5LIB and exec automake via perl.

        CI #15352: raw Conan automake perl script is not directly exec-able on
        OHOS (bad shebang) and was incorrectly dropped from PATH. Wrappers live
        under the package build folder (archives only — no ci/ changes).
        """
        am = self.dependencies.build.get("automake")
        if not am:
            raise RuntimeError("tool_requires automake/1.18 is required")
        ac = self.dependencies.build.get("autoconf")
        if not ac:
            raise RuntimeError("tool_requires autoconf/2.72 is required")
        am_bin = os.path.join(am.package_folder, "bin")
        ac_bin = os.path.join(ac.package_folder, "bin")
        am_exe = os.path.join(am_bin, "automake")
        acl_exe = os.path.join(am_bin, "aclocal")
        am_real = os.path.join(am_bin, ".automake-real")
        acl_real = os.path.join(am_bin, ".aclocal-real")
        if not os.path.isfile(am_exe):
            raise RuntimeError(f"automake missing in package: {am_exe}")

        perl = self._find_perl()
        if not perl:
            raise RuntimeError(
                "perl not found (needed to run Conan automake on OHOS); "
                "expected under /data/service/hnp/bin/perl"
            )

        pl = os.path.join(am.package_folder, "share", "automake-1.18")
        perl5lib = ":".join(self._perl5lib_dirs() + [pl])
        ac_lib = os.path.join(ac.package_folder, "share", "autoconf")
        if os.path.isdir(ac_lib):
            perl5lib = ":".join([perl5lib, ac_lib])
        m4_dep = self.dependencies.build.get("m4")
        m4_exe = (
            os.path.join(m4_dep.package_folder, "bin", "m4")
            if m4_dep else (shutil.which("m4") or "m4")
        )
        lt = self.dependencies.build.get("libtool")
        lt_ac_dirs = []
        if lt:
            lt_ac_dirs = [
                os.path.join(lt.package_folder, "share", "aclocal"),
                os.path.join(lt.package_folder, "share", "libtool", "m4"),
            ]
        ac_dirs = [
            d for d in (
                os.path.join(am.package_folder, "share", "aclocal-1.18"),
                os.path.join(am.package_folder, "share", "aclocal"),
                *lt_ac_dirs,
            ) if os.path.isdir(d)
        ]
        ac_join = ":".join(ac_dirs)

        wrap_dir = os.path.join(self.build_folder, "_host_autotools", "bin")
        os.makedirs(wrap_dir, exist_ok=True)
        common_exports = (
            f'export PATH="{wrap_dir}${{PATH:+:$PATH}}"\n'
            f'export PERL="{perl}"\n'
            f'export M4="{m4_exe}"\n'
            f'export ACLOCAL="{os.path.join(wrap_dir, "aclocal")}"\n'
            f'export AUTOMAKE="{os.path.join(wrap_dir, "automake")}"\n'
            f'export AUTOCONF="{os.path.join(wrap_dir, "autoconf")}"\n'
            f'export AUTOHEADER="{os.path.join(wrap_dir, "autoheader")}"\n'
            f'export AUTOM4TE="{os.path.join(wrap_dir, "autom4te")}"\n'
            f'export AUTORECONF="{os.path.join(wrap_dir, "autoreconf")}"\n'
            f'export AUTOUPDATE="{os.path.join(wrap_dir, "autoupdate")}"\n'
            f'export AUTOSCAN="{os.path.join(wrap_dir, "autoscan")}"\n'
            f'export IFNAMES="{os.path.join(wrap_dir, "ifnames")}"\n'
        )
        if os.path.isdir(ac_lib):
            common_exports += (
                f'export autom4te_perllibdir="{ac_lib}"\n'
                f'export AC_MACRODIR="{ac_lib}"\n'
                f'export trailer_m4="{os.path.join(ac_lib, "autoconf", "trailer.m4")}"\n'
                f'export autom4te_buildauxdir="{os.path.join(ac_lib, "build-aux")}"\n'
            )
        perl_wrap = os.path.join(wrap_dir, "perl")
        with open(perl_wrap, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "#!/bin/sh\n"
                f'export PERL5LIB="{perl5lib}${{PERL5LIB:+:$PERL5LIB}}"\n'
                f'exec "{perl}" "$@"\n'
            )
        try:
            os.chmod(perl_wrap, 0o755)
        except OSError as exc:
            self.output.warning(f"chmod {perl_wrap} skipped: {exc}")
        self.output.info(f"perl wrapper: {perl_wrap} -> {perl}")
        for name, real, args in (
            ("automake", am_real if os.path.isfile(am_real) else am_exe, [f"--libdir={pl}"]),
            ("aclocal", acl_real if os.path.isfile(acl_real) else acl_exe, [
                f"--automake-acdir={os.path.join(am.package_folder, 'share', 'aclocal-1.18')}",
                f"--system-acdir={os.path.join(am.package_folder, 'share', 'aclocal')}",
            ]),
        ):
            if not os.path.isfile(real):
                continue
            wrap = os.path.join(wrap_dir, name)
            # HandBrake configure finds `automake` on PATH and runs it directly.
            arg_line = " ".join(f'"{a}"' for a in args)
            script = (
                "#!/bin/sh\n"
                f"{common_exports}"
                f'export PERL5LIB="{perl5lib}${{PERL5LIB:+:$PERL5LIB}}"\n'
                f'export ACLOCAL_PATH="{ac_join}${{ACLOCAL_PATH:+:$ACLOCAL_PATH}}"\n'
                f'exec "{perl}" "{real}" {arg_line} "$@"\n'
            )
            with open(wrap, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(script)
            try:
                os.chmod(wrap, 0o755)
            except OSError as exc:
                self.output.warning(f"chmod {wrap} skipped: {exc}")
            self.output.info(f"autotools wrapper: {wrap} -> {real}")
        for name in ("autoconf", "autoheader", "autoreconf", "autom4te", "autoupdate", "autoscan", "ifnames"):
            exe = os.path.join(ac_bin, name)
            real = os.path.join(ac_bin, f".{name}-real")
            real = real if os.path.isfile(real) else exe
            if not os.path.isfile(real):
                continue
            wrap = os.path.join(wrap_dir, name)
            extra_args = (
                f' --prepend-include "{ac_lib}"'
                if name == "autom4te" and os.path.isdir(ac_lib) else ""
            )
            script = (
                "#!/bin/sh\n"
                f"{common_exports}"
                f'export PERL5LIB="{perl5lib}${{PERL5LIB:+:$PERL5LIB}}"\n'
                f'exec "{perl}" "{real}"{extra_args} "$@"\n'
            )
            with open(wrap, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(script)
            try:
                os.chmod(wrap, 0o755)
            except OSError as exc:
                self.output.warning(f"chmod {wrap} skipped: {exc}")
            self.output.info(f"autotools wrapper: {wrap} -> {real}")
        return wrap_dir, am_exe, pl, ac_dirs

    def _prepare_autotools_env(self, cc):
        """Inject runnable automake/libtool for HandBrake configure (recipe-only).

        CI #15489: Conan ``Environment.vars().apply()`` is a context manager; calling
        it without ``with`` does not persist PATH into ``os.environ``, so
        ``shutil.which("automake")`` stayed None even after wrappers were written.
        Mutate ``os.environ`` directly (same pattern as GNU patch PATH injection).
        """
        self._quarantine_broken_home_autotools()

        wrap_dir, am_exe, pl, ac_dirs = self._install_autotools_wrappers()
        wrap_am = os.path.join(wrap_dir, "automake")
        wrap_acl = os.path.join(wrap_dir, "aclocal")

        os.environ["AUTOMAKE"] = wrap_am
        os.environ["ACLOCAL"] = wrap_acl
        os.environ["AUTOCONF"] = os.path.join(wrap_dir, "autoconf")
        os.environ["AUTOHEADER"] = os.path.join(wrap_dir, "autoheader")
        os.environ["AUTOM4TE"] = os.path.join(wrap_dir, "autom4te")
        os.environ["AUTORECONF"] = os.path.join(wrap_dir, "autoreconf")
        os.environ["AUTOUPDATE"] = os.path.join(wrap_dir, "autoupdate")
        os.environ["AUTOSCAN"] = os.path.join(wrap_dir, "autoscan")
        os.environ["IFNAMES"] = os.path.join(wrap_dir, "ifnames")
        os.environ["PERL"] = self._find_perl() or os.path.join(wrap_dir, "perl")
        m4_dep = self.dependencies.build.get("m4")
        if m4_dep:
            os.environ["M4"] = os.path.join(m4_dep.package_folder, "bin", "m4")
        ac = self.dependencies.build.get("autoconf")
        if ac:
            ac_lib = os.path.join(ac.package_folder, "share", "autoconf")
            if os.path.isdir(ac_lib):
                os.environ["autom4te_perllibdir"] = ac_lib
                os.environ["AC_MACRODIR"] = ac_lib
                os.environ["trailer_m4"] = os.path.join(
                    ac_lib, "autoconf", "trailer.m4"
                )
                os.environ["autom4te_buildauxdir"] = os.path.join(
                    ac_lib, "build-aux"
                )
        if os.path.isdir(pl):
            prev = os.environ.get("PERL5LIB", "")
            os.environ["PERL5LIB"] = pl + ((":" + prev) if prev else "")
        if ac_dirs:
            prev = os.environ.get("ACLOCAL_PATH", "")
            joined = ":".join(ac_dirs)
            os.environ["ACLOCAL_PATH"] = joined + ((":" + prev) if prev else "")

        cc_abs = cc if os.path.isabs(cc) else (shutil.which(cc) or "")
        cc_dir = ""
        if cc_abs and os.path.isfile(cc_abs):
            cc_dir = os.path.dirname(os.path.realpath(cc_abs))
        alias_dir = self._install_toolchain_aliases(cc_dir)
        archive_dir = self._install_archive_tool_wrappers()

        tool_bins = [alias_dir, archive_dir, wrap_dir]
        if cc_dir:
            tool_bins.append(cc_dir)
        lt = self.dependencies.build.get("libtool")
        if lt:
            tool_bins.append(os.path.join(lt.package_folder, "bin"))
        am = self.dependencies.build.get("automake")
        if am:
            tool_bins.append(os.path.join(am.package_folder, "bin"))
        ac = self.dependencies.build.get("autoconf")
        if ac:
            tool_bins.append(os.path.join(ac.package_folder, "bin"))
        m4 = self.dependencies.build.get("m4")
        if m4:
            tool_bins.append(os.path.join(m4.package_folder, "bin"))

        # Drop broken $HOME/usr/local/bin automake shadow (E049/CI #14768), keep
        # the rest of PATH, then prepend our wrapper/tool bins.
        home = os.environ.get("HOME") or os.path.expanduser("~")
        home_bin = os.path.normpath(os.path.join(home, "usr", "local", "bin"))
        cleaned = []
        for part in os.environ.get("PATH", "").split(":"):
            if not part:
                continue
            if os.path.normpath(part) == home_bin:
                candidate = os.path.join(part, "automake")
                if os.path.lexists(candidate) and not self._is_runnable_tool(candidate):
                    self.output.warning(
                        f"dropping PATH entry with broken automake: {part}"
                    )
                    continue
            cleaned.append(part)

        prefix = [b for b in tool_bins if os.path.isdir(b)]
        # de-dupe while preserving order
        seen = set()
        ordered = []
        for b in prefix + cleaned:
            nb = os.path.normpath(b)
            if nb in seen:
                continue
            seen.add(nb)
            ordered.append(b)
        os.environ["PATH"] = ":".join(ordered)

        # Prefer the wrapper path itself — do not trust which() alone.
        which_am = wrap_am if os.path.isfile(wrap_am) else shutil.which("automake")
        if not which_am or not self._is_runnable_tool(which_am):
            raise RuntimeError(
                "No runnable automake after wrapper injection "
                f"(wrap={wrap_am!r}, which={shutil.which('automake')!r}, "
                f"conan={am_exe!r}, PATH0={ordered[:3]!r}); "
                "HandBrake configure will abort"
            )
        self.output.info(f"PATH automake -> {which_am}")

    def _install_archive_tool_wrappers(self):
        """Provide a tar implementation that does not depend on toybox filters."""
        alias_dir = os.path.join(self.build_folder, "_host_archive_tools", "bin")
        os.makedirs(alias_dir, exist_ok=True)
        py = sys.executable or shutil.which("python3") or "python3"
        tar_py = os.path.join(alias_dir, "tar.py")
        with open(tar_py, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(r'''#!/usr/bin/env python3
import os
import sys
import tarfile


def _usage():
    sys.stderr.write("usage: tar xfC ARCHIVE DIR\n")
    return 2


def _safe_extract(tf, dst):
    root = os.path.realpath(dst)
    for member in tf.getmembers():
        target = os.path.realpath(os.path.join(dst, member.name))
        if target != root and not target.startswith(root + os.sep):
            raise RuntimeError("refusing to extract outside destination: " + member.name)
    tf.extractall(dst)


def main(argv):
    if len(argv) == 2 and argv[1] in ("--version", "-V"):
        print("python-tar-wrapper")
        return 0
    if len(argv) == 2 and argv[1] in ("--help", "-h"):
        return _usage()

    archive = None
    dest = None
    mode = None
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            i += 1
            continue
        if arg.startswith("-"):
            opts = arg[1:]
        elif all(ch in "xfCzjJv" for ch in arg):
            opts = arg
        else:
            return _usage()
        if "x" in opts:
            mode = "x"
        if "f" in opts:
            i += 1
            if i >= len(argv):
                return _usage()
            archive = argv[i]
        if "C" in opts:
            i += 1
            if i >= len(argv):
                return _usage()
            dest = argv[i]
        i += 1

    if mode != "x" or not archive or not dest:
        return _usage()
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(archive, "r:*") as tf:
        _safe_extract(tf, dest)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except Exception as exc:
        sys.stderr.write("tar wrapper: %s\n" % exc)
        raise SystemExit(2)
''')
        try:
            os.chmod(tar_py, 0o755)
        except OSError as exc:
            self.output.warning(f"chmod {tar_py} skipped: {exc}")
        for name in ("tar", "gtar"):
            wrap = os.path.join(alias_dir, name)
            with open(wrap, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(f"#!/bin/sh\nexec {shlex.quote(py)} {shlex.quote(tar_py)} \"$@\"\n")
            try:
                os.chmod(wrap, 0o755)
            except OSError as exc:
                self.output.warning(f"chmod {wrap} skipped: {exc}")
            self.output.info(f"archive alias: {name} -> {tar_py}")
        return alias_dir

    def _prepend_sdk_llvm_lib(self, cc_dir):
        """Keep OHOS SDK lld's private libxml2 ahead of worker libraries."""
        candidates = []
        if cc_dir:
            candidates.append(os.path.join(os.path.dirname(cc_dir), "lib"))
        candidates.extend(
            reversed(sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")))
        )
        for lib_dir in candidates:
            if not (lib_dir and os.path.isdir(lib_dir)):
                continue
            ordered = []
            seen = set()
            for part in [lib_dir] + os.environ.get("LD_LIBRARY_PATH", "").split(":"):
                if not part:
                    continue
                norm = os.path.normpath(part)
                if norm in seen:
                    continue
                seen.add(norm)
                ordered.append(part)
            os.environ["LD_LIBRARY_PATH"] = ":".join(ordered)
            self.output.info(f"LD_LIBRARY_PATH SDK llvm lib -> {lib_dir}")
            return lib_dir
        return ""

    def _install_compiler_wrappers(self, cc, cxx):
        """Wrap OHOS clang so compile-only probes ignore injected linker args."""
        cc_abs = cc if os.path.isabs(cc) else (shutil.which(cc) or "")
        if not (cc_abs and os.path.isfile(cc_abs)):
            return cc

        cc_dir = os.path.dirname(os.path.realpath(cc_abs))
        self._prepend_sdk_llvm_lib(cc_dir)
        cxx_abs = cxx if cxx and os.path.isabs(cxx) else (shutil.which(cxx) if cxx else "")
        if not cxx_abs:
            cand = os.path.join(cc_dir, "clang++")
            if os.path.isfile(cand):
                cxx_abs = cand

        if "clang" not in os.path.basename(cc_abs):
            os.environ["CC"] = cc_abs
            if cxx_abs and os.path.isfile(cxx_abs):
                os.environ["CXX"] = cxx_abs
            if cc_dir not in os.environ.get("PATH", "").split(":"):
                os.environ["PATH"] = cc_dir + os.pathsep + os.environ.get("PATH", "")
            self.output.info(
                f"CC={os.environ['CC']} CXX={os.environ.get('CXX','')} PATH+={cc_dir}"
            )
            return cc_abs

        wrap_dir = os.path.join(self.build_folder, "_host_compilers", "bin")
        os.makedirs(wrap_dir, exist_ok=True)
        written = {}

        def _write(name, target):
            if not target or not os.path.isfile(target):
                return ""
            if name in written:
                return written[name]
            wrap = os.path.join(wrap_dir, name)
            with open(wrap, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(
                    "#!/bin/sh\n"
                    f"exec {shlex.quote(target)} -Qunused-arguments \"$@\"\n"
                )
            try:
                os.chmod(wrap, 0o755)
            except OSError as exc:
                self.output.warning(f"chmod {wrap} skipped: {exc}")
            written[name] = wrap
            self.output.info(f"compiler wrapper: {name} -> {target} -Qunused-arguments")
            return wrap

        cc_wrap = _write("clang", cc_abs)
        _write(os.path.basename(cc_abs), cc_abs)
        cxx_wrap = ""
        if cxx_abs and os.path.isfile(cxx_abs):
            cxx_wrap = _write("clang++", cxx_abs)
            _write(os.path.basename(cxx_abs), cxx_abs)

        old_path = os.environ.get("PATH", "").split(":")
        ordered = []
        seen = set()
        for part in [wrap_dir, cc_dir] + old_path:
            if not part:
                continue
            norm = os.path.normpath(part)
            if norm in seen:
                continue
            seen.add(norm)
            ordered.append(part)
        os.environ["PATH"] = ":".join(ordered)
        os.environ["CC"] = cc_wrap
        if cxx_wrap:
            os.environ["CXX"] = cxx_wrap
        self.output.info(
            f"CC={os.environ['CC']} CXX={os.environ.get('CXX','')} PATH+={wrap_dir}:{cc_dir}"
        )
        return cc_wrap

    def _install_toolchain_aliases(self, cc_dir):
        """Expose LLVM binutils under the bare names HandBrake configure probes."""
        alias_dir = os.path.join(self.build_folder, "_host_toolchain", "bin")
        os.makedirs(alias_dir, exist_ok=True)

        env_tools = {}
        for bare, llvm in (
            ("ar", "llvm-ar"),
            ("ranlib", "llvm-ranlib"),
            ("nm", "llvm-nm"),
            ("strip", "llvm-strip"),
            ("ld", "ld.lld"),
        ):
            target = shutil.which(llvm)
            if not target and cc_dir:
                cand = os.path.join(cc_dir, llvm)
                if os.path.isfile(cand):
                    target = cand
            if not target:
                self.output.warning(f"{llvm} not found; {bare} alias not installed")
                continue
            wrap = os.path.join(alias_dir, bare)
            with open(wrap, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(f"#!/bin/sh\nexec {shlex.quote(target)} \"$@\"\n")
            try:
                os.chmod(wrap, 0o755)
            except OSError as exc:
                self.output.warning(f"chmod {wrap} skipped: {exc}")
            env_tools[bare.upper()] = wrap
            self.output.info(f"toolchain alias: {bare} -> {target}")
        for name, wrap in env_tools.items():
            if name == "LD" and cc_dir:
                cc = os.path.join(cc_dir, "clang")
                if os.path.isfile(cc):
                    # libvpx uses $LD as the final linker driver and passes
                    # compiler-driver flags such as -fstack-protector-strong.
                    # Keep the bare ld wrapper on PATH for configure probes,
                    # but export LD=clang so contrib check_ld can link.
                    os.environ[name] = cc
                    self.output.info(f"toolchain env: LD -> {cc}")
                    continue
            os.environ[name] = wrap
        return alias_dir

    def build(self):
        # R33: compilers from Conan conf (profile [conf]), never bare shell vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        raw_cc = compilers.get("c", "clang")
        raw_cxx = compilers.get("cpp") or compilers.get("cxx")

        # CI #16631: /bin/sh on the true-device worker cannot reliably run
        # Autoconf scripts that create temp files; zsh passed the libiconv
        # prefix probe and remains available on both old and new port images.
        self._set_config_shell()

        # CI #16632: the OHOS clang launcher injects -Wl,--code-sign. Meson
        # compile-only probes use -Werror=unused-command-line-argument, so
        # dav1d falsely concludes that stdatomic/GCC atomics are unavailable.
        cc = self._install_compiler_wrappers(raw_cc, raw_cxx)

        # CI #14768: prefer Conan automake/libtool; quarantine broken
        # $HOME/usr/local/bin/automake that shadows tool_requires.
        self._prepare_autotools_env(cc)

        # CI #12753: worker has no GNU patch — resolve or fetch from cmd-pkgs.
        patch_tool = self._ensure_gnu_patch(cc)
        self._ensure_pkg_config(cc)

        seeded = self._seed_local_cache()

        # CI worker 无法直连 github.com 下载 33 个 contrib distfile
        # (CI #13117/#13144). 改写镜像 URL + 并行预取到 download/。
        self._prefetch_contribs()

        # CI #16631: HandBrake emits contrib configure commands into
        # build/GNUmakefile, so selected Autoconf fixes must be injected into
        # module.defs before the top-level configure generates those rules.
        self._patch_contrib_autoconf_rules()
        self._patch_x264_rules()
        self._patch_libass_fribidi_flags()

        self._configure(cc, patch_tool)

        # HMDFS ($HOME) cannot mkfifo — GNU make jobserver then degrades and
        # parallel -j is ineffective (CI log: "jobserver mkfifo: Operation not
        # permitted"). Point TMPDIR at a local FS that supports FIFOs so -j2
        # actually parallelises the 33-contrib build inside the 10800s budget.
        for tmp_cand in ("/data/local/tmp", "/tmp"):
            if os.path.isdir(tmp_cand) and os.access(tmp_cand, os.W_OK):
                os.environ["TMPDIR"] = tmp_cand
                self.output.info(f"TMPDIR={tmp_cand} (jobserver FIFO-capable)")
                break

        make_bin = shutil.which("make") or "make"
        build_dir = os.path.join(self.source_folder, "build")
        # GNU make >= 4.4: --jobserver-style=pipe avoids FIFO on HMDFS.
        make_jobs = '-j2'
        try:
            help_txt = subprocess.check_output(
                [make_bin, "--help"], text=True, stderr=subprocess.STDOUT, timeout=5)
            if "--jobserver-style" in help_txt:
                make_jobs = '--jobserver-style=pipe -j2'
                self.output.info("using make --jobserver-style=pipe (no FIFO)")
        except Exception:
            pass

        # Conan buildenv re-applies the profile environment for self.run(), so
        # keep the private Autotools wrappers visible to contrib make rules.
        make_env_keys = (
            "PATH", "AUTOCONF", "AUTOHEADER", "AUTOMAKE", "ACLOCAL",
            "AUTOM4TE", "AUTORECONF", "AUTOUPDATE", "AUTOSCAN", "IFNAMES",
            "PERL", "M4", "PERL5LIB", "ACLOCAL_PATH", "autom4te_perllibdir",
            "AC_MACRODIR", "trailer_m4", "autom4te_buildauxdir",
            "CONFIG_SHELL", "SHELL", "TMPDIR", "LD_LIBRARY_PATH",
        )
        make_env = " ".join(
            f"{key}={shlex.quote(os.environ[key])}"
            for key in make_env_keys
            if os.environ.get(key)
        )
        self.run(f'cd "{build_dir}" && {make_env} "{make_bin}" {make_jobs}')

        cli = os.path.join(self.source_folder, "build", "HandBrakeCLI")
        if not os.path.isfile(cli):
            raise RuntimeError(f"HandBrakeCLI was not produced: {cli}")
        self.output.info(f"HandBrakeCLI built ({'seeded cache' if seeded else 'clean source'})")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "HandBrakeCLI",
             src=os.path.join(self.source_folder, "build"),
             dst=bin_dir, keep_path=False)

        # OHOS requires ELF code signature: unsigned binaries get
        # "Operation not permitted" and cannot execute. Self-sign here.
        # ELF self-sign is OHOS-only (aireview P2): Linux has no binary-sign-tool.
        # Recipe still supports both platforms (R32); signing runs only on OHOS.
        if self.settings.os == "OHOS":
            cli = os.path.join(bin_dir, "HandBrakeCLI")
            sign_tool = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(cli):
                # remove the linker-added self-sign section, then re-sign
                objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
                self.run(f'"{objcopy}" --remove-section .codesign "{cli}"')
                signed = cli + ".signed"
                self.run(
                    f'"{sign_tool}" sign -inFile "{cli}" -outFile "{signed}" '
                    '-selfSign 1 -signAlg SHA256withECDSA',
                    quiet=True,
                )
                if not os.path.isfile(signed):
                    # R19: 静默失败会发布不可执行二进制 → 必须显式失败
                    raise RuntimeError(
                        f"HandBrakeCLI self-sign failed: {signed} was not produced"
                    )
                os.replace(signed, cli)
                os.chmod(cli, 0o755)
            else:
                raise RuntimeError(
                    "OHOS requires an ELF-signed binary, but binary-sign-tool "
                    f"({sign_tool}) or HandBrakeCLI is missing"
                )

    def package_info(self):
        # HandBrakeCLI is an application, not a library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
