#!/usr/bin/env python3
"""Conan recipe for libnpupnp 6.2.3 (Meson).

libnpupnp is the UPnP SDK fork used by upmpdcli (framagit medoc92/npupnp).
Upstream builds with Meson, depends on libcurl + libmicrohttpd + threads,
and ships four test programs under test/ (built with -Dtestmains=true).
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibnpupnpConan(ConanFile):
    name = "libnpupnp"
    version = "6.2.3"
    description = "Another SDK for UPnP Devices (C++ fork used by upmpdcli)"
    license = "BSD-3-Clause"
    homepage = "https://framagit.org/medoc92/npupnp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libnpupnp requires a POSIX-like target (Linux or OHOS), "
                "got {}".format(self.settings.os)
            )

    def requirements(self):
        self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)
        self.requires(
            "libmicrohttpd/1.0.1", transitive_headers=True, transitive_libs=True
        )

    def build_requirements(self):
        # Preflight/CI workers have no system pkg-config on PATH (HMBS only
        # injects cmake/make/ninja/python3); without it meson cannot resolve
        # the libcurl/libmicrohttpd .pc files emitted by PkgConfigDeps and
        # dies with "Dependency 'libcurl' is required but not found".
        # Pull pkgconf from ohpcd like fcft/3.3.3 and gulkan/0.15.1 do.
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        # framagit.org tarball timed out on every preflight attempt
        # (ConnectTimeout to port 443, 3/3 attempts failed), and no
        # byte-identical mirror exists on another host, so the recipe
        # uses the author's canonical release tarball on
        # lesbonscomptes.com (same source tree, single top-level dir,
        # COPYING + meson.build + test/meson.build present). It is the
        # SRC_URI used by Gentoo/Alpine/Void/Arch; the sha512 of the
        # file (ed8ed5d1...) matches the Gentoo Manifest entry for
        # libnpupnp-6.2.3.tar.gz (468168 bytes). get() is still
        # retried so a transient truncation restarts clean instead of
        # failing the whole create.
        data = dict(self.conan_data["sources"])
        last_exc = None
        for attempt in range(1, 4):
            try:
                get(self, **data, strip_root=True)
                return
            except ConanException as exc:
                last_exc = exc
                self.output.warning(
                    "source download attempt {}/3 failed: {}".format(
                        attempt, exc
                    )
                )
                self._clean_partial_source()
        raise last_exc

    def _clean_partial_source(self):
        """Remove partially extracted files so a retry starts clean."""
        folder = self.source_folder
        if not folder or not os.path.isdir(folder):
            return
        for entry in os.listdir(folder):
            full = os.path.join(folder, entry)
            try:
                if os.path.isdir(full) and not os.path.islink(full):
                    shutil.rmtree(full, ignore_errors=True)
                else:
                    os.remove(full)
            except OSError:
                pass

    def generate(self):
        self._ensure_writable_tmp()
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # expat support is optional upstream ("feature" option); keep the
        # default off so the recipe does not gain an extra dependency.
        tc.project_options["expat"] = "disabled"
        # Build the four upstream test programs under test/ and run them
        # with `meson test` in build().
        tc.project_options["testmains"] = "true"
        # Wire the pkg-config binary explicitly: the ohpcd pkgconf package
        # installs bin/pkgconf only (no bin/pkg-config alias by design) and
        # preflight workers have no system pkg-config on PATH, so meson
        # cannot resolve the PkgConfigDeps .pc files (libcurl, libmicrohttpd)
        # unless [binaries] points at a real executable.
        pkg_config = self._resolve_pkg_config()
        if pkg_config:
            tc.binaries["pkg-config"] = pkg_config
        tc.generate()
        self._repair_meson_machine_files()

    def _resolve_tool(self, name, extra_dirs=()):
        # Return an executable tool path that really exists on this machine.
        # The OHOS profile pins absolute DevBox paths
        # (tools.build:compiler_executables). When a preflight worker does
        # not provide that exact path, meson setup dies with
        # Unknown compiler(s) ... No such file or directory. Probe order:
        # profile conf value, PATH lookup, well-known DevBox locations.
        # A candidate is accepted only if it exists and --version runs
        # (this also catches a present-but-unloadable binary whose ELF
        # interpreter or shared libs are missing, which exec reports as
        # ENOENT as well).
        candidates = []
        executables = self.conf.get(
            'tools.build:compiler_executables', default={}, check_type=dict
        ) or {}
        configured = executables.get(name)
        if configured:
            candidates.append(configured)
        found = shutil.which(name)
        if found and found not in candidates:
            candidates.append(found)
        for directory in extra_dirs:
            candidate = os.path.join(directory, name)
            if candidate not in candidates:
                candidates.append(candidate)
        probed = []
        for candidate in candidates:
            if not candidate or not os.path.isfile(candidate):
                probed.append(
                    '{} (missing)'.format(candidate or '<empty>')
                )
                continue
            try:
                proc = subprocess.run(
                    [candidate, '--version'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                probed.append('{} (not runnable: {})'.format(candidate, exc))
                continue
            if proc.returncode == 0:
                if candidate != configured:
                    self.output.info(
                        'Using {} {} (profile value {} unavailable)'.format(
                            name, candidate, configured
                        )
                    )
                return candidate
            probed.append(
                '{} (--version rc={})'.format(candidate, proc.returncode)
            )
        raise ConanException(
            'No runnable {} found on this machine; probed: {}. '.format(
                name, '; '.join(probed)
            )
            + 'The profile compiler path is missing on this worker.'
        )

    def _ensure_writable_tmp(self):
        # HMBS injects TMPDIR/TMP/TEMP pointing at a writable per-task dir
        # because the worker root /tmp is read-only. Export the first
        # writable candidate to os.environ at generate() time (before
        # MesonToolchain/meson create temp files) and to all three vars so
        # meson, ninja and the compiler driver agree on one location.
        candidates = []
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var)
            if val and val not in candidates:
                candidates.append(val)
        candidates.append(os.path.join(self.build_folder or "", "tmp-fallback"))
        chosen = ""
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(probe)
                chosen = cand
                break
            except OSError:
                continue
        if chosen:
            for var in ("TMPDIR", "TMP", "TEMP"):
                os.environ[var] = chosen
            self.output.info("Using writable tmpdir {}".format(chosen))
        else:
            self.output.warning("No writable tmpdir found; build may hit read-only /tmp")

    def _resolve_archiver(self, kind, bindir=""):
        # Resolve ar/ranlib/strip without assuming one basename. The OHOS
        # profile pins /data/service/hnp/bin/llvm-ar, but a preflight worker
        # may only ship harmonybrew clang + generic binutils (ar/ranlib) on
        # PATH. Probe profile value first, then every alias via PATH, then
        # bindir/devbox fallbacks. A candidate wins if --version runs; as a
        # last resort accept mere existence so meson gets a usable path
        # instead of a dangling absolute one.
        aliases = {
            "ar": ("llvm-ar", "ar"),
            "ranlib": ("llvm-ranlib", "ranlib"),
            "strip": ("llvm-strip", "strip"),
        }.get(kind, (kind,))
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidates = []
        configured = executables.get(kind)
        if configured and configured not in candidates:
            candidates.append(configured)
        for alias in aliases:
            found = shutil.which(alias)
            if found and found not in candidates:
                candidates.append(found)
        search_dirs = []
        if bindir:
            search_dirs.append(bindir)
        search_dirs.extend(("/data/service/hnp/bin", "/usr/bin"))
        for directory in search_dirs:
            for alias in aliases:
                cand = os.path.join(directory, alias)
                if cand not in candidates:
                    candidates.append(cand)
        probed = []
        fallback = ""
        for cand in candidates:
            if not cand or not os.path.isfile(cand):
                probed.append("{} (missing)".format(cand or "<empty>"))
                continue
            try:
                proc = subprocess.run(
                    [cand, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                probed.append("{} (not runnable: {})".format(cand, exc))
                continue
            if proc.returncode == 0:
                if cand != configured:
                    self.output.info(
                        "Using {} {} (profile value {} unavailable)".format(
                            kind, cand, configured
                        )
                    )
                return cand
            if not fallback:
                fallback = cand
            probed.append("{} (--version rc={})".format(cand, proc.returncode))
        if fallback:
            self.output.warning(
                "Using {} {} without --version handshake; probed: {}".format(
                    kind, fallback, "; ".join(probed)
                )
            )
            return fallback
        self.output.warning(
            "No runnable {} found; probed: {}".format(kind, "; ".join(probed))
        )
        return ""

    def _resolve_pkg_config(self):
        # Locate a runnable pkg-config compatible binary. Probe order:
        # explicit conf, conan pkgconf tool package (bin/pkgconf, no
        # pkg-config alias by design), then PATH names. The winner must
        # exist and answer --version; meson executes whatever path the
        # [binaries] pkg-config entry holds, so a pkgconf binary works.
        candidates = []
        configured = self.conf.get(
            "tools.gnu:pkg_config", default=None, check_type=str
        )
        if configured and configured not in candidates:
            candidates.append(configured)
        try:
            build_deps = self.dependencies.build
        except Exception:
            build_deps = {}
        try:
            pkgconf_dep = build_deps["pkgconf"] if build_deps else None
        except Exception:
            pkgconf_dep = None
        if pkgconf_dep is not None:
            try:
                folder = pkgconf_dep.package_folder
            except Exception:
                folder = ""
            if folder:
                cand = os.path.join(folder, "bin", "pkgconf")
                if cand not in candidates:
                    candidates.append(cand)
        for name in ("pkg-config", "pkgconf"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)
        probed = []
        for cand in candidates:
            if not cand or not os.path.isfile(cand):
                probed.append("{} (missing)".format(cand or "<empty>"))
                continue
            try:
                proc = subprocess.run(
                    [cand, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                probed.append("{} (not runnable: {})".format(cand, exc))
                continue
            if proc.returncode == 0:
                if cand != configured:
                    self.output.info(
                        "Using pkg-config {} (conf value {} unavailable)".format(
                            cand, configured
                        )
                    )
                return cand
            probed.append("{} (--version rc={})".format(cand, proc.returncode))
        self.output.warning(
            "No runnable pkg-config found; probed: {}".format(
                "; ".join(probed)
            )
        )
        return ""

    def _repair_meson_machine_files(self):
        # Single machine-file repair covering both value shapes Meson accepts:
        #   ar = '/path/llvm-ar'        (string form)
        #   ar = ['/path/llvm-ar']      (list form, used by MesonToolchain)
        # The previous fix only matched the string form, so archiver lines in
        # list form were never rewritten and meson kept dying on the dangling
        # /data/service/hnp/bin/llvm-ar. Here the whole right-hand side is
        # captured and every quoted absolute path inside it is rebound.
        devbox = "/data/service/hnp/bin"
        c = self._resolve_tool("clang", extra_dirs=(devbox, "/usr/bin"))
        cpp = self._resolve_tool("clang++", extra_dirs=(devbox, "/usr/bin"))
        bindir = os.path.dirname(c) if os.path.isabs(c) else ""
        wanted = {"c": c, "cpp": cpp}
        for kind in ("ar", "ranlib", "strip"):
            resolved = self._resolve_archiver(kind, bindir=bindir)
            if resolved:
                wanted[kind] = resolved
        wanted["pkg-config"] = self._resolve_pkg_config() or wanted.get(
            "pkg-config", ""
        )
        # c_ld/cpp_ld stay on the verified C/C++ drivers when the profile
        # value is missing; they are handled as path swaps below.
        for key in ("c_ld", "cpp_ld"):
            driver = c if key == "c_ld" else cpp
            if driver:
                wanted[key] = driver
        line_pattern = re.compile(r"(?m)^(\s*[A-Za-z0-9_-]+\s*=\s*)(.+)$")
        quoted_pattern = re.compile(r"'([^']*)'|\"([^\"]*)\"")
        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            original = content
            lines = content.splitlines(keepends=True)
            in_binaries = False
            seen_keys = set()
            out_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("["):
                    in_binaries = stripped == "[binaries]"
                    out_lines.append(line)
                    continue
                if not in_binaries:
                    out_lines.append(line)
                    continue
                match = line_pattern.match(line)
                if not match:
                    out_lines.append(line)
                    continue
                key_match = re.match(r"\s*([A-Za-z0-9_-]+)", line)
                key = key_match.group(1) if key_match else ""
                if key not in ("c", "cpp", "c_ld", "cpp_ld", "ar", "ranlib", "strip", "pkg-config", "pkgconf"):
                    out_lines.append(line)
                    continue
                seen_keys.add(key)
                prefix, value = match.group(1), match.group(2)

                def _is_abs(text):
                    return os.path.isabs(text) or text.startswith("/")

                state = {"done_compiler": False}

                def _swap_quoted(qmatch):
                    text = qmatch.group(1) if qmatch.group(1) is not None else qmatch.group(2)
                    quote = "'" if qmatch.group(1) is not None else '"'
                    if key in ("c", "cpp", "c_ld", "cpp_ld"):
                        # Only the first quoted entry is the executable;
                        # later entries are compiler flags and must be kept.
                        if key in wanted and not state["done_compiler"]:
                            state["done_compiler"] = True
                            return quote + wanted[key] + quote
                        return qmatch.group(0)
                    if key in ("ar", "ranlib", "strip"):
                        if key in wanted:
                            if not text or (_is_abs(text) and not os.path.isfile(text)):
                                return quote + wanted[key] + quote
                            if _is_abs(text) and bindir:
                                relocated = os.path.join(bindir, os.path.basename(text))
                                if os.path.isfile(relocated):
                                    return quote + relocated + quote
                            return qmatch.group(0)
                    if key in ("pkg-config", "pkgconf"):
                        want = wanted.get("pkg-config", "")
                        if want:
                            if not text or (_is_abs(text) and not os.path.isfile(text)):
                                return quote + want + quote
                            if text in ("pkg-config", "pkgconf") and not shutil.which(text):
                                return quote + want + quote
                        return qmatch.group(0)
                    if _is_abs(text) and not os.path.isfile(text) and bindir:
                        relocated = os.path.join(bindir, os.path.basename(text))
                        if os.path.isfile(relocated):
                            return quote + relocated + quote
                    return qmatch.group(0)

                new_value = quoted_pattern.sub(_swap_quoted, value.rstrip("\r\n"))
                if line.endswith("\r\n"):
                    out_lines.append(prefix + new_value + "\r\n")
                elif line.endswith("\n"):
                    out_lines.append(prefix + new_value + "\n")
                else:
                    out_lines.append(prefix + new_value)
            content = "".join(out_lines)
            # Insert missing archiver entries so meson never falls back to a
            # bare name that is absent from PATH on the worker.
            if "[binaries]" in content:
                missing = [k for k in ("ar", "ranlib") if k not in seen_keys and k in wanted]
                if wanted.get("pkg-config") and "pkg-config" not in seen_keys and "pkgconf" not in seen_keys:
                    missing.append("pkg-config")
                if missing:
                    insert = "".join("{} = '{}'\n".format(k, wanted[k]) for k in missing)
                    content = content.replace("[binaries]\n", "[binaries]\n" + insert, 1)
            if content != original:
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
                self.output.info("Repaired toolchain paths in {}".format(filename))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._meson_environment().vars(self).apply():
            meson.configure()
            meson.build()
            self._run_upstream_tests()

    def _meson_bindir(self):
        # Locate the meson tool package bindir so the custom `meson test`
        # invocation sees the same binary the Meson helper uses. Meson
        # configure/build succeed (helper resolves the tool internally)
        # while a bare `meson` on PATH fails with rc=127 because the recipe
        # never generated VirtualBuildEnv and _meson_environment() never
        # exposed the meson bindir.
        try:
            meson_dep = self.dependencies.build["meson"]
        except Exception:
            meson_dep = None
        if meson_dep is not None:
            try:
                folder = meson_dep.package_folder
            except Exception:
                folder = ""
            if folder:
                bindir = os.path.join(folder, "bin")
                if os.path.isdir(bindir):
                    return bindir
        return ""

    def _resolve_meson(self, extra_path=""):
        # Absolute meson executable: tool package first, then PATH
        # (PATH already contains the tool bindir when called after the
        # _meson_environment prepend below), never a bare name that
        # depends on worker-global PATH.
        candidates = []
        bindir = self._meson_bindir()
        if bindir:
            cand = os.path.join(bindir, "meson")
            if cand not in candidates:
                candidates.append(cand)
        if extra_path:
            for entry in extra_path.split(os.pathsep):
                cand = os.path.join(entry, "meson")
                if cand not in candidates:
                    candidates.append(cand)
        found = shutil.which("meson")
        if found and found not in candidates:
            candidates.append(found)
        candidates.append("meson")
        for cand in candidates:
            if cand != "meson" and not os.path.isfile(cand):
                continue
            try:
                proc = subprocess.run(
                    [cand, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if proc.returncode == 0:
                return cand
        return "meson"

    def _run_upstream_tests(self):
        """Run the four upstream test programs and emit the evidence marker.

        Parses the real `meson test` summary (Ok:/Fail: counters plus the
        per-test "OK" lines) so the HMBS_UPSTREAM_TEST_RESULT numbers come
        from the framework output, not from estimates.
        """
        test_env = dict(os.environ)
        test_env["LD_LIBRARY_PATH"] = ":".join(
            self._test_library_dirs(test_env.get("LD_LIBRARY_PATH", ""))
        )
        # Expose the meson tool bindir to the test subprocess (the outer
        # `with _meson_environment()` already put pkgconf/compiler bindirs
        # into os.environ, but nothing ever added meson, hence rc=127).
        meson_bindir = self._meson_bindir()
        if meson_bindir:
            old_path = test_env.get("PATH", "")
            entries = old_path.split(os.pathsep) if old_path else []
            if meson_bindir not in entries:
                test_env["PATH"] = meson_bindir + (
                    os.pathsep + old_path if old_path else ""
                )
        meson_bin = self._resolve_meson(test_env.get("PATH", ""))
        cmd = (
            'meson test -C "{}" --print-errorlogs'.format(self.build_folder)
        )
        argv = [meson_bin, "test", "-C", self.build_folder, "--print-errorlogs"]
        self.output.info(
            "Running upstream tests: {} (meson binary: {})".format(
                cmd, meson_bin
            )
        )
        proc = subprocess.run(
            argv,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
            env=test_env,
        )
        output = proc.stdout or ""
        self.output.info("meson test output:\n{}".format(output))
        ok_tests = re.findall(r"^\d+/\d+\s+\S+\s+OK", output, flags=re.M)
        fail_tests = re.findall(r"^\d+/\d+\s+\S+\s+FAIL", output, flags=re.M)
        passed = len(ok_tests)
        failed = len(fail_tests)
        summary_ok = re.search(r"^Ok:\s+(\d+)", output, flags=re.M)
        summary_fail = re.search(r"^Fail:\s+(\d+)", output, flags=re.M)
        if summary_ok is not None:
            passed = int(summary_ok.group(1))
        if summary_fail is not None:
            failed = int(summary_fail.group(1))
        executed = passed + failed
        discovered = 4  # test_description, test_init, test_netif, test_url
        if executed == 0:
            # No test line was produced: treat as not-run, never as passed.
            marker = {
                "status": "failed",
                "framework": "meson",
                "command": cmd,
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
            )
            raise ConanException(
                "meson test produced no test results (rc={})".format(
                    proc.returncode
                )
            )
        status = (
            "passed"
            if (proc.returncode == 0 and failed == 0 and executed == discovered)
            else "failed"
        )
        marker = {
            "status": status,
            "framework": "meson",
            "command": cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": discovered - executed,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if status != "passed":
            raise ConanException(
                "upstream meson tests failed "
                "(passed={} failed={} rc={})".format(
                    passed, failed, proc.returncode
                )
            )

    def package(self):
        with self._meson_environment().vars(self).apply():
            Meson(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self.options.shared and str(self.settings.os) == "OHOS":
            self._materialize_shared_aliases()
            self._sign_shared_libraries()

    def package_info(self):
        # Meson: library('libnpupnp', ..., name_prefix: '') installs the file
        # libnpupnp.so, so the link name without the 'lib' prefix is 'npupnp'
        # ('-lnpupnp' finds libnpupnp.so). Using ["libnpupnp"] makes CMakeDeps
        # look for liblibnpupnp.so and fail with "Library 'libnpupnp' not
        # found in package".
        self.cpp_info.libs = ["npupnp"]
        self.cpp_info.includedirs = ["include", "include/npupnp"]
        self.cpp_info.requires = [
            "curl::curl",
            "libmicrohttpd::libmicrohttpd",
        ]
        self.cpp_info.set_property("cmake_file_name", "libnpupnp")
        self.cpp_info.set_property("cmake_target_name", "libnpupnp::libnpupnp")
        self.cpp_info.set_property("pkg_config_name", "libnpupnp")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]

    def _test_library_dirs(self, current):
        libdirs = []
        for dep in self.dependencies.values():
            try:
                libdirs.extend(dep.cpp_info.libdirs)
            except Exception:
                continue
        if current:
            libdirs.append(current)
        seen = set()
        result = []
        for item in libdirs:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _meson_environment(self):
        """Conan-scoped environment for Meson, pkg-config and the toolchain."""
        environment = Environment()
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        meson_bindir = self._meson_bindir()
        if meson_bindir and os.path.isdir(meson_bindir):
            environment.prepend_path("PATH", meson_bindir)
        try:
            pkgconf_dep = self.dependencies.build["pkgconf"]
        except Exception:
            pkgconf_dep = None
        if pkgconf_dep is not None:
            try:
                pkgconf_bindir = os.path.join(
                    pkgconf_dep.package_folder, "bin"
                )
            except Exception:
                pkgconf_bindir = ""
            if pkgconf_bindir and os.path.isdir(pkgconf_bindir):
                environment.prepend_path("PATH", pkgconf_bindir)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            environment.prepend_path("PATH", bindir)
        # Forward the HMBS-provided writable temp dirs into the build
        # environment so meson/ninja do not fall back to a read-only /tmp.
        for tmpvar in ('TMPDIR', 'TMP', 'TEMP'):
            tmpval = os.environ.get(tmpvar)
            if tmpval:
                environment.define(tmpvar, tmpval)
        return environment

    def _materialize_shared_aliases(self):
        """Replace versioned .so symlinks with real copies (HMFS-safe)."""
        library_dir = os.path.join(self.package_folder, "lib")
        versioned = sorted(
            path
            for path in glob.glob(os.path.join(library_dir, "libnpupnp.so.*"))
            if os.path.isfile(path) and not os.path.islink(path)
        )
        if not versioned:
            raise ConanException(
                "installed libnpupnp shared object is missing in {}".format(
                    library_dir
                )
            )
        source = versioned[-1]
        for alias in (
            os.path.join(library_dir, "libnpupnp.so.13"),
            os.path.join(library_dir, "libnpupnp.so"),
        ):
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copy2(source, alias)

    def _resolve_ohos_tool(self, name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = executables.get(name) or executables.get(
            name.replace("-", "_")
        )
        compiler = executables.get("c") or executables.get("cpp") or ""
        compiler_dir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        candidates = [configured, shutil.which(name)]
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._resolve_ohos_tool("llvm-objcopy")
        signer = self._resolve_ohos_tool("binary-sign-tool")
        missing = [
            name
            for name, path in (
                ("llvm-objcopy", objcopy),
                ("binary-sign-tool", signer),
            )
            if not path
        ]
        if missing:
            raise ConanException(
                "OHOS shared-library packaging requires " + ", ".join(missing)
            )
        targets = sorted(
            glob.glob(os.path.join(self.package_folder, "lib", "libnpupnp.so*"))
        )
        for path in targets:
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            signed_path = path + ".signed"
            if os.path.exists(signed_path):
                os.remove(signed_path)
            mode = os.stat(path).st_mode
            self.run(
                shlex.join([objcopy, "--remove-section", ".codesign", path])
            )
            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        path,
                        "-outFile",
                        signed_path,
                        "-selfSign",
                        "1",
                    ]
                )
            )
            os.replace(signed_path, path)
            os.chmod(path, mode)
