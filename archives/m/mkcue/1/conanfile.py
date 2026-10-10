#!/usr/bin/env python3
"""Conan recipe — mkcue 1 (CUE sheet generator from a CD's TOC).

mkcue is a single-binary C++ program by Eric Gillespie.  It reads a CD's
Table Of Contents through the Linux CDROM ioctls and prints a CUE sheet
on stdout.

Upstream is distributed only through the author's Subversion tree
(``https://diplodocus.org/``), so version ``1`` builds from the canonical
Debian original tarball ``mkcue_1.orig.tar.gz`` (see ``conandata.yml``).

Build system is minimal autotools: a pre-generated ``configure``
(AC_INIT(mkcue, 1, ...)) plus a hand-written ``GNUmakefile.in``.  Two
translation units are linked (``mkcue.cc`` + the platform file
``osdep/mb_linux.cpp``, copied to ``mb.cc`` by ``AC_LINK_FILES``); the
link line carries no ``-l``, so the package has **no third-party
dependencies** under Linux/OHOS.

The tarball ships no test suite at all (no ``tests/`` directory and no
``check``/``test`` target in ``GNUmakefile.in``); see
``test_package/MANIFEST.yml`` for the upstream no-tests audit and
``test_package/`` for the consumer verification.

Directory-artifact separation (house pattern cutmp3/4, cronic/3):
task-card directory ``archives/m/mkcue/1`` keeps the single-character
upstream label ``1`` (branch feat/mkcue-1), while the built artifact uses
the dotted upstream form ``1.0`` because Conan 2.29+ rejects one-character
versions at export (``ERROR: Invalid package version '1'``).
"""

