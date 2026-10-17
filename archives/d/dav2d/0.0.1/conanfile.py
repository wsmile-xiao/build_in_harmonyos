#!/usr/bin/env python3
"""Conan recipe — dav2d 0.0.1 (meson)

VideoLAN dav2d: small and fast AV2 decoder, successor of dav1d.
C-only Meson profile for HarmonyOS PC (aarch64):

- pure C build (asm/tools/examples/docs off), no NASM needed;
- upstream header tests on (6 per-header tests), test-data suite off
  (requires the separate dav2d-test-data repository);
- wrap_mode=nodownload: subproject wraps must never hit the network.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import collect_libs, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Dav2dConan(ConanFile):
    name = "dav2d"
    version = "0.0.1"
    description = "Small and fast AV2 decoder from the VideoLAN project"
    license = "BSD-2-Clause"
    homepage = "https://code.videolan.org/videolan/dav2d"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # retry/retry_wait: first connection to the origin is flaky from
        # some workers; get() retries the download instead of failing fast.
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=3, retry_wait=10)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Pure-C library profile: no asm (keeps checkasm out, it needs the
        # external checkasm wrap), no CLI tools/examples/docs, upstream
        # header tests on, external test-data suite off.
        tc.project_options["enable_asm"] = False
        tc.project_options["enable_tools"] = False
        tc.project_options["enable_examples"] = False
        tc.project_options["enable_tests"] = True
        tc.project_options["enable_docs"] = False
        tc.project_options["testdata_tests"] = False
        # Dependencies must come from Conan only: never let Meson download
        # wrap subprojects behind our back; a missing piece fails loudly.
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._patch_meson_machine_files()

    def build(self):
        self._ensure_meson()
        meson = Meson(self)
        self._meson_configure(meson)
        meson.build()
        # Upstream test suite runs on the target machine at the end of
        # build() and emits the HMBS_UPSTREAM_TEST_RESULT evidence marker.
        self._run_upstream_tests()

    def package(self):
        self._ensure_meson()
        Meson(self).install()
        self._copy_shared_library_aliases()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_package_elfs()
        # Persist the upstream test verdict inside the package so
        # test_package can re-emit the same marker every round (build() is
        # skipped on Conan cache hits, test_package always runs).
        _jf = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(_jf):
            _res = os.path.join(self.package_folder, "res")
            os.makedirs(_res, exist_ok=True)
            shutil.copy2(_jf, os.path.join(_res, "upstream_test_result.json"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["dav2d"]
        self.cpp_info.set_property("cmake_file_name", "dav2d")
        self.cpp_info.set_property("cmake_target_name", "dav2d::dav2d")
        self.cpp_info.set_property("pkg_config_name", "dav2d")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]

    def _ensure_meson(self):
        """Provide a working `meson` executable on machines without one.

        Official CI workers ship meson globally and skip this entirely.
        The shared preflight device only injects cmake/make/ninja/python3,
        so build() would fail with 'meson: inaccessible or not found'.
        Bootstrap order: reuse the device python3's mesonbuild module when
        present, else download the meson 1.5.1 source tarball (GitHub
        mirror first, official URL last; identical archive, sha256
        unchanged) and run its meson.py. The wrapper is created with
        os.open(0o755) so no chmod round-trip is needed.
        """
        if shutil.which("meson"):
            return
        _bin = os.path.join(self.build_folder, "meson-bin")
        _script = os.path.join(_bin, "meson")
        if os.path.isfile(_script):
            os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")
            return
        python = os.environ.get("HMBS_PYTHON3") or "python3"
        entry = None
        try:
            _r = subprocess.run([python, "-c", "import mesonbuild"],
                                capture_output=True)
            if _r.returncode == 0:
                # -u forces line-buffered output: Conan captures the child
                # stdout through a pipe and Meson otherwise block-buffers,
                # which can look like a hang to intermediate gateways.
                entry = 'exec "%s" -u -m mesonbuild.mesonmain "$@"' % python
        except OSError:
            entry = None
        if entry is None:
            _src = os.path.join(self.build_folder, "meson-src")
            if not os.path.isfile(os.path.join(_src, "meson.py")):
                _m_url = ("https://github.com/mesonbuild/meson/releases/download/"
                          "1.5.1/meson-1.5.1.tar.gz")
                get(self,
                    url=[
                        "https://gh-proxy.com/" + _m_url,
                        "https://mirror.ghproxy.com/" + _m_url,
                        _m_url,
                    ],
                    retry=3, retry_wait=10,
                    sha256="567e533adf255de73a2de35049b99923caf872a455af9ce03e01077e0d384bed",
                    destination=_src, strip_root=True)
            entry = 'exec "%s" -u "%s" "$@"' % (python, os.path.join(_src, "meson.py"))
        os.makedirs(_bin, exist_ok=True)
        _fd = os.open(_script, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o755)
        with os.fdopen(_fd, "w") as _f:
            _f.write("#!/bin/sh\n" + entry + "\n")
        os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")
        self.output.info("[dav2d] meson bootstrap: %s" % entry)

    def _meson_configure(self, meson):
        """Run meson setup with one retry on transient gateway failures.

        On failure the tail of meson-log.txt is dumped (real root cause for
        the next round), meson-private/ is removed so the retry starts from
        a clean setup, and the error is re-raised after the second attempt.
        """
        for _i in (1, 2):
            try:
                meson.configure()
                return
            except ConanException as _e:
                self.output.info("[dav2d] meson setup failed (attempt %d/2): %s" % (_i, _e))
                _log = os.path.join(self.build_folder, "meson-logs", "meson-log.txt")
                if os.path.isfile(_log):
                    try:
                        with open(_log, encoding="utf-8", errors="replace") as _f:
                            _tail = "".join(_f.readlines()[-40:])
                        self.output.info("[dav2d] meson-log.txt tail:\n%s" % _tail)
                    except OSError:
                        pass
                if _i == 2:
                    raise
                _mp = os.path.join(self.build_folder, "meson-private")
                if os.path.isdir(_mp):
                    shutil.rmtree(_mp, ignore_errors=True)
                self.output.info("[dav2d] waiting 65s before retrying meson setup...")
                time.sleep(65)

    def _run_upstream_tests(self):
        """Execute the dav2d upstream suite (meson test) on the target.

        Streams meson test output line by line (keeps long runs visibly
        alive), parses the meson summary block into real counters, persists
        the verdict to build_folder/upstream_test_result.json and prints
        the HMBS_UPSTREAM_TEST_RESULT evidence marker. Any non-passed
        outcome (failures, skips, zero executed, unparsable summary) raises
        loudly instead of faking a pass.
        """
        _meson = shutil.which("meson")
        if not _meson:
            raise ConanException("[dav2d] meson not found; cannot run upstream tests")
        _cmd = [_meson, "test", "-C", self.build_folder, "--print-errorlogs"]
        _proc = subprocess.Popen(_cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 env=os.environ, bufsize=1)
        _lines = []
        for _line in _proc.stdout:
            _lines.append(_line)
            print(_line, end="", flush=True)
        _proc.wait()
        _out = "".join(_lines)

        _sums = {}
        for _m in re.finditer(
                r"^\s*(Ok|Expected Fail|Fail|Unexpected Pass|Skipped|Timeout):\s+(\d+)",
                _out, re.M):
            _sums[_m.group(1)] = _sums.get(_m.group(1), 0) + int(_m.group(2))
        if not _sums:
            raise ConanException(
                "[dav2d] meson test summary not found (exit=%d); cannot "
                "produce HMBS_UPSTREAM_TEST_RESULT" % _proc.returncode)
        _ok = _sums.get("Ok", 0)
        _fail = _sums.get("Fail", 0) + _sums.get("Timeout", 0) + _sums.get("Unexpected Pass", 0)
        _skip = _sums.get("Skipped", 0)
        _exp = _sums.get("Expected Fail", 0)
        _discovered = _ok + _fail + _skip + _exp
        _executed = _discovered - _skip
        _status = ("passed" if (_proc.returncode == 0 and _fail == 0
                                and _skip == 0 and _executed > 0
                                and _executed == _discovered)
                   else "failed")
        _result = {
            "status": _status,
            "framework": "meson",
            "command": " ".join(_cmd),
            "discovered": _discovered,
            "executed": _executed,
            "passed": _ok,
            "failed": _fail,
            "skipped": _skip,
        }
        _jf = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(_jf, "w", encoding="utf-8") as _f:
            json.dump(_result, _f)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_result), flush=True)
        if _status != "passed":
            raise ConanException(
                "[dav2d] upstream tests not passed: %s" % json.dumps(_result))

    def _patch_meson_machine_files(self):
        """OHOS fixes for Conan-generated Meson machine files.

        1. Compiler wrappers arrive as shell scripts on OHOS runners; Meson
           cannot execute them directly, so wrap them as [shell, compiler].
        2. clock_gettime/CLOCK_MONOTONIC stay hidden under plain C99 on musl
           unless POSIX macros are set; Meson's has_function probe for
           clock_gettime would fail the whole configure. Add
           -D_POSIX_C_SOURCE=200809L (proven by the libdav1d 1.5.4 port).
        3. The OHOS clang wrapper injects linker-only flags; Meson
           compile-only probes add -Werror=unused-command-line-argument, so
           add -Qunused-arguments to keep feature probes honest.
        4. Conan's MesonToolchain omits ar/ranlib from the native file while
           Meson looks up a bare llvm-ar; inject the absolute paths derived
           from the C compiler location.
        """
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        wrapper_binaries = {}
        if str(self.settings.os) == "OHOS":
            for key in ("c", "cpp"):
                compiler = compiler_exes.get(key)
                if compiler and self._is_shell_script(compiler):
                    wrapper_binaries[key] = "[{}, {}]".format(
                        self._meson_quote(shell),
                        self._meson_quote(compiler),
                    )

        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            cc = compiler_exes.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate

        for name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            if str(self.settings.os) == "OHOS":
                for arg in ("-D_POSIX_C_SOURCE=200809L", "-Qunused-arguments"):
                    content = self._append_meson_builtin_array_option(content, "c_args", arg)
            if ar and "\nar =" not in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
                content = content.replace("[binaries]\n", insertion, 1)
            for key, value in wrapper_binaries.items():
                content = self._replace_meson_binary(content, key, value)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    @staticmethod
    def _is_shell_script(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(32).startswith(b"#!")
        except OSError:
            return False

    @staticmethod
    def _meson_quote(value):
        return "'{}'".format(value.replace("\\", "/").replace("'", "\\'"))

    @staticmethod
    def _replace_meson_binary(content, key, value):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("%s = " % key):
                lines[index] = "%s = %s" % (key, value)
                break
        trailing_newline = "\n" if content.endswith("\n") else ""
        return "\n".join(lines) + trailing_newline

    @classmethod
    def _append_meson_builtin_array_option(cls, content, option, value):
        quoted = cls._meson_quote(value)
        trailing_newline = "\n" if content.endswith("\n") else ""
        lines = content.splitlines()
        section_start = None
        for index, line in enumerate(lines):
            if line.strip() == "[built-in options]":
                section_start = index
                break
        if section_start is None:
            prefix = "\n" if content and not content.endswith("\n") else ""
            return "{}{}[built-in options]\n{} = [{}]\n".format(
                content, prefix, option, quoted)
        section_end = len(lines)
        for index in range(section_start + 1, len(lines)):
            stripped = lines[index].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section_end = index
                break
        for index in range(section_start + 1, section_end):
            line = lines[index]
            if not line.strip().startswith("%s =" % option):
                continue
            if quoted in line:
                return "\n".join(lines) + trailing_newline
            before, separator, after = line.rpartition("]")
            if not separator:
                continue
            if before.rstrip().endswith("["):
                lines[index] = before + quoted + separator + after
            else:
                lines[index] = before + ", " + quoted + separator + after
            return "\n".join(lines) + trailing_newline
        lines.insert(section_end, "{} = [{}]".format(option, quoted))
        return "\n".join(lines) + trailing_newline

    def _copy_shared_library_aliases(self):
        """Meson install may skip versioned .so symlinks on this worker.

        Consumers link -ldav2d and load libdav2d.so at runtime, so materialize
        every alias (libdav2d.so, libdav2d.so.<major>, ...) as a real copy of
        the versioned file. (Same worker limitation hit by libdav1d 1.5.4.)
        """
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for name in os.listdir(lib_dir):
            if ".so." not in name:
                continue
            source = os.path.join(lib_dir, name)
            if not os.path.isfile(source):
                continue
            prefix, version = name.split(".so.", 1)
            aliases = ["{}.so".format(prefix)]
            version_parts = version.split(".")
            aliases.extend(
                "{}.so.{}".format(prefix, ".".join(version_parts[:index]))
                for index in range(1, len(version_parts))
            )
            for alias in aliases:
                target = os.path.join(lib_dir, alias)
                if not os.path.exists(target):
                    shutil.copy2(source, target)

    def _sign_ohos_package_elfs(self):
        objcopy = self._resolve_tool("llvm-objcopy")
        signer = self._resolve_tool("binary-sign-tool")
        if not objcopy or not signer:
            return
        for root_dir in ("lib", "bin"):
            scan_root = os.path.join(self.package_folder, root_dir)
            if not os.path.isdir(scan_root):
                continue
            self._sign_ohos_elfs_in_directory(scan_root, objcopy, signer)

    def _sign_ohos_elfs_in_directory(self, scan_root, objcopy, signer):
        """XPM requires dlopen'ed .so files to be code-signed on HarmonyOS PC.

        Re-sign in place (via a .signed sidecar + os.replace to keep file
        modes intact); the toolchain's own signature does not survive the
        Conan install copy. (Same handling as libdav1d 1.5.4.)
        """
        for root, _, filenames in os.walk(scan_root):
            for filename in sorted(filenames):
                path = os.path.join(root, filename)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                mode = os.stat(path).st_mode
                signed_path = path + ".signed"
                self.run("{} 2>/dev/null || true".format(
                    shlex.join([objcopy, "--remove-section", ".codesign", path])
                ))
                self.run(shlex.join([
                    signer, "sign", "-inFile", path,
                    "-outFile", signed_path, "-selfSign", "1",
                ]))
                os.replace(signed_path, path)
                os.chmod(path, mode)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resolve_tool(self, name):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compiler_exes.get("c") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        candidates = [
            os.environ.get(name.upper().replace("-", "_")),
            shutil.which(name),
            os.path.join(compiler_dir, name) if compiler_dir else None,
            os.path.join("/data/service/hnp/bin", name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""
