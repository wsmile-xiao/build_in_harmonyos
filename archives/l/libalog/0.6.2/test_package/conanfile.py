#!/usr/bin/env python3
"""Consumer + upstream tests for the packaged libalog 0.6.2 Ada library.

Compiles the downstream Ada smoke program (test_package/alog_smoke.adb)
against the packaged specs/ALI/static library with the ``gcc-ada/9.5.0``
GNAT toolchain (adacgi/1.6 pattern), signs the resulting OHOS ELF, and
executes three functional assertions through run_tests.sh.  The upstream
Ahven suite (tests/test_runner.adb, 81 routines) is re-fetched from the
official tarballs and recompiled against the PACKAGED library so this
always-run test_package validates the real consumer path and re-emits
the upstream marker on cached builds.
"""

import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment


_AHVEN_VERSION = "2.8"
_AHVEN_TARBALL = "ahven-%s.tar.gz" % _AHVEN_VERSION
_AHVEN_SHA256 = "6ead94fbd1b95454e959cc2a343acfb2f733bcbf10d9a286214d1dec1b9e8e0c"
_AHVEN_URL = "https://www.ahven-framework.com/releases/%s" % _AHVEN_TARBALL
_UPSTREAM_TARBALL = "libalog-0.6.2.tar.bz2"
_UPSTREAM_SHA256 = "4f6f41aa85f7dec4bc2b4e10a26957514247eee4b5a498762fddab1714768425"
_UPSTREAM_URL = "https://www.codelabs.ch/download/%s" % _UPSTREAM_TARBALL

_ENV_SCRIPT = "libalog_test_gnat_env"


class LibalogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = (
        "alog_smoke.adb",
        "run_tests.sh",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("gcc-ada/9.5.0")
        # as/ld for the GNAT driver when the runner has no HNP bin
        # (libgmpada/1.6 precedent; mirrors the main recipe).
        self.tool_requires("binutils/2.46.0")

    def generate(self):
        env = Environment()
        if str(self.settings.os) == "OHOS":
            # Same HNP binutils PATH fix as the main recipe (adacgi/1.6).
            env.prepend_path("PATH", "/data/service/hnp/bin")
        env.vars(self).save_script(_ENV_SCRIPT)

    def _tool(self, name):
        dependency = self.dependencies.build["gcc-ada"]
        bindirs = dependency.cpp_info.bindirs or ["bin"]
        executable = os.path.join(
            dependency.package_folder, bindirs[0], name
        )
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "The gcc-ada build requirement does not provide {}: {}".format(
                    name, executable
                )
            )
        return executable

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "Running GNAT output on OHOS requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )
        header = subprocess.run(
            [readelf, "-h", path],
            capture_output=True,
            text=True,
            check=True,
        )
        if not re.search(r"Type:\s+(?:EXEC|DYN)\b", header.stdout):
            raise ConanInvalidConfiguration(
                "GNAT did not produce a runnable ELF file: {}".format(path)
            )
        original_mode = stat.S_IMODE(os.stat(path).st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=os.path.dirname(path)
        ) as temp_dir:
            os.chmod(temp_dir, 0o775)
            unsigned = os.path.join(temp_dir, "unsigned")
            signed = os.path.join(temp_dir, "signed")
            shutil.copy2(path, unsigned)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                [signer, "sign", "-inFile", unsigned,
                 "-outFile", signed, "-selfSign", "1"],
                check=True,
            )
            sections = subprocess.run(
                [readelf, "-S", signed],
                capture_output=True,
                text=True,
                check=True,
            )
            if ".codesign" not in sections.stdout:
                raise ConanInvalidConfiguration(
                    "Signing did not add .codesign: {}".format(path)
                )
            os.replace(signed, path)
            os.chmod(
                path,
                original_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
        self.output.info("  [ok] signed " + path)

    def _device_truth(self):
        """Log broad, read-only device facts (mirror of main recipe)."""

        def _note(line):
            self.output.info("  [device-truth] " + line)

        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        _note("tools.build:compiler_executables={!r}".format(configured))
        for path in (
            "/data/service/hnp",
            "/data/service/hnp/bin",
            "/data/service/hnp/ohos-sdk.org",
        ):
            _note("path {} isdir={}".format(path, os.path.isdir(path)))
        for tool in ("clang", "cc", "as", "ld", "ar", "llvm-objcopy",
                     "binary-sign-tool"):
            _note("which({})={}".format(tool, shutil.which(tool)))
        try:
            dep = self.dependencies.build.get("binutils")
            _note("binutils dep present={}".format(dep is not None))
        except Exception as exc:  # noqa: BLE001 - diagnostics only
            _note("binutils dep lookup failed: {}".format(exc))

    def _binutils_bindir(self):
        """Return the binutils/2.46.0 bindir carrying as/ld/ar (or '')."""
        try:
            dep = self.dependencies.build.get("binutils")
        except Exception:  # noqa: BLE001 - optional toolchain
            return ""
        if dep is None or not dep.package_folder:
            return ""
        candidates = [os.path.join(dep.package_folder, d)
                      for d in (dep.cpp_info.bindirs or ["bin"])]
        candidates.append(os.path.join(dep.package_folder, "bin"))
        for path in candidates:
            if path and os.path.isfile(os.path.join(path, "as")):
                return path
        return ""

    def _discover_ohos_sysroot(self):
        """Find a usable OHOS sysroot, or (None, None) when absent
        (mirror of the main recipe: baked value, clang derivations,
        OHOS env hints, SDK globs; layout facts logged)."""
        import glob as _glob

        target = "aarch64-linux-ohos"

        def _note(line):
            self.output.info("  [sysroot-probe] " + line)

        candidates = []
        try:
            real = self._tool("gcc.real")
        except ConanInvalidConfiguration as exc:
            real = ""
            _note("gcc.real lookup failed: {}".format(exc))
        baked = ""
        if real:
            try:
                proc = subprocess.run(
                    [real, "-print-sysroot"],
                    capture_output=True, text=True, timeout=60,
                )
                baked = proc.stdout.strip()
                _note("gcc.real -print-sysroot exit={} value={!r}".format(
                    proc.returncode, baked))
            except (OSError, subprocess.TimeoutExpired) as exc:
                _note("gcc.real -print-sysroot failed: {}".format(exc))
        if baked:
            candidates.append(baked)
        configured = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        clangs = []
        if configured.get("c"):
            clangs.append(configured.get("c"))
        clangs.append("/data/service/hnp/bin/clang")
        hit = shutil.which("clang")
        if hit and hit not in clangs:
            clangs.append(hit)
        for clang in clangs:
            if not (clang and os.path.isfile(clang)):
                _note("clang candidate absent: {}".format(clang))
                continue
            try:
                proc = subprocess.run(
                    [clang, "-print-resource-dir"],
                    capture_output=True, text=True, timeout=60,
                )
                resource = proc.stdout.strip()
                _note("clang {} -print-resource-dir exit={} value={!r}"
                      .format(clang, proc.returncode, resource))
                if proc.returncode == 0 and resource:
                    candidates.append(os.path.normpath(os.path.join(
                        resource, "..", "..", "..", "..", "sysroot")))
            except (OSError, subprocess.TimeoutExpired) as exc:
                _note("clang {} resource-dir failed: {}".format(clang, exc))
            for exe in (os.path.realpath(clang), os.path.abspath(clang)):
                d = os.path.dirname(exe)
                candidates.append(os.path.normpath(
                    os.path.join(d, "..", "..", "sysroot")))
                candidates.append(os.path.normpath(
                    os.path.join(d, "..", "sysroot")))
        for var in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_PATH",
                    "OHOS_SYSROOT"):
            val = os.environ.get(var, "")
            if val:
                _note("{}={!r}".format(var, val))
                candidates.append(val)
                candidates.append(os.path.join(val, "sysroot"))
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot",
            "/data/service/hnp/ohos-sdk/*/ohos/native/sysroot",
            "/data/service/hnp/sysroot",
            "/opt/ohos-sdk*/**/sysroot",
            "/opt/hnp*/**/sysroot",
        ):
            try:
                hits = sorted(_glob.glob(pattern, recursive=True))
            except OSError as exc:
                _note("glob {} error: {}".format(pattern, exc))
                continue
            for found in hits[:10]:
                candidates.append(found)
        _note("total candidates: {}".format(len(candidates)))
        seen = set()
        for candidate in candidates:
            sysroot = os.path.normpath(candidate)
            if not sysroot or sysroot in seen:
                continue
            seen.add(sysroot)
            has_include = os.path.isdir(
                os.path.join(sysroot, "usr", "include"))
            triplet_lib = os.path.join(
                sysroot, "usr", "lib", target)
            plain_lib = os.path.join(sysroot, "usr", "lib")
            triplet_crt = os.path.isfile(
                os.path.join(triplet_lib, "Scrt1.o"))
            plain_crt = os.path.isfile(
                os.path.join(plain_lib, "Scrt1.o"))
            _note("candidate {} include={} triplet_lib={} "
                  "triplet_Scrt1.o={} plain_Scrt1.o={}".format(
                      sysroot, has_include,
                      os.path.isdir(triplet_lib),
                      triplet_crt, plain_crt))
            if not has_include:
                continue
            if triplet_crt:
                return sysroot, triplet_lib
            if plain_crt:
                return sysroot, plain_lib
        self.output.warning(
            "No usable OHOS sysroot on this device; probed: {}".format(
                "; ".join(sorted(seen)) if seen else "none"))
        return None, None

    def _ensure_gcc_shim(self):
        """Write a ``gcc`` shim (mirror of the main recipe).

        Execs ``gcc.real`` directly, adding an explicit ``--sysroot``
        (+ ``-B`` libdir + triplet ``-isystem`` + availability define)
        only when a usable sysroot was found; otherwise plain
        pass-through so failures surface as genuine errors.
        NOTE (round 7/8, mirror): gnatmake ignores PATH for its gcc
        driver (absolute sibling bin/gcc proxy), so every gnatmake
        command passes ``--GCC=<shim>`` explicitly, and --GCC is not
        forwarded to the link phase, so ``--GNATLINK=<wrapper>`` (this
        function also writes a gnatlink wrapper forcing --GCC=<shim>)
        is passed too; PATH prefix is for binutils as/ld/ar only.
        Returns the (gcc shim, gnatlink wrapper) file paths.
        Always rewritten.
        """
        shim_dir = os.path.join(self.build_folder, "fixed-ohos-gcc")
        shim = os.path.join(shim_dir, "gcc")
        sysroot, libdir = self._discover_ohos_sysroot()
        target = "aarch64-linux-ohos"
        real = self._tool("gcc.real")
        # Mirror of the main recipe (round 9): -B<gcc-ada pkg> private
        # lib (crtbegin.o/crtend.o/libgcc) or links fail.
        pkg_root = os.path.normpath(
            os.path.join(os.path.dirname(real), ".."))
        gcc_lib_base = os.path.join(pkg_root, "lib", "gcc", target)
        gcc_lib = ""
        try:
            versions = sorted(os.listdir(gcc_lib_base))
        except OSError as exc:
            self.output.warning(
                "  [shim] gcc private lib not listable ({}): {}".format(
                    gcc_lib_base, exc))
            versions = []
        for version in versions:
            candidate = os.path.join(gcc_lib_base, version)
            if os.path.isfile(os.path.join(candidate, "crtbegin.o")):
                gcc_lib = candidate
                break
        if gcc_lib:
            self.output.info(
                "  [shim] gcc private lib: {}".format(gcc_lib))
        else:
            self.output.warning(
                "  [shim] no crtbegin.o under {}; links are expected "
                "to fail".format(gcc_lib_base))
        lines = [
            "#!/bin/sh",
            "# libalog test_package fixed OHOS gcc shim.",
            "set -eu",
            "real=%s" % shlex.quote(real),
        ]
        if sysroot:
            lines.extend([
                "sysroot=%s" % shlex.quote(sysroot),
                "libdir=%s" % shlex.quote(libdir),
                "set -- \"--sysroot=$sysroot\" \"-B$libdir/\" \"$@\"",
            ])
            triplet_inc = os.path.join(sysroot, "usr", "include", target)
            if os.path.isdir(triplet_inc):
                lines.append("set -- -isystem %s \"$@\""
                             % shlex.quote(triplet_inc))
            lines.append("set -- '-D__availability__(...)=' \"$@\"")
        else:
            lines.append("sysroot=; libdir=")
            self.output.warning(
                "  [shim] no sysroot: pass-through mode")
        if gcc_lib:
            lines.append("pkg_gcc_lib=%s" % shlex.quote(gcc_lib))
            lines.append("set -- \"-B$pkg_gcc_lib/\" \"$@\"")
        lines.extend([
            "link=1",
            "has_input=0",
            "takes_value=0",
            'for argument in "$@"; do',
            '    if [ "$takes_value" -eq 1 ]; then',
            "        takes_value=0",
            "        continue",
            "    fi",
            '    case "$argument" in',
            "        -c|-S|-E|-M|-MM|-fsyntax-only) link=0 ;;",
            "        -o|-x|-isystem|-include|-imacros|-MF|-MT|-MQ|-B|-L|-I|-D|-U|-specs)",
            "            takes_value=1 ;;",
            "        -) has_input=1 ;;",
            "        -*) ;;",
            "        *) has_input=1 ;;",
            "    esac",
            "done",
            'if [ -n "$sysroot" ] && [ "$link" -eq 1 ] && [ "$has_input" -eq 1 ]; then',
            '    sdk_native=$(CDPATH= cd "$sysroot/.." && pwd -P)',
            '    libunwind="$sdk_native/llvm/lib/%s/libunwind.a"' % target,
            '    if [ -f "$libunwind" ]; then',
            '        set -- -Wl,--whole-archive "$libunwind" '
            '"-Wl,--no-whole-archive" "$@"',
            "    fi",
            "fi",
            'exec "$real" "$@"',
        ])
        os.makedirs(shim_dir, exist_ok=True)
        with open(shim, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
        os.chmod(shim, 0o755)
        self.output.info(
            "  [ok] fixed gcc shim: {} (sysroot={} libdir={})".format(
                shim, sysroot, libdir))
        # Mirror of the main recipe (round 8): gnatlink wrapper forcing
        # --GCC=<shim>, selected via --GNATLINK=<wrapper>.
        real_gnatlink = self._tool("gnatlink")
        link_wrap = os.path.join(shim_dir, "gnatlink")
        with open(link_wrap, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "#!/bin/sh\n"
                "# libalog test_package fixed gnatlink wrapper.\n"
                "exec {} {} \"$@\"\n".format(
                    shlex.quote(real_gnatlink),
                    shlex.quote("--GCC=" + shim)))
        os.chmod(link_wrap, 0o755)
        self.output.info(
            "  [ok] fixed gnatlink wrapper: {}".format(link_wrap))
        return shim, link_wrap

    def _fetch_cached(self, url, filename, sha256, cache_subdir):
        """Download one pinned tarball into the shared home cache."""
        cache = os.path.join(os.path.expanduser("~"), ".cache", cache_subdir)
        os.makedirs(cache, exist_ok=True)
        archive = os.path.join(cache, filename)
        if os.path.isfile(archive):
            actual = hashlib.sha256(open(archive, "rb").read()).hexdigest()
            if actual == sha256:
                return archive
            self.output.warning(
                "cached %s fails sha256 (got %s); re-downloading"
                % (filename, actual))
            try:
                os.remove(archive)
            except OSError:
                pass
        self.output.info("downloading %s" % filename)
        with urllib.request.urlopen(url, timeout=120) as resp, \
                open(archive, "wb") as out:
            shutil.copyfileobj(resp, out)
        actual = hashlib.sha256(open(archive, "rb").read()).hexdigest()
        if actual != sha256:
            raise ConanInvalidConfiguration(
                "sha256 mismatch for %s: got %s expected %s"
                % (filename, actual, sha256))
        return archive

    def _ensure_ahven(self):
        """Unpack Ahven 2.8 (test-only) into this package's build folder."""
        root = os.path.join(self.build_folder, "ahven-2.8")
        probe = os.path.join(root, "src", "ahven-text_runner.adb")
        if os.path.isfile(probe):
            return root
        archive = self._fetch_cached(
            _AHVEN_URL, _AHVEN_TARBALL, _AHVEN_SHA256, "alog-ahven")
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(self.build_folder)
        if not os.path.isfile(probe):
            raise ConanInvalidConfiguration(
                "Ahven unpack failed: %s not found" % probe)
        return root

    def _ensure_upstream(self):
        """Unpack the upstream libalog sources (tests + data + src)."""
        root = os.path.join(self.build_folder, "libalog-0.6.2")
        probe = os.path.join(root, "tests", "test_runner.adb")
        if os.path.isfile(probe):
            return root
        archive = self._fetch_cached(
            _UPSTREAM_URL, _UPSTREAM_TARBALL, _UPSTREAM_SHA256,
            "alog-upstream")
        with tarfile.open(archive, "r:*") as tf:
            tf.extractall(self.build_folder)
        if not os.path.isfile(probe):
            raise ConanInvalidConfiguration(
                "upstream unpack failed: %s not found" % probe)
        return root

    @staticmethod
    def _parse_ahven_summary(output):
        """Parse the deterministic Ahven Text_Runner summary (mirror of
        the main recipe: Passed/Failed/Errors/Skipped summary lines are
        the single counting source; raises with reason when absent)."""
        counts = {}
        for name in ("Passed", "Failed", "Errors", "Skipped"):
            m = re.search(
                r"^" + name + r"\s*:\s*(\d+)\s*$", output, re.MULTILINE)
            counts[name] = int(m.group(1)) if m else 0
        if not re.search(r"^Passed\s*:\s*\d+\s*$", output, re.MULTILINE):
            raise RuntimeError(
                "Ahven summary 'Passed :' line not found in test output "
                "(%d chars); refusing to guess counts" % len(output))
        failed_names = []
        for line in output.splitlines():
            m = re.match(
                r"^\s{2,}(.{1,60}?)\s{2,}(FAIL|ERROR)\s+\S", line)
            if m:
                failed_names.append(m.group(1).strip() + ":" + m.group(2))
        return (counts["Passed"], counts["Failed"], counts["Errors"],
                counts["Skipped"], failed_names)

    def build(self):
        self._device_truth()
        gnatmake = self._tool("gnatmake")
        self._tool("gnatbind")
        self._tool("gnatlink")
        env = ["conanbuild", _ENV_SCRIPT]
        # Same stale-wrapper bypass as the main recipe (see
        # _ensure_gcc_shim): gnat ignores PATH for its `gcc` driver,
        # so --GCC=<shim> is passed explicitly below.
        # binutils/2.46.0 supplies as/ld when the runner has no HNP bin.
        shim, gnatlink_wrap = self._ensure_gcc_shim()
        gcc_opt = shlex.quote("--GCC=" + shim)
        link_opt = shlex.quote("--GNATLINK=" + gnatlink_wrap)
        self.output.info("  [gnat] driver override: {}".format(gcc_opt))
        self.output.info("  [gnat] linker override: {}".format(link_opt))
        path_dirs = []
        binutils_dir = self._binutils_bindir()
        if binutils_dir:
            path_dirs.append(binutils_dir)
            self.output.info(
                "  [tools] binutils bindir: {}".format(binutils_dir))
        path_prefix = "export PATH={}:$PATH && ".format(
            shlex.quote(":".join(path_dirs))) if path_dirs else ""
        package = self.dependencies[self.tested_reference_str.split("/")[0]]
        include_dir = os.path.join(
            package.package_folder, package.cpp_info.includedirs[0])
        lib_dir = os.path.join(
            package.package_folder, package.cpp_info.libdirs[0])
        for label, path, expect_dir in (
            ("include dir", include_dir, True),
            ("library dir", lib_dir, True),
        ):
            ok = os.path.isdir(path) if expect_dir else os.path.isfile(path)
            if not ok:
                raise ConanInvalidConfiguration(
                    "required consumer-test input is missing: {}".format(path))

        # Consumer smoke binary: gnatmake resolves the Alog sources via
        # -I<include>, the ALI bind info via -aL<lib>, and the static
        # archive via -largs -L<lib> -lalog.
        source = os.path.join(self.source_folder, "alog_smoke.adb")
        binary = os.path.join(self.build_folder, "alog_smoke")
        self.run(
            path_prefix +
            "{g} {gcc} {link} -I{inc} -aL{lib} -O2 {src} -o {bin} "
            "-largs -L{lib} -lalog".format(
                g=shlex.quote(gnatmake), gcc=gcc_opt, link=link_opt,
                inc=shlex.quote(include_dir),
                lib=shlex.quote(lib_dir),
                src=shlex.quote(source),
                bin=shlex.quote(binary)),
            env=env,
        )
        self._sign_program(binary)

        # Upstream suite against the PACKAGED library (specs from
        # include/alog, libalog.a + ALI from lib/).
        up_root = self._ensure_upstream()
        ahven_root = self._ensure_ahven()
        up_binary = os.path.join(self.build_folder, "test_runner")
        self.run(
            path_prefix +
            "mkdir -p {obj} && "
            "{g} {gcc} {link} -D {obj} -I{inc} -aL{lib} "
            "-I{usrc} -I{utst} -I{ah} -I{ahu} -O2 "
            "{src} -o {bin} "
            "-largs -L{lib} -lalog".format(
                g=shlex.quote(gnatmake), gcc=gcc_opt, link=link_opt,
                obj=shlex.quote(os.path.join(self.build_folder, "up-obj")),
                inc=shlex.quote(include_dir),
                lib=shlex.quote(lib_dir),
                usrc=shlex.quote(os.path.join(up_root, "src")),
                utst=shlex.quote(os.path.join(up_root, "tests")),
                ah=shlex.quote(os.path.join(ahven_root, "src")),
                ahu=shlex.quote(os.path.join(ahven_root, "src", "unix")),
                src=shlex.quote(
                    os.path.join(up_root, "tests", "test_runner.adb")),
                bin=shlex.quote(up_binary)),
            env=env,
        )
        self._sign_program(up_binary)

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-building: GNAT compile, bind and link completed; "
                "execution skipped")
            return
        # ---- Consumer smoke test (3 assertions) via the L0c driver.
        binary = os.path.join(self.build_folder, "alog_smoke")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                "The libalog smoke executable was not built: {}".format(binary))
        driver = os.path.join(self.source_folder, "run_tests.sh")
        if not os.path.isfile(driver):
            raise ConanInvalidConfiguration(
                "required test driver is missing: {}".format(driver))
        proc = subprocess.run(
            ["sh", driver, binary],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
        )
        output = proc.stdout
        self.output.info(output)
        m = re.search(r"checks_passed=\s*(\d+)", output)
        if proc.returncode != 0 or m is None:
            self.output.error("=== alog_smoke output tail ===\n" + output[-800:])
            raise ConanInvalidConfiguration("test_package smoke test failed")
        passed_count = int(m.group(1))
        if passed_count < 3:
            raise ConanInvalidConfiguration(
                "test_package smoke test passed only {} checks".format(passed_count))
        result = {
            "executed": True,
            "passed": True,
            "command": "./alog_smoke",
            "discovered": passed_count,
            "passedCount": passed_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))

        # ---- Upstream Ahven suite (81 routines), cwd at the upstream
        # root for the ./data/*.ref fixtures.  The FD/helper cases
        # create their logfiles as ./obj/<name> relative to this cwd
        # (upstream alog_tests.gpr uses Object_Dir obj/ for the same
        # purpose), so the directory must exist: a fresh upstream
        # unpack has src/tests/data/... but no obj/ (objects live in
        # build/up-obj), hence the previous 15x OPEN_FILE_ERROR
        # "No such file or directory" (passed=66 errors=15).
        up_root = os.path.join(self.build_folder, "libalog-0.6.2")
        up_binary = os.path.join(self.build_folder, "test_runner")
        if not os.path.isfile(up_binary):
            raise ConanInvalidConfiguration(
                "Upstream test executable was not built: {}".format(up_binary))
        os.makedirs(os.path.join(up_root, "obj"), exist_ok=True)
        up_proc = subprocess.run(
            [up_binary],
            cwd=up_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1800,
        )
        self.output.info(up_proc.stdout)
        (up_pass, up_fail, up_err, up_skip, up_failed_names) = \
            self._parse_ahven_summary(up_proc.stdout)
        up_discovered = up_pass + up_fail + up_err + up_skip
        up_executed = up_pass + up_fail + up_err
        up_failed_total = up_fail + up_err
        self.output.info(
            "upstream test_runner exit={} passed={} failed={} "
            "errors={} skipped={}".format(
                up_proc.returncode, up_pass, up_fail, up_err, up_skip))
        up_ok = (up_proc.returncode == 0 and up_failed_total == 0
                 and up_discovered > 0)
        upstream = {
            "status": "passed" if up_ok else "failed",
            "framework": "ahven",
            "command": "./test_runner (tests/test_runner.adb)",
            "discovered": up_discovered,
            "executed": up_executed,
            "passed": up_pass,
            "failed": up_failed_total,
            "skipped": up_skip,
        }
        if not up_ok:
            if up_failed_names:
                upstream["gaps"] = [{
                    "count": up_failed_total,
                    "category": "test_failure",
                    "detail": "failed routines: "
                              + "; ".join(up_failed_names[:20]),
                    "evidence": "Ahven FAIL/ERROR lines in output above",
                }]
            else:
                upstream["gaps"] = [{
                    "count": up_discovered - up_pass,
                    "category": "test_failure",
                    "detail": "exit=%s; see output tail" % up_proc.returncode,
                    "evidence": up_proc.stdout[-2000:],
                }]
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if not up_ok:
            self.output.error(
                "=== test_runner output tail ===\n" + up_proc.stdout[-2000:])
            raise ConanInvalidConfiguration(
                "upstream tests failed: exit={} passed={} failed={} "
                "errors={} skipped={}".format(
                    up_proc.returncode, up_pass, up_fail, up_err, up_skip))