import os
import glob
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MkcueConan(ConanFile):
    name = "mkcue"
    description = "Generates a CUE sheet from a CD's Table Of Contents"
    license = "LGPL-2.1-or-later"  # upstream COPYING is LGPL-2.1 (README says "GNU GPL")
    homepage = "https://diplodocus.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # Conan 2.29+ RecipeReference regex requires >= 2 chars, so the
        # single-character task version "1" cannot be exported directly.
        # Directory/branch keep "1" (archives/m/mkcue/1, feat/mkcue-1);
        # the artifact uses the dotted upstream form "1.0".
        # Precedent: cutmp3/4 -> 4.0, cvechecker/4 -> 4.0.
        self.version = "1.0"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: mkcue only speaks the Linux CDROM ioctl interface (osdep/mb_linux.cpp).
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} only supports Linux and OHOS, not {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: the compiler comes from the Conan toolchain (tools.build:compiler_executables
        # / the profile), never from a bare ${CC}/${CXX} shell variable.
        tc = AutotoolsToolchain(self)
        # mkcue's hand-written GNUmakefile is not VPATH-clean: configure's
        # AC_LINK_FILES creates mb.cc/mb.h in the *build* folder while diskid.h and
        # the other headers stay in the *source* folder, and the two translation
        # units include across the two folders in both directions.  Put both on the
        # include path explicitly instead of patching upstream.
        tc.extra_cxxflags.extend([f"-I{self.source_folder}", f"-I{self.build_folder}"])
        tc.extra_cflags.extend([f"-I{self.source_folder}", f"-I{self.build_folder}"])
        # Profile buildenv exports SHELL/CONFIG_SHELL as
        # /data/service/hnp/bin/bash, which does not exist on the preflight
        # worker (FileNotFoundError) while /bin/sh canonicalizes every
        # triplet with rc=0. Prior rounds tried Environment save_script
        # (scope build) + os.environ overrides and still failed: the bad
        # value returns via conanbuild.sh sourcing order. Pass SHELL as
        # configure *arguments* instead (precious vars assigned inside the
        # script), immune to outer env ordering.
        tc.configure_args.extend(["SHELL=/bin/sh", "CONFIG_SHELL=/bin/sh"])
        tc.make_args.append("SHELL=/bin/sh")
        # Preflight 2026-10-08 evidence: profile conf points CXX at
        # /data/service/hnp/bin/clang++ but the worker has no such file
        # (build() probe FileNotFoundError) so configure dies with Error 77.
        # Same immunity trick as SHELL: pass the real driver as configure
        # precious-var arguments (CC=/real/clang CXX=/real/clang++), which the
        # script assigns internally regardless of conanbuild.sh ordering.
        # Discovery prefers PATH (hmbs-prepended tool dirs), then env, then
        # the OHOS SDK llvm tree the profile LD_LIBRARY_PATH already proves.
        _cc, _cxx = self._find_ohos_compilers()
        if _cc and _cxx:
            tc.configure_args.extend([f"CC={_cc}", f"CXX={_cxx}"])
            self.output.info(f"mkcue compiler override: CC={_cc} CXX={_cxx}")
        else:
            self.output.warning("mkcue compiler override skipped: no usable clang found")
        tc.generate()

    def _find_ohos_compilers(self):
        """Return (cc, cxx) absolute paths or (None, None)."""
        def _usable(path):
            return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)

        _cc_env = os.environ.get("CC")
        _cxx_env = os.environ.get("CXX")
        _candidates_cc = [
            _cc_env,
            shutil.which("clang"),
            "/storage/Users/currentUser/usr/local/bin/clang",
            "/data/service/hnp/bin/clang",
            "/usr/bin/clang",
            "/usr/local/bin/clang",
        ]
        _candidates_cxx = [
            _cxx_env,
            shutil.which("clang++"),
            "/storage/Users/currentUser/usr/local/bin/clang++",
            "/data/service/hnp/bin/clang++",
            "/usr/bin/clang++",
            "/usr/local/bin/clang++",
        ]
        # OHOS SDK llvm tree (profile LD_LIBRARY_PATH proves
        # .../ohos-sdk_26.0.0.18/ohos/native/llvm/lib exists on workers).
        for _sdk_clang in sorted(glob.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang")):
            _candidates_cc.append(_sdk_clang)
        for _sdk_clangxx in sorted(glob.glob("/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang++")):
            _candidates_cxx.append(_sdk_clangxx)
        try:
            _execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            _execs = {}
        # Profile value last: it is the CI-canonical path but missing on preflight.
        _candidates_cc.append((_execs or {}).get("c"))
        _candidates_cxx.append((_execs or {}).get("cpp"))

        _cc = next((p for p in _candidates_cc if _usable(p)), None)
        _cxx = next((p for p in _candidates_cxx if _usable(p)), None)
        self.output.info(f"mkcue compiler discovery: cc_candidates={_candidates_cc} -> {_cc}")
        self.output.info(f"mkcue compiler discovery: cxx_candidates={_candidates_cxx} -> {_cxx}")
        return _cc, _cxx

    def build(self):
        apply_conandata_patches(self)

        # E490: autotools helper scripts are executable programs; some adaptation
        # paths preserve file contents without the exec bit, so restore it.
        # HMBS_CAP_CHMOD=0 workers ignore chmod: never let it abort the build.
        for rel in ("configure", "build/config.guess", "build/config.sub", "build/install-sh"):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod {rel} skipped: {exc!r}")

        # Current failure moved past config.sub to the compiler sanity test:
        # "checking for C++ compiler default output... configure: error:
        #  C++ compiler cannot create executables" (Error 77). Prior cycles
        # proved the SHELL hypothesis (configure_args SHELL=/bin/sh kept) but
        # never examined the compiler temp-file path. coinor-vol precedent:
        # clang needs a writable TMPDIR; a stale $HOME/tmp or an unwritable
        # injected TMPDIR breaks the very first compile test even when
        # `clang --version` works. Probe candidates with a real file write
        # (HMDFS ignores chmod/os.access, so only open(w)+unlink counts) and
        # fall back to build_folder/.tmp which conan already proved writable.
        _tmpdir = None
        _candidates = []
        for _key in ("TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_key)
            if _val:
                _candidates.append(_val)
        _candidates.append(os.path.join(os.path.expanduser("~"), "tmp"))
        _candidates.append(os.path.join(self.build_folder, ".tmp"))
        for _cand in _candidates:
            try:
                os.makedirs(_cand, exist_ok=True)
                _probe = os.path.join(_cand, ".mkcue-tmp-write-probe")
                with open(_probe, "w") as _pf:
                    _pf.write("ok")
                os.unlink(_probe)
                _tmpdir = _cand
                break
            except OSError:
                continue
        if _tmpdir is not None:
            os.environ["TMPDIR"] = _tmpdir
            os.environ["TMP"] = _tmpdir
            os.environ["TEMP"] = _tmpdir
            self.output.info(f"mkcue TMPDIR probe: using {_tmpdir}")
        else:
            self.output.warning("mkcue TMPDIR probe: no writable candidate found")

        # Log the effective C++ driver before configure so the next preflight
        # log shows whether the failure is driver-missing or link-time.
        # generate() already passed the discovered driver as configure args;
        # re-discover here for logging (PATH may differ slightly by phase).
        _disc_cc, _disc_cxx = self._find_ohos_compilers()
        try:
            _execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            _execs = {}
        _cxx = _disc_cxx or _execs.get("cpp", os.environ.get("CXX", "clang++"))
        self.output.info(f"mkcue compiler probe: CXX={_cxx} (discovered={_disc_cxx}) PATH={os.environ.get('PATH', '')[:400]}")
        try:
            _ver = subprocess.run(
                [_cxx, "--version"],
                capture_output=True, text=True, errors="replace", timeout=60,
            )
            self.output.info(f"mkcue compiler probe rc={_ver.returncode}: {(_ver.stdout or '').splitlines()[:1]}")
        except Exception as exc:
            self.output.warning(f"mkcue compiler probe failed: {exc!r}")

        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            # Surface the real first error: configure only prints the summary
            # line while config.log holds the failing command (e.g. clang
            # "unable to make temporary file" vs missing sysroot vs bad flag).
            import glob
            _logs = []
            for _pat in (
                os.path.join(self.build_folder, "config.log"),
                os.path.join(self.build_folder, "**", "config.log"),
                os.path.join(self.source_folder, "config.log"),
            ):
                _logs.extend(glob.glob(_pat, recursive=True))
            _seen = set()
            for _log in _logs:
                if _log in _seen:
                    continue
                _seen.add(_log)
                try:
                    with open(_log, "r", encoding="utf-8", errors="replace") as _fh:
                        _lines = _fh.read().splitlines()
                    self.output.info(f"mkcue config.log dump ({_log}, last 60 lines):")
                    for _line in _lines[-60:]:
                        self.output.info(f"mkcue-config-log| {_line}")
                except OSError as exc:
                    self.output.warning(f"mkcue config.log unreadable {_log}: {exc!r}")
            if not _seen:
                self.output.warning(
                    "mkcue config.log not found under build/source folders; "
                    "searched build/config.log, build/**/config.log, source/config.log"
                )
            raise
        autotools.make()
        # Upstream ships no test suite: GNUmakefile.in defines only
        # all/clean/maintainer-clean/install/dist, no check/test target
        # (audited in test_package/MANIFEST.yml). No make check here.

    def package(self):
        # Preflight 2026-10-08: `make install` dies at the very first install
        # rule (`GNUmakefile:76: <pkg>/bin/mkcue] Error 64`, EX_USAGE) even
        # though `make` itself succeeded. The failing command is the
        # `install -c -m 755 [-d]` separate-args form baked by AC_PROG_INSTALL
        # into INSTALL/INSTALL_PROGRAM/INSTALL_DIR: the HMBS/OHOS `install`
        # shim on PATH only accepts single-file two-arg calls (zurl #35,
        # cvechecker/4 #9, postgresql-18.3 `cp: bad '755'` are the same
        # family) and exits 64 on `-c -m 755` / `-d`. The tarball already
        # ships the canonical portable installer `build/install-sh` (which
        # correctly handles `-c/-m/-d`), so redirect the generated
        # GNUmakefile/Makefile INSTALL variables to it before installing.
        # This keeps upstream `make install` semantics (single binary to
        # $(bindir)); no source, test, or file-list change.
        self._redirect_install_to_bundled_install_sh()
        autotools = Autotools(self)
        autotools.install(args=["SHELL=/bin/sh"])

        # The upstream GNUmakefile installs only the binary; ship the README as docs.
        copy(
            self,
            "README",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "mkcue"),
            keep_path=False,
        )

        binary = os.path.join(self.package_folder, "bin", "mkcue")
        if os.path.isfile(binary):
            try:
                os.chmod(binary, 0o755)
            except OSError as exc:
                self.output.warning(f"chmod packaged binary skipped: {exc!r}")
            self._ensure_ohos_signature(binary)

    def _redirect_install_to_bundled_install_sh(self):
        """Point generated Makefiles' INSTALL vars at bundled install-sh.

        configure bakes `INSTALL = <hmbs-shim>/install -c` (plus
        INSTALL_PROGRAM/INSTALL_DATA derived from it and the custom
        INSTALL_DIR added by 0001) at configure time. The shim exits 64 on
        the separate-args form this package uses, so rewrite those lines to
        `/bin/sh <source>/build/install-sh -c [...]` which is the upstream
        AC_PROG_INSTALL fallback itself. Only lines already referencing an
        `/install` program or starting with a known INSTALL key are touched;
        `${INSTALL}`-derived lines keep working via the rewritten INSTALL.
        Idempotent; Linux unaffected (install-sh is portable).
        """
        candidates = [
            os.path.join(self.source_folder, "build", "install-sh"),
            os.path.join(self.source_folder, "install-sh"),
        ]
        install_sh = next((p for p in candidates if os.path.isfile(p)), None)
        if install_sh is None:
            self.output.warning(
                "bundled install-sh not found (tried %s); "
                "INSTALL redirect skipped" % ", ".join(candidates)
            )
            return 0
        mapping = {
            "INSTALL": f"/bin/sh {install_sh} -c",
            "INSTALL_PROGRAM": f"/bin/sh {install_sh} -c -m 755",
            "INSTALL_DATA": f"/bin/sh {install_sh} -c -m 644",
            "INSTALL_SCRIPT": f"/bin/sh {install_sh} -c",
            "INSTALL_DIR": f"/bin/sh {install_sh} -c -m 755 -d",
            "MKDIR_P": f"/bin/sh {install_sh} -c -d",
        }
        redirected = 0
        for root, _dirs, files in os.walk(self.build_folder):
            for name in ("GNUmakefile", "Makefile", "makefile"):
                if name not in files:
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="surrogateescape") as fh:
                        content = fh.read()
                except OSError:
                    continue
                if "/install" not in content and "${INSTALL}" not in content:
                    continue
                changed = False
                lines = []
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    key = stripped.split("=", 1)[0].strip() if "=" in stripped else ""
                    if key in mapping and (
                        "/install" in stripped or "${INSTALL}" in stripped
                        or stripped.startswith(key)
                    ):
                        # Only rewrite when the line is a make variable
                        # assignment for a known INSTALL key; keep indentation.
                        indent = line[:len(line) - len(stripped)]
                        lines.append(f"{indent}{key} = {mapping[key]}\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    try:
                        with open(path, "w", encoding="utf-8",
                                  errors="surrogateescape", newline="\n") as fh:
                            fh.write("".join(lines))
                    except OSError as exc:
                        self.output.warning(f"INSTALL redirect unwritable {path}: {exc!r}")
                        continue
                    redirected += 1
        self.output.info(
            f"mkcue INSTALL redirect to bundled install-sh in {redirected} Makefile(s)"
        )
        return redirected

    # ── OHOS ELF 签名（E077）：HarmonyOS 只加载带有效 .codesign 段的 ELF ─────
    def _tool(self, name, fallbacks):
        found = shutil.which(name)
        for candidate in ([found] if found else []) + list(fallbacks):
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _has_codesign_section(self, readelf, path):
        try:
            completed = subprocess.run(
                [readelf, "-S", path],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return completed.returncode == 0 and ".codesign" in completed.stdout

    def _sign_ohos_elf(self, path):
        signer = self._tool(
            "binary-sign-tool",
            [os.environ.get("OHOS_SIGN_TOOL"), "/data/service/hnp/bin/binary-sign-tool"],
        )
        if signer is None:
            self.output.warning(
                f"binary-sign-tool is unavailable; {os.path.basename(path)} left unsigned"
            )
            return

        signed = f"{path}.signed"
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{signed}" -selfSign 1')
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def _ensure_ohos_signature(self, path):
        """Verify the toolchain-produced ``.codesign`` section, repair if missing.

        The OHOS SDK clang driver already signs every image it links
        (``ld.lld --code-sign``) and this recipe performs no post-link ELF
        mutation, so the signature produced by the linker is normally still
        intact; signing again would only churn the file.
        """
        if str(self.settings.os) != "OHOS":
            return

        readelf = self._tool(
            "llvm-readelf",
            [os.environ.get("OHOS_READELF"), "/data/service/hnp/bin/llvm-readelf"],
        )
        if readelf and self._has_codesign_section(readelf, path):
            return

        self._sign_ohos_elf(path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
