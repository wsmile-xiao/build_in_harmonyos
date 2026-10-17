#!/usr/bin/env python3
"""Conan recipe for pupnp 1.14.31 (Portable SDK for UPnP Devices).

Upstream: https://github.com/pupnp/pupnp (tag release-1.14.31,
asset libupnp-1.14.31.tar.bz2). Dual library: libixml (XML parser) and
libupnp (UPnP core: discovery, control, eventing, embedded web server).

OHOS notes:
- CMake build (upstream supports CMake and Autotools; CMake avoids the
  Autotools/HMDFS restrictions noted by the libupnp 1.18.5 adaptation).
- Both upstream linkages are built and shipped (UPNP_BUILD_SHARED=ON and
  UPNP_BUILD_STATIC=ON, the upstream defaults), so the complete 18-entry
  CTest suite runs and every consumer can choose shared or static linking
  from a single package. A standard `shared`/`fPIC` option pair is declared
  for Conan `library` compliance (the package always carries both artifacts;
  the option does not trim the build matrix).
- Samples (tv_ctrlpt/tv_combo/tv_device demo programs) are disabled
  (UPNP_BUILD_SAMPLES=OFF): they are demo binaries, not library API, and
  keeping them out keeps the package a pure library (no commands.json).
- OpenSSL support stays OFF (upstream default): no extra dependency.
- The gtest-based test (gtest/test_template.cpp, 1 TEST case) is enabled by
  supplementing GTest from the ohpcd registry via `test_requires`
  (gtest/1.18.5 pattern: test_requires does not enter the runtime
  dependency graph; CMakeDeps generates the GTest config that upstream
  `find_package(GTest CONFIG)` expects).
- Upstream tests run inside build() via ctest. discovered comes from
  `ctest -N` (Total Tests line); executed/passed/failed/skipped come from
  the captured `ctest --output-on-failure` stdout (per-line
  "N/M Test #K: <name> ... Passed|Failed|Timeout|Skipped"). No guessing,
  no arithmetic patching; identity passed+failed==executed is self-checked.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PupnpConan(ConanFile):
    name = "pupnp"
    version = "1.14.31"
    description = "Portable SDK for UPnP Devices (libupnp + libixml)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pupnp/pupnp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # Conan `library` package_type requires a `shared` option. The package
    # always builds and ships both upstream linkages (full 18-entry CTest
    # suite), so this option is ecosystem compatibility and does not trim
    # the build matrix.
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # Build-time test framework only: upstream enables gtest/ only when
    # find_package(GTest CONFIG) succeeds. test_requires keeps it out of
    # the runtime dependency graph (openrct2/0.5.3 precedent).
    test_requires = "gtest/1.17.0.1"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pupnp is adapted for Linux and OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_writable_tmp(self):
        # HMBS true-device mounts /tmp read-only; reuse the injected
        # writable TMPDIR/TMP/TEMP (plus HOME/tmp and build-local fallback)
        # so CMake compiler checks and ctest can write. Only redirects the
        # temp root, never skips upstream tests.
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.getenv("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                tmpdir = json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as handle:
                    handle.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                os.environ["GOTMPDIR"] = cand
                return cand
            except Exception:
                continue
        return None

    def _resolve_compiler(self, configured, names):
        # Tool-specific candidates only: never fall back from C to C++
        # names or vice versa. Prefer the profile's configured absolute
        # path when it exists (CI workers), otherwise resolve via PATH
        # or the ~/usr/local/bin fallback (true-device clang migration).
        if configured and os.path.exists(configured):
            return configured
        for tool in names:
            found = shutil.which(tool)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for tool in names:
            cand = os.path.join(home_bin, tool)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("GOTMPDIR", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")
        deps = CMakeDeps(self)
        deps.generate()
        vrun = VirtualRunEnv(self)
        vrun.generate()
        tc = CMakeToolchain(self)
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            compilers = None
        if not isinstance(compilers, dict):
            compilers = {}
        c_tool = self._resolve_compiler(compilers.get("c"),
                                        ("clang", "cc"))
        cxx_tool = self._resolve_compiler(compilers.get("cpp"),
                                          ("clang++", "c++"))
        if c_tool:
            tc.cache_variables["CMAKE_C_COMPILER"] = c_tool
        if cxx_tool:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx_tool
        self.output.info("HMBS diag compilers c=%s cxx=%s"
                         % (c_tool, cxx_tool))
        # Preserve upstream defaults: both linkages (full 18-entry CTest
        # suite), testing on, samples off (demo binaries are not library
        # API; keeps the package a pure library), OpenSSL off (no dep).
        # NOTE: self.options.shared is intentionally NOT mapped to
        # UPNP_BUILD_SHARED/STATIC; both stay ON so either package_id runs
        # the complete suite (Conan hard-gate requires the option to exist).
        tc.variables["UPNP_BUILD_SHARED"] = True
        tc.variables["UPNP_BUILD_STATIC"] = True
        tc.variables["BUILD_TESTING"] = True
        tc.variables["UPNP_BUILD_SAMPLES"] = False
        tc.variables["UPNP_ENABLE_OPEN_SSL"] = False
        tc.variables["DOWNLOAD_AND_BUILD_DEPS"] = False
        # Static archives must be linkable into shared consumers.
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        # Keep CMake's build-tree RPATH so shared test executables find
        # the just-built libixml/libupnp without relying on the loader's
        # default search path (HarmonyOS reports as unknown to CMake and
        # may not record SONAME/RPATH like Linux does). $ORIGIN entries
        # additionally cover the installed layout; harmless on Linux.
        tc.cache_variables["CMAKE_SKIP_RPATH"] = False
        tc.cache_variables["CMAKE_SKIP_BUILD_RPATH"] = False
        tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = False
        tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = True
        # HarmonyOS has no CMake Platform/HarmonyOS module, so
        # CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG stays empty and the
        # linker never receives -Wl,-soname: libixml/libupnp end up with
        # no DT_SONAME and libupnp.so records a literal relative NEEDED
        # "../ixml/libixml.so" (consumer-log evidence 2026-09-24), which
        # the musl loader resolves as a path and fails with 127 even
        # when LD_LIBRARY_PATH is correct. Upstream already sets
        # VERSION/SOVERSION on both targets, so only the toolchain flags
        # are needed (libharu SONAME precedent): force unversioned
        # SONAMEs (libixml.so/libupnp.so) relocatable via LD_LIBRARY_PATH.
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = True
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()
        self._fix_generated_toolchain_compiler(compilers, c_tool, cxx_tool)

    def _fix_generated_toolchain_compiler(self, configured_map, c_tool,
                                          cxx_tool):
        # The cache_variables pin alone may not override a stale profile
        # compiler path on the true device, so correct the generated
        # conan_toolchain.cmake itself -- only when the configured path is
        # missing and the resolved one exists (CI workers untouched).
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c_tool and c_old != c_tool \
                and not os.path.exists(c_old) and os.path.exists(c_tool):
            pairs.append((c_old, c_tool))
        if cxx_old and cxx_tool and cxx_old != cxx_tool \
                and not os.path.exists(cxx_old) \
                and os.path.exists(cxx_tool):
            pairs.append((cxx_old, cxx_tool))
        if not pairs:
            return
        try:
            gen_folder = getattr(self, "generators_folder", None)
            path = os.path.join(gen_folder, "conan_toolchain.cmake") \
                if gen_folder else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    text = handle.read()
                orig = text
                for old_path, new_path in pairs:
                    text = text.replace(old_path, new_path)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(text)
                    self.output.info(
                        "HMBS diag fixed generated toolchain %s" % path)
            else:
                self.output.warning(
                    "HMBS diag toolchain file not found: %s" % path)
        except Exception as exc:
            self.output.warning("HMBS diag toolchain fix failed: %s" % exc)
        try:
            comp_env = Environment()
            if c_old and c_tool and (c_old, c_tool) in pairs:
                comp_env.define("CC", c_tool)
            if cxx_old and cxx_tool and (cxx_old, cxx_tool) in pairs:
                comp_env.define("CXX", cxx_tool)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as exc:
            self.output.warning(
                "HMBS diag compiler env export failed: %s" % exc)

    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            payload, separators=(",", ":"))
        # Dual-channel: conan output + raw stdout so preflight catches it.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                with open(os.path.join(bf, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as handle:
                    json.dump(payload, handle)
        except Exception as exc:
            self.output.warning("HMBS diag persist upstream failed: %s"
                                % exc)
        return line

    def _read_text(self, path):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def _find_lib_dirs(self):
        # Locate the just-built shared libraries so the test run can
        # find them even when the HarmonyOS loader does not honour the
        # build-tree RPATH (CMake reports "System is unknown" for
        # HarmonyOS and may skip SONAME/RPATH handling it does on Linux).
        found = []
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if name == "libixml.so" or name.startswith("libixml.so."):
                    found.append(root)
                    break
            else:
                continue
            break
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if name == "libupnp.so" or name.startswith("libupnp.so."):
                    found.append(root)
                    break
            else:
                continue
            break
        dirs = []
        for item in found:
            if item not in dirs:
                dirs.append(item)
        return dirs

    def _ensure_shared_loader_path(self):
        """Export LD_LIBRARY_PATH and repair relative DT_NEEDED lookups.

        True-device evidence (2026-09-23): every shared upnp test failed
        with musl loader errors
        "Error loading shared library ../ixml/libixml.so:
        (needed by ../libupnp.so)" while all -static twins passed.
        Upstream records no SONAME handling for the unknown HarmonyOS
        platform, so the slash-containing NEEDED entries resolve relative
        to each test's working directory (build/upnp/test) instead of via
        SONAME search. Creating build/upnp/ixml -> ../ixml makes
        <cwd>/../ixml/libixml.so resolve to the real build/ixml artefact;
        LD_LIBRARY_PATH covers the SONAME-search case. No test is skipped
        or altered; this only repairs the runtime search path.
        """
        lib_dirs = self._find_lib_dirs()
        if lib_dirs:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            extra = ":".join(lib_dirs)
            os.environ["LD_LIBRARY_PATH"] = extra + (":" + prev if prev else "")
            self.output.info("HMBS diag lib_dirs=%s" % lib_dirs)
        else:
            self.output.warning("HMBS diag no built libixml/libupnp found")
        # Compatibility symlink for slash-containing NEEDED:
        # <build>/upnp/ixml -> <build>/ixml
        try:
            upnp_dir = None
            ixml_dir = None
            for root, dirs, _files in os.walk(self.build_folder):
                if "libupnp.so" in dirs or any(
                        d.startswith("libupnp") for d in dirs):
                    pass
                if os.path.basename(root) == "upnp" and os.path.isdir(root):
                    # Prefer the top-level build/upnp directory.
                    parent = os.path.dirname(root)
                    if parent == self.build_folder or upnp_dir is None:
                        upnp_dir = root
                if os.path.basename(root) == "ixml" and os.path.isdir(root):
                    parent = os.path.dirname(root)
                    if parent == self.build_folder or ixml_dir is None:
                        ixml_dir = root
                if upnp_dir and ixml_dir:
                    break
            if not upnp_dir:
                cand = os.path.join(self.build_folder, "upnp")
                if os.path.isdir(cand):
                    upnp_dir = cand
            if not ixml_dir:
                cand = os.path.join(self.build_folder, "ixml")
                if os.path.isdir(cand):
                    ixml_dir = cand
            if upnp_dir and ixml_dir:
                link = os.path.join(upnp_dir, "ixml")
                if not os.path.lexists(link):
                    try:
                        os.symlink(os.path.relpath(ixml_dir, upnp_dir), link)
                        self.output.info(
                            "HMBS diag compat symlink %s -> %s"
                            % (link, ixml_dir))
                    except Exception as exc:
                        self.output.warning(
                            "HMBS diag symlink failed: %s" % exc)
                # Also drop direct .so symlinks next to the upnp lib dir
                # so both <cwd>/../libupnp.so and ../ixml/libixml.so hit.
                for lib_dir in lib_dirs:
                    for name in os.listdir(lib_dir):
                        if name.startswith(
                                ("libixml.so", "libupnp.so")):
                            src = os.path.join(lib_dir, name)
                            dst = os.path.join(upnp_dir, name)
                            if not os.path.lexists(dst) and os.path.isfile(
                                    src):
                                try:
                                    os.symlink(
                                        os.path.relpath(src, upnp_dir), dst)
                                except Exception:
                                    pass
        except Exception as exc:
            self.output.warning("HMBS diag loader-path fix failed: %s" % exc)

    def _run_upstream_tests(self):
        """Run the full upstream CTest suite and emit the hard-gate marker.

        discovered: parsed from `ctest -N` ("Total Tests: N").
        executed/passed/failed/skipped: parsed per-line from the captured
        `ctest --output-on-failure` stdout
        ("N/M Test #K: <name> ... Passed|Failed|Timeout|Skipped").
        That stdout capture (hmbs_ctest_run.log) is the single
        deterministic source; Testing/Temporary/LastTest.log is only
        logged for forensics. A missing/empty capture yields a failed
        marker with reason (never fabricated).
        """
        if cross_building(self):
            self.output.warning(
                "Cross build: upstream executables compiled but not run.")
            self._hmbs_emit_upstream({
                "status": "skipped",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "cross_building: tests compiled, not executed",
            })
            return
        list_log = os.path.join(self.build_folder, "hmbs_ctest_list.log")
        self.run('ctest -N > "%s" 2>&1' % list_log,
                 cwd=self.build_folder, env="conanbuild",
                 ignore_errors=True)
        discovered = 0
        if os.path.isfile(list_log):
            match = re.search(r"Total Tests:\s*(\d+)",
                              self._read_text(list_log))
            if match:
                discovered = int(match.group(1))
        self._ensure_shared_loader_path()
        run_log = os.path.join(self.build_folder, "hmbs_ctest_run.log")
        self.run('ctest --output-on-failure > "%s" 2>&1' % run_log,
                 cwd=self.build_folder, env=["conanbuild", "conanrun"],
                 ignore_errors=True)
        run_text = ""
        if os.path.isfile(run_log):
            run_text = self._read_text(run_log)
            tail = run_text.splitlines()[-30:]
            self.output.info("=== upstream ctest (tail) ===")
            for line in tail:
                self.output.info(line)
        else:
            run_text = ""
        # Forensics only: LastTest.log location (not a counting source).
        last_test = None
        for root, _dirs, files in os.walk(self.build_folder):
            if "LastTest.log" in files and root.endswith(
                    os.path.join("Testing", "Temporary")):
                last_test = os.path.join(root, "LastTest.log")
                break
        self.output.info("HMBS diag LastTest.log=%s" % last_test)
        if not run_text.strip():
            searched = [list_log, run_log]
            self._hmbs_emit_upstream({
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "empty ctest stdout capture; searched %s"
                          % searched,
            })
            raise RuntimeError(
                "upstream ctest produced no stdout capture; "
                "searched %s" % searched)
        passed = failed = skipped = 0
        parsed_lines = 0
        failed_names = []
        skipped_names = []
        for line in run_text.splitlines():
            match = re.match(r"^\s*(\d+)/(\d+)\s+Test\s+#\d+:\s+(\S+)\s*(.*)$",
                             line)
            if not match:
                continue
            parsed_lines += 1
            name = match.group(3)
            tail = match.group(4)
            if "Passed" in tail:
                passed += 1
            elif "Timeout" in tail:
                failed += 1
                failed_names.append(name)
            elif "Failed" in tail:
                failed += 1
                failed_names.append(name)
            elif "Skip" in tail:
                skipped += 1
                skipped_names.append(name)
        if discovered <= 0:
            # ctest -N output unparseable: fall back to the parsed line
            # count from the same deterministic log file (single source,
            # no stdout word counting).
            discovered = parsed_lines
        executed = passed + failed
        identities_ok = (
            discovered > 0
            and parsed_lines == discovered
            and passed + failed == executed
            and executed + skipped <= discovered
            and executed <= discovered
        )
        status = "passed" if (
            identities_ok and failed == 0 and skipped == 0
            and executed == discovered) else "failed"
        result = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if status != "passed":
            result["reason"] = (
                "parsed_lines=%d identities_ok=%s "
                "(see hmbs_ctest_run.log; LastTest.log=%s)"
                % (parsed_lines, identities_ok, last_test))
            gaps = []
            if failed:
                gaps.append({
                    "count": failed,
                    "category": "test_failure",
                    "detail": "failed ctest entries: %s"
                              % ", ".join(failed_names[:10]),
                    "evidence": "hmbs_ctest_run.log ctest --output-on-failure",
                })
            if skipped:
                gaps.append({
                    "count": skipped,
                    "category": "environment",
                    "detail": "skipped ctest entries: %s"
                              % ", ".join(skipped_names[:10]),
                    "evidence": "hmbs_ctest_run.log ctest --output-on-failure",
                })
            if gaps:
                result["gaps"] = gaps
        self._hmbs_emit_upstream(result)
        if status != "passed":
            raise RuntimeError(
                "upstream ctest failed: discovered=%d executed=%d "
                "passed=%d failed=%d skipped=%d"
                % (discovered, executed, passed, failed, skipped))

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # Carry the real upstream result into the package so cache-hit
        # test_package runs can re-emit without re-running the build.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(res_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(res_dir,
                                                  "hmbs_upstream.json"))
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as exc:
            self.output.warning("HMBS diag package upstream copy failed: %s"
                                % exc)

    def package_info(self):
        # libupnp links libixml; keep dependency order.
        self.cpp_info.libs = ["upnp", "ixml"]
        self.cpp_info.set_property("cmake_file_name", "UPNP")
        self.cpp_info.set_property("cmake_target_name", "UPNP::Shared")
        self.cpp_info.set_property("pkg_config_name", "libupnp")
