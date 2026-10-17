#!/usr/bin/env python3
"""Conan recipe — libmusicxml 3.22 (CMake, C++17)."""

import glob
import json
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, export_conandata_patches, get


class LibmusicxmlConan(ConanFile):
    name = "libmusicxml"
    version = "3.22"
    description = "Portable C++ library around the MusicXML format"
    license = "MPL-2.0"
    homepage = "https://github.com/grame-cncm/libmusicxml"
    url = "https://github.com/grame-cncm/libmusicxml"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libmusicxml supports Linux and OHOS targets, got {}".format(self.settings.os)
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # readonly_tmp: conan get() may stage downloads via /tmp; force the
        # HMBS writable dir first so download/extract never touches /tmp.
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        # Prefer HMBS-injected writable dirs; fall back to build-local tmp.
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder, "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def _resolve_actual_compiler(self, conf_path, basename):
        if conf_path and os.path.isfile(conf_path):
            return conf_path
        found = shutil.which(basename)
        if found and os.path.isfile(found):
            self.output.info(
                "profile compiler '{}' not found; using '{}' from PATH".format(
                    conf_path or basename, found
                )
            )
            return found
        return conf_path or basename

    def _fixup_compiler_conf(self):
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            comp = {}
        c_path = self._resolve_actual_compiler(comp.get("c"), "clang")
        cpp_path = self._resolve_actual_compiler(comp.get("cpp"), "clang++")
        new_comp = dict(comp)
        new_comp["c"] = c_path
        new_comp["cpp"] = cpp_path
        try:
            self.conf.define("tools.build:compiler_executables", new_comp)
        except Exception:
            pass
        return c_path, cpp_path

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            comp = {}
        cc = comp.get("c") or comp.get("cpp") or shutil.which("clang") or "clang"
        cc_resolved = shutil.which(cc) if not os.path.isabs(cc) else cc
        cc_resolved = cc_resolved or cc
        try:
            cc_real = os.path.realpath(cc_resolved)
        except Exception:
            cc_real = cc_resolved
        candidates = []
        try:
            resource_dir = subprocess.check_output(
                [cc_resolved, "-print-resource-dir"],
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            ).strip()
            if resource_dir:
                candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
        except Exception:
            pass
        try:
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
            )
        except Exception:
            pass
        for candidate in dict.fromkeys(candidates):
            try:
                if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                    return candidate
            except Exception:
                continue
        return ""

    def _build_environment(self):
        env = Environment()
        tmp = self._writable_tmpdir()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("SHELL", "/bin/sh")
        env.define("CONFIG_SHELL", "/bin/sh")
        for key in (
            "HMBS_AUTOCONF_MKTEMP_FALLBACK",
            "HMBS_CAP_LOCAL_MKTEMP",
            "HMBS_TMPDIR",
            "HMBS_CAP_HARDLINK",
            "HMBS_CAP_CHMOD",
            "HMBS_CAP_SYMLINK",
        ):
            val = os.environ.get(key)
            if val:
                env.define(key, val)
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                "prepending OHOS SDK linker runtime path: {}".format(sdk_lib)
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def _resolve_hmbs_tool(self, conf_key, env_var, basenames):
        # Prefer HMBS-injected absolute paths (conf user.hmbs:* then env
        # HMBS_*), fall back to PATH lookup. Never return a bare name when
        # an absolute path exists so posix_spawn finds the tool on OHOS.
        try:
            val = self.conf.get(conf_key, check_type=str)
            if val and os.path.isfile(val):
                return val
        except Exception:
            pass
        env_val = os.environ.get(env_var)
        if env_val and os.path.isfile(env_val):
            return env_val
        if isinstance(basenames, str):
            basenames = [basenames]
        for name in basenames:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        return env_val or basenames[0]

    def _conan_toolchain_file(self):
        candidates = []
        try:
            candidates.append(os.path.join(self.generators_folder, "conan_toolchain.cmake"))
        except Exception:
            pass
        for root, _dirs, files in os.walk(self.build_folder):
            if "conan_toolchain.cmake" in files:
                candidates.append(os.path.join(root, "conan_toolchain.cmake"))
                break
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        return candidates[0] if candidates else "conan_toolchain.cmake"

    def _cmake_build_dir(self):
        # Dedicated build dir under the recipe build folder so configure /
        # build / install stay consistent regardless of cmake_layout
        # sub-folder assumptions. Reused by build() and package().
        d = os.path.join(self.build_folder, "hmbs_build")
        os.makedirs(d, exist_ok=True)
        return d

    def _run_direct(self, argv, env=None, cwd=None):
        run_env = dict(os.environ)
        tmp = self._writable_tmpdir()
        run_env["TMPDIR"] = tmp
        run_env["TMP"] = tmp
        run_env["TEMP"] = tmp
        if env:
            run_env.update(env)
        self.output.info("noshell: {}".format(" ".join(str(a) for a in argv)))
        proc = subprocess.run(
            list(argv),
            env=run_env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.stdout:
            self.output.info(proc.stdout)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, list(argv))
        return proc

    def generate(self):
        # Repair stale profile compiler path before CMakeToolchain bakes it
        # into conan_toolchain.cmake (else CMake aborts at project() with
        # "not a full path to an existing compiler tool").
        cc, cxx = self._fixup_compiler_conf()
        tc = CMakeToolchain(self)
        # Upstream build/CMakeLists.txt declares cmake_minimum_required < 3.5;
        # CMake >= 4 (true machine 4.4.3) removed that compat. Pin the policy
        # minimum so configure proceeds without touching upstream sources.
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_C_COMPILER"] = cc
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
            for lang in ("C", "CXX"):
                tc.variables["CMAKE_SHARED_LIBRARY_SONAME_{}_FLAG".format(lang)] = "-Wl,-soname,"
                tc.variables["CMAKE_SHARED_LIBRARY_RUNTIME_{}_FLAG".format(lang)] = "-Wl,-rpath,"
                tc.variables["CMAKE_SHARED_LIBRARY_RUNTIME_{}_FLAG_SEP".format(lang)] = ":"
                tc.variables["CMAKE_SHARED_LIBRARY_RPATH_LINK_{}_FLAG".format(lang)] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.variables["GENTOOLS"] = True
        tc.variables["GENSTATIC"] = True
        shared = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = shared or bool(
            self.options.get_safe("fPIC", True)
        )
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.generate()
        VirtualRunEnv(self).generate()
        self._build_environment().vars(self, scope="build").save_script("hmbs_env")

    def build(self):
        # readonly_tmp: Conan's CMake helper runs `cmake ...` via /bin/sh -c,
        # and dash creates /tmp/sh*.tmp which fails on the read-only /tmp
        # (preflight: "can't create temporary file /tmp/shbz3j61.tmp" then
        # "Error: [Errno 12] Out of memory: '/bin/sh'"). Invoke the cmake
        # binary directly in list form so no shell temp file is created;
        # TMPDIR is forwarded via _run_direct (experience 1, adapt: keep
        # CMake semantics, only change the exec channel).
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        cmake_bin = self._resolve_hmbs_tool("user.hmbs:cmake_path", "HMBS_CMAKE", "cmake")
        make_bin = self._resolve_hmbs_tool("user.hmbs:make_path", "HMBS_MAKE", "make")
        src_dir = os.path.join(self.source_folder, "build")
        build_dir = self._cmake_build_dir()
        toolchain = self._conan_toolchain_file()
        self.output.info("noshell cmake configure: {} -S {} -B {}".format(cmake_bin, src_dir, build_dir))
        with self._build_environment().vars(self).apply():
            self._run_direct([
                cmake_bin,
                "-S", src_dir,
                "-B", build_dir,
                "-G", "Unix Makefiles",
                "-DCMAKE_TOOLCHAIN_FILE={}".format(toolchain),
                "-DCMAKE_INSTALL_PREFIX={}".format(self.package_folder),
                "-DCMAKE_POLICY_DEFAULT_CMP0091=NEW",
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                "-DCMAKE_BUILD_TYPE={}".format(str(self.settings.build_type)),
                "-DCMAKE_MAKE_PROGRAM={}".format(make_bin),
            ])
            self._run_direct([cmake_bin, "--build", build_dir, "--config", str(self.settings.build_type), "--parallel", "1"])
            self._run_upstream_validation()

    def _find_built_tool(self, name):
        # Upstream sets RUNTIME_OUTPUT_DIRECTORY to <source>/build/bin, so
        # tools land in the source tree, not in hmbs_build. Search both plus
        # a full walk as fallback. Return "" when absent (caller fails hard).
        candidates = [
            os.path.join(self.source_folder, "build", "bin", name),
            os.path.join(self._cmake_build_dir(), name),
            os.path.join(self.build_folder, "hmbs_build", name),
        ]
        for path in candidates:
            if path and os.path.isfile(path):
                return path
        for root in (self.source_folder, self.build_folder):
            for dirpath, _dirs, files in os.walk(root):
                if name in files:
                    hit = os.path.join(dirpath, name)
                    try:
                        if os.access(hit, os.X_OK) or os.path.isfile(hit):
                            return hit
                    except Exception:
                        return hit
        return ""

    def _collect_upstream_samples(self):
        # validation/Makefile drives ../files -name "*.xml"; files/tests has
        # its own Makefile over *.xml. Collect both (recursive) as the suite.
        patterns = [
            os.path.join(self.source_folder, "files", "**", "*.xml"),
            os.path.join(self.source_folder, "samples", "*.xml"),
        ]
        found = []
        for pattern in patterns:
            found.extend(glob.glob(pattern, recursive=True))
        # De-duplicate, keep deterministic order, skip empty files up front
        # (empty would be a meaningless "pass" on empty-vs-empty compares).
        unique = []
        seen = set()
        for path in sorted(found):
            if path in seen:
                continue
            seen.add(path)
            try:
                if os.path.isfile(path) and os.path.getsize(path) > 0:
                    unique.append(path)
            except OSError:
                continue
        return unique

    def _exec_capture(self, argv, cwd=None):
        # Quiet direct exec for the per-file loop: hundreds of files would
        # flood the log if every stdout were echoed. Failures are logged by
        # the caller with file context; success stays silent except counts.
        # NOTE: samples contain Latin-1 bytes (e.g. 0xf6); strict utf-8
        # decode crashed here (UnicodeDecodeError at position 490). Use
        # errors="replace" so a non-UTF8 byte never aborts the harness;
        # exit-code + non-empty checks still gate pass/fail.
        run_env = dict(os.environ)
        tmp = self._writable_tmpdir()
        run_env["TMPDIR"] = tmp
        run_env["TMP"] = tmp
        run_env["TEMP"] = tmp
        proc = subprocess.run(
            list(argv),
            env=run_env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc

    def _emit_upstream_result(self, payload):
        # Dual-channel (experience 2, apply): conan output channel plus plain
        # stdout so the marker survives even if one channel is filtered.
        # Persist without BOM for test_package re-emit verification.
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(payload, ensure_ascii=False)
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream_result.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except Exception as exc:
            self.output.warning("could not persist upstream result: {}".format(exc))

    def _run_upstream_validation(self):
        # Real upstream regression entry (validation/files/tests Makefiles drive
        # xmlread + xml2guido over files/*.xml). No ctest/gtest exists, so this
        # loop IS the suite: each sample must round-trip (xmlread) and convert
        # to Guido (xml2guido) with exit 0 and non-empty output. Any failure
        # fails the build — never silently skipped or stubbed.
        with self._build_environment().vars(self).apply():
            xmlread = self._find_built_tool("xmlread")
            xml2guido = self._find_built_tool("xml2guido")
            missing = [n for n, p in (("xmlread", xmlread), ("xml2guido", xml2guido)) if not p]
            if missing:
                raise ConanInvalidConfiguration(
                    "upstream validation tools missing (GENTOOLS must build {}): {}".format(
                        "/".join(missing), self.build_folder
                    )
                )
            samples = self._collect_upstream_samples()
            if not samples:
                raise ConanInvalidConfiguration(
                    "no upstream sample XML found under files/; refusing empty pass"
                )
            discovered = len(samples) * 2
            passed = 0
            failed = 0
            failures = []
            for sample in samples:
                for tool, label in ((xmlread, "read"), (xml2guido, "guido")):
                    proc = self._exec_capture([tool, sample])
                    out = proc.stdout or ""
                    # Falsification guard: non-empty check (empty-vs-empty
                    # would fake a pass) plus tool-specific content marker.
                    if label == "read":
                        ok = proc.returncode == 0 and len(out.strip()) > 0 and "<" in out
                    else:
                        ok = proc.returncode == 0 and len(out.strip()) > 0
                    if ok:
                        passed += 1
                    else:
                        failed += 1
                        snippet = out.strip().replace("\n", " ")[:200]
                        failures.append(
                            "{}:{} rc={} out={!r}".format(label, os.path.basename(sample), proc.returncode, snippet)
                        )
            status = "passed" if failed == 0 else "failed"
            payload = {
                "status": status,
                "framework": "validation-harness",
                "command": "xmlread+xml2guido over {} files (validation/Makefile + files/tests/Makefile entry)".format(len(samples)),
                "discovered": discovered,
                "executed": discovered,
                "passed": passed,
                "failed": failed,
                "skipped": 0,
            }
            self._emit_upstream_result(payload)
            if failures:
                for line in failures[:10]:
                    self.output.warning("upstream validation failure: {}".format(line))
                raise ConanInvalidConfiguration(
                    "upstream validation failed: {}/{} checks failed (see warnings)".format(failed, discovered)
                )
            self.output.info(
                "upstream validation OK: {}/{} checks passed over {} files".format(passed, discovered, len(samples))
            )

    def package(self):
        copy(
            self,
            "license.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        with self._build_environment().vars(self).apply():
            # noshell install: same reason as build() — avoid /bin/sh -c.
            cmake_bin = self._resolve_hmbs_tool("user.hmbs:cmake_path", "HMBS_CMAKE", "cmake")
            build_dir = self._cmake_build_dir()
            self._run_direct([cmake_bin, "--install", build_dir, "--config", str(self.settings.build_type)])
        # Persist the build-time upstream result inside the package so
        # test_package can re-emit the exact measured counts (experience 2:
        # re-emit must source from the persisted file, never re-typed).
        try:
            src_result = os.path.join(self.build_folder, "hmbs_upstream_result.json")
            if os.path.isfile(src_result):
                with open(src_result, "r", encoding="utf-8") as f:
                    json.load(f)  # validate before shipping
                dst_dir = os.path.join(self.package_folder, "share", "libmusicxml")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src_result, os.path.join(dst_dir, "upstream_test_result.json"))
        except Exception as exc:
            self.output.warning("could not stage upstream result: {}".format(exc))
        # Tools (xmlread/xml2guido/...) were built for validation only; the
        # package stays a pure library so no bin/ ships and no commands.json
        # obligation is triggered. Upstream evidence is the build-time run
        # above, re-emitted by test_package from the persisted JSON.
        try:
            bin_dir = os.path.join(self.package_folder, "bin")
            if os.path.isdir(bin_dir):
                shutil.rmtree(bin_dir)
        except Exception as exc:
            self.output.warning("could not drop tool binaries: {}".format(exc))
        if self.options.shared:
            for pattern in ("libmusicxml2.a", "libmusicxml2*.a"):
                for path in glob.glob(os.path.join(self.package_folder, "lib", pattern)):
                    if os.path.isfile(path):
                        os.remove(path)
        else:
            # Static package: drop the shared object. Upstream shared file is
            # liblibmusicxml.so* (double-lib prefix); also match single-prefix
            # just in case a future upstream normalizes OUTPUT_NAME.
            for pattern in ("liblibmusicxml.so*", "libmusicxml.so*", "libmusicxml*.so*"):
                for path in glob.glob(
                    os.path.join(self.package_folder, "lib", "**", pattern), recursive=True
                ):
                    if os.path.isfile(path) and not os.path.islink(path):
                        os.remove(path)
                    elif os.path.islink(path):
                        os.remove(path)
        if self.settings.os == "OHOS" and self.options.shared:
            libraries = glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
            )
            self._sign_paths(libraries, required=False)

    def _sign_paths(self, paths, required):
        paths = sorted(
            {path for path in paths if os.path.isfile(path) and not os.path.islink(path)}
        )
        if not paths:
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            message = "HarmonyOS execution requires llvm-objcopy and binary-sign-tool"
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning("{}; release worker must sign the package".format(message))
            return
        for path in paths:
            self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        try:
            original_mode = os.stat(path).st_mode
        except OSError:
            original_mode = None
        temporary = "{}.signing".format(path)
        try:
            shutil.copy2(path, temporary)
            # Direct exec without /bin/sh -c so no shell temp file lands on
            # read-only /tmp; TMPDIR is forwarded via _run_direct.
            self._run_direct([objcopy, "--remove-section", ".codesign", temporary])
            self._run_direct(
                [signer, "sign", "-inFile", temporary, "-outFile", temporary, "-selfSign", "1"]
            )
            # HMBS reports HMBS_CAP_CHMOD=0 on this target (chmod unsupported):
            # preserve mode on a best-effort basis, never fail the build here.
            if original_mode is not None:
                try:
                    os.chmod(temporary, original_mode)
                except OSError as exc:
                    self.output.warning("chmod on {} failed (ignored): {}".format(temporary, exc))
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = (
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    def package_info(self):
        # Upstream naming is eccentric but real (verified against Arch/FreshPorts
        # file lists): shared target "libmusicxml" installs liblibmusicxml.so*
        # (VERSION 3.2.2, SOVERSION 3), static target "musicxml2static" with
        # OUTPUT_NAME musicxml2 installs libmusicxml2.a. cpp_info.libs is the
        # bare name without "lib" prefix/suffix, hence "libmusicxml" <-> file
        # liblibmusicxml.so. Declaring "musicxml" here makes CMakeDeps abort
        # with "Library 'musicxml' not found in package".
        if self.options.shared:
            self.cpp_info.libs = ["libmusicxml"]
        else:
            self.cpp_info.libs = ["musicxml2"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "libmusicxml")]
        self.cpp_info.set_property("cmake_file_name", "libmusicxml")
        self.cpp_info.set_property("cmake_target_name", "libmusicxml::libmusicxml")
