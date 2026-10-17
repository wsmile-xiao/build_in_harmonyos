#!/usr/bin/env python3
"""Conan recipe -- ocl-icd 2.3.5 (Autotools)

OpenCL ICD Loader (free software alternative to vendor-specific ICD loaders).
Builds libOpenCL.so plus the cllayerinfo utility from the OCL-dev
database-driven sources (icd_generator.rb + ocl_interface.yaml).
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OclIcdConan(ConanFile):
    name = "ocl-icd"
    version = "2.3.5"
    description = "OpenCL ICD Loader (free software alternative to vendor-specific ICD loaders)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/OCL-dev/ocl-icd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No runtime requirements: the build uses the bundled khronos-headers
        # copy inside the sources (configure falls back to it automatically
        # when no system CL headers exist, which is the OHOS case).
        pass

    def build_requirements(self):
        # The GitHub archive ships configure.ac only, so configure must be
        # bootstrapped on the worker (same approach as zbar/0.23.93).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ocl-icd only supports Linux/OHOS, got: {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"OHOS builds require armv8/aarch64, got: {self.settings.arch}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # E007: bundled config.guess predates HarmonyOS and cannot guess the
        # build type when uname -s reports HarmonyOS; config.sub already
        # normalizes linux-ohos, so pin an explicit native triplet.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # GitHub archive has no pre-generated configure; bootstrap it with
        # the tool_requires-provided autotools (ruby ships on the worker and
        # is used by icd_generator.rb during the build itself).
        autotools.autoreconf()
        # E011: HMDFS inherits umask 077, fix it in the fresh configure.
        self.run("sed -i 's/umask 077/umask 022/g' configure",
                 cwd=self.source_folder)
        autotools.configure()
        # ACLOCAL/AUTOMAKE/AUTOHEADER=true stops make from trying to
        # regenerate autotools files on timestamp skew (zbar pattern).
        autotools.make(args=["-j1", "ACLOCAL=true", "AUTOMAKE=true",
                             "AUTOHEADER=true"])
        # Upstream test suite (make check): ocl_test / ocl_test_icdl plus
        # the tests/ autotest testsuite (34 cases). Fails the build on red.
        autotools.make(target="check", args=["-j1", "ACLOCAL=true",
                                             "AUTOMAKE=true",
                                             "AUTOHEADER=true"])
        self._emit_upstream_marker()
        # Snapshot the just-built library bytes NOW: at package() time the
        # build-tree search empirically finds nothing (round-4 log: "no
        # real libOpenCL entity found in build tree"), so capture the
        # artifacts while `make`/`make check` has provably produced them.
        self._stage_built_libs()

    def _emit_upstream_marker(self):
        """Parse tests/testsuite.log and emit the HMBS evidence marker.

        Source audit: testsuite-standard.at has 15 AT_SETUP cases,
        testsuite-default-platform.at has 16, testsuite-workaround.at
        has 3 -- 34 autotest cases in total. Numbers below come from the
        actually generated testsuite.log, never from this comment.

        Note: ocl-icd drives its suite via `check-local: $(SHELL)
        '$(TESTSUITE)'` (tests/Makefile.am), i.e. a direct Autotest
        invocation, not the Automake TESTS harness. There is therefore
        no `# TOTAL:` summary line; the native Autotest summary is
        `All N tests were successful.` Both formats are parsed.
        """
        log_path = self._find_testsuite_log()
        discovered = executed = passed = failed = skipped = 0
        status = "failed"
        reason = ""
        if log_path is None:
            reason = "tests/testsuite.log not found after make check"
            text = ""
        else:
            try:
                with open(log_path, "r", encoding="utf-8",
                           errors="replace") as f:
                    text = f.read()
            except OSError as exc:
                reason = f"cannot read testsuite.log: {exc!r}"
                text = ""
            if text:
                total = self._log_number(text, "TOTAL")
                npass = self._log_number(text, "PASS")
                nfail = self._log_number(text, "FAIL")
                nskip = self._log_number(text, "SKIP")
                nxpass = self._log_number(text, "XPASS")
                nerror = self._log_number(text, "ERROR")
                if total > 0:
                    discovered = total
                    failed = nfail + nxpass + nerror
                    skipped = nskip
                    passed = npass
                    executed = passed + failed
                    if failed == 0 and executed > 0:
                        status = "passed"
                    elif failed > 0:
                        reason = (f"autotest suite reports "
                                  f"{failed} failed case(s)")
                    else:
                        reason = ("exit 0 but no passed cases parsed "
                                  "from testsuite.log")
                else:
                    parsed = self._parse_autotest_summary(text)
                    if parsed is not None:
                        (discovered, executed, passed,
                         failed, skipped) = parsed
                        if failed == 0 and executed > 0:
                            status = "passed"
                        elif failed > 0:
                            reason = (f"autotest suite reports "
                                      f"{failed} failed case(s)")
                        else:
                            reason = ("exit 0 but no passed cases parsed "
                                      "from testsuite.log")
                    else:
                        reason = "no TOTAL line parsed from testsuite.log"
                tail = "\n".join(text.splitlines()[-8:])
                self.output.info(f"testsuite.log tail:\n{tail}")
        marker = {
            "status": status,
            "framework": "autotest",
            "command": "make check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            marker["reason"] = reason
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if status != "passed":
            raise ConanException(
                f"ocl-icd upstream tests did not pass: {reason}")

    def _find_testsuite_log(self):
        # check-local runs $(SHELL) '$(TESTSUITE)' with cwd at the top
        # build dir, so testsuite.log may live under the base build dir
        # (not the build-release subdir) or under tests/. Search all
        # plausible roots plus test-suite.log (Automake wrapper name).
        roots = []
        for attr in ("build_folder", "source_folder",
                     "base_build_folder", "base_source_folder"):
            try:
                value = getattr(self.folders, attr, None) or getattr(
                    self, attr, None)
            except Exception:
                value = None
            if value and os.path.isdir(value) and value not in roots:
                roots.append(value)
        rel_names = [
            os.path.join("tests", "testsuite.log"),
            "testsuite.log",
            "test-suite.log",
            os.path.join("tests", "test-suite.log"),
        ]
        for root in roots:
            for rel in rel_names:
                path = os.path.join(root, rel)
                if os.path.isfile(path) and os.path.getsize(path) > 0:
                    return path
        # Recursive fallback: any testsuite.log / test-suite.log with
        # Autotest or Automake summary content under the known roots.
        for root in roots:
            for name in ("testsuite.log", "test-suite.log"):
                pattern = os.path.join(root, "**", name)
                try:
                    hits = sorted(glob.glob(pattern, recursive=True))
                except Exception:
                    hits = []
                for path in hits:
                    try:
                        if (os.path.isfile(path)
                                and os.path.getsize(path) > 0):
                            return path
                    except OSError:
                        continue
        return None

    @staticmethod
    def _parse_autotest_summary(text):
        """Parse native Autotest summary lines.

        Returns (discovered, executed, passed, failed, skipped) or None.
        Handles `All N tests were successful.` and partial summaries
        such as `N tests passed, M failed (K skipped ...)`.
        """
        all_ok = re.search(
            r"All\s+(\d+)\s+tests?\s+were\s+successful\.?", text)
        if all_ok:
            n = int(all_ok.group(1))
            if n > 0:
                return (n, n, n, 0, 0)
            return None
        all_passed = re.search(
            r"All\s+(\d+)\s+tests?\s+passed\.?", text)
        if all_passed:
            n = int(all_passed.group(1))
            if n > 0:
                return (n, n, n, 0, 0)
            return None
        # Partial summary, e.g. "34 tests passed, 1 failed" or
        # "3 tests failed, 31 passed (2 skipped)". Only accept when at
        # least one passed/failed count is present.
        passed = failed = skipped = 0
        found = False
        for key, pat in (
                ("passed", r"(\d+)\s+tests?\s+passed"),
                ("failed", r"(\d+)\s+tests?\s+failed"),
                ("skipped", r"(\d+)\s+tests?\s+skipped"),
                ("failed2", r"#\s*of\s+unexpected\s+failures\s*[:\s]+(\d+)"),
                ("passed2", r"#\s*of\s+expected\s+passes\s*[:\s]+(\d+)"),
        ):
            m = re.search(pat, text, re.IGNORECASE)
            if not m:
                continue
            found = True
            if key in ("passed", "passed2"):
                passed += int(m.group(1))
            elif key in ("failed", "failed2"):
                failed += int(m.group(1))
            else:
                skipped += int(m.group(1))
        if not found:
            return None
        discovered = passed + failed + skipped
        executed = passed + failed
        if discovered <= 0 or executed <= 0:
            return None
        return (discovered, executed, passed, failed, skipped)

    @staticmethod
    def _log_number(text, key):
        match = re.search(rf"^#\s*{key}:\s*(\d+)\s*$", text,
                          re.MULTILINE)
        return int(match.group(1)) if match else 0

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["ACLOCAL=true", "AUTOMAKE=true",
                                "AUTOHEADER=true"])
        copy(self, "COPYING",
             self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # Upstream builds dummy ICDs as pkglib_LTLIBRARIES and removes
        # $(pkglibdir) (= lib{,64}/ocl-icd) via install-exec-hook. If that
        # hook did not run, drop the leftovers here so they never pollute
        # the package; the real lib (libOpenCL) lives directly in lib/
        # (or lib64/ on some triplets) and is kept.
        for libdir in ("lib", "lib64"):
            dummy_dir = os.path.join(self.package_folder, libdir, "ocl-icd")
            if os.path.isdir(dummy_dir):
                shutil.rmtree(dummy_dir, ignore_errors=True)
        # Drop libtool wrapper archives in both candidate libdirs.
        for libdir in ("lib", "lib64"):
            for stale in glob.glob(os.path.join(self.package_folder, libdir,
                                                 "*.la")):
                try:
                    os.remove(stale)
                except OSError:
                    pass
        # Log the real install layout (names, link targets, sizes) so a
        # consumer-side "Library not found" can be diagnosed from evidence
        # instead of guessed from the recipe text.
        self._log_package_libs()
        # Repair the files CMakeDeps find_library() needs: the unversioned
        # libOpenCL.so development link must resolve to a real file. A
        # dangling link passes naive islink() checks yet fails in CMake,
        # so re-point or materialize it from the versioned library.
        self._repair_opencl_links()
        # 2026-09-07 healing: the 2026-09-06 preflight proved the versioned
        # entity itself can be absent from the package (only DANGLING
        # libOpenCL.so -> libOpenCL.so.1.0.0 and libOpenCL.so.1 ->
        # libOpenCL.so.1.0.0 remained). In that state intra-package repair
        # has nothing to copy from, so fall back to the staged snapshot
        # (captured at build() time) and then the build tree's .libs/
        # artifacts via plain Python copy (bypasses the HMBS install shim
        # / chmod / hardlink limits that libtool install hits).
        if not self._has_opencl_lib():
            self._heal_opencl_from_build()
            self._repair_opencl_links()
            self._log_package_libs()
        # Fail fast with the observed layout if the main library is still
        # missing instead of a cryptic CMakeDeps error downstream.
        # NOTE: os.path.exists() follows symlinks, so dangling links do
        # NOT count here (unlike islink()).
        if not self._has_opencl_lib():
            raise ConanException(
                "ocl-icd: libOpenCL not found in lib/ nor lib64/ "
                "after make install; see package lib listing above")

    def _lib_candidates(self):
        for libdir in ("lib", "lib64"):
            lib_dir = os.path.join(self.package_folder, libdir)
            if not os.path.isdir(lib_dir):
                continue
            try:
                names = sorted(os.listdir(lib_dir))
            except OSError:
                continue
            for name in names:
                if name == "libOpenCL" or name.startswith("libOpenCL."):
                    yield lib_dir, name

    def _log_package_libs(self):
        lines = []
        for lib_dir, name in self._lib_candidates():
            path = os.path.join(lib_dir, name)
            try:
                if os.path.islink(path):
                    target = os.readlink(path)
                    ok = os.path.exists(path)
                    size = os.path.getsize(path) if ok else -1
                    lines.append(
                        f"{path} -> {target} "
                        f"[{'OK' if ok else 'DANGLING'}, size={size}]")
                elif os.path.isfile(path):
                    lines.append(
                        f"{path} [file, size={os.path.getsize(path)}]")
                else:
                    lines.append(f"{path} [special node]")
            except OSError as exc:
                lines.append(f"{path} [unstatable: {exc!r}]")
        if not lines:
            lines = ["<no libOpenCL.* entries under lib/ or lib64/>"]
        self.output.info("ocl-icd package lib listing:\n" + "\n".join(lines))

    def _has_opencl_lib(self):
        for lib_dir, name in self._lib_candidates():
            path = os.path.join(lib_dir, name)
            if name in ("libOpenCL.so", "libOpenCL.a", "libOpenCL.dylib",
                        "OpenCL.lib"):
                if os.path.exists(path):
                    return True
            elif re.match(r"libOpenCL\.so\..+", name):
                if os.path.isfile(path) and not os.path.islink(path):
                    return True
        return False

    def _repair_opencl_links(self):
        for libdir in ("lib", "lib64"):
            lib_dir = os.path.join(self.package_folder, libdir)
            if not os.path.isdir(lib_dir):
                continue
            # Accept both libOpenCL.so.1 (single suffix, usually a link)
            # and libOpenCL.so.1.0.0 (double suffix, the real entity);
            # only non-link regular files count as copy sources.
            real_targets = sorted(
                p for p in glob.glob(
                    os.path.join(lib_dir, "libOpenCL.so.*"))
                if os.path.isfile(p) and not os.path.islink(p)
                and self._is_real_lib(p))
            if not real_targets:
                continue
            best = real_targets[-1]
            dev_link = os.path.join(lib_dir, "libOpenCL.so")
            if os.path.exists(dev_link):
                continue
            try:
                if os.path.islink(dev_link):
                    os.remove(dev_link)
            except OSError:
                pass
            try:
                os.symlink(os.path.basename(best), dev_link)
            except OSError:
                try:
                    shutil.copyfile(best, dev_link)
                except OSError:
                    continue
            self.output.info(
                f"ocl-icd: (re)created {dev_link} -> {best}")

    @staticmethod
    def _is_real_lib(path):
        try:
            return os.path.getsize(path) > 0
        except OSError:
            return False

    def _build_roots(self):
        roots = []
        for attr in ("build_folder", "source_folder",
                     "base_build_folder", "base_source_folder"):
            try:
                value = getattr(self.folders, attr, None) or getattr(
                    self, attr, None)
            except Exception:
                value = None
            if value and os.path.isdir(value) and value not in roots:
                roots.append(value)
        return roots

    def _stage_built_libs(self):
        """Snapshot the just-built libOpenCL bytes at build() time.

        Round-4 evidence: at package() time the build-tree search finds
        nothing ("no real libOpenCL entity found in build tree") even
        though `make`/`make check` provably produced a working library
        (34/34 autotest cases ran against it). Capturing the bytes here
        -- while they provably exist -- removes the dependence on
        package-time rediscovery. Plain Python I/O bypasses the HMBS
        install shim / chmod / hardlink limits.
        """
        stage = os.path.join(self.build_folder, "_ocl_staged")
        try:
            os.makedirs(stage, exist_ok=True)
        except OSError:
            pass
        arts = self._collect_opencl_artifacts()
        picked = self._pick_lib_source(arts)
        if picked is None:
            self.output.warning(
                "ocl-icd: build-time staging found no libOpenCL bytes; "
                "package() healing will rely on live search")
            return
        src, base = picked
        try:
            shutil.copyfile(src, os.path.join(stage, base))
            self.output.info(
                f"ocl-icd: staged {base} "
                f"(size={os.path.getsize(os.path.join(stage, base))}) "
                f"from {src}")
        except OSError as exc:
            self.output.warning(
                f"ocl-icd: staging copy failed {src}: {exc!r}")

    def _collect_opencl_artifacts(self):
        """Walk build/source roots; log every *OpenCL* entry as evidence.

        Symlinks are recorded with their targets and resolvability so the
        next log shows the real layout instead of another blind guess.
        """
        roots = self._build_roots()
        if roots:
            self.output.info("ocl-icd artifact roots:")
            for root in roots:
                self.output.info(f"ocl-icd root: {root}")
        else:
            self.output.info("ocl-icd artifact roots: <none>")
        entries = []
        for root in roots:
            try:
                top = sorted(os.listdir(root))
            except OSError as exc:
                self.output.info(f"ocl-icd: cannot list {root}: {exc!r}")
                continue
            self.output.info(
                f"ocl-icd top of {root} (first 30): {top[:30]}")
            for dirpath, dirnames, filenames in os.walk(root):
                for name in filenames + dirnames:
                    if "OpenCL" not in name:
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        if os.path.islink(path):
                            target = os.readlink(path)
                            real = os.path.realpath(path)
                            ok = os.path.isfile(real)
                            size = os.path.getsize(real) if ok else -1
                            entries.append((path, "link:" + target, ok,
                                            size, real if ok else None))
                        elif os.path.isfile(path):
                            entries.append((path, "file", True,
                                            os.path.getsize(path), path))
                        else:
                            entries.append((path, "other", False, -1,
                                            None))
                    except OSError:
                        entries.append((path, "unstatable", False, -1,
                                        None))
        for path, kind, ok, size, _real in entries[:40]:
            self.output.info(
                f"ocl-icd artifact: {path} [{kind}] usable={ok} "
                f"size={size}")
        if not entries:
            self.output.info("ocl-icd artifacts: <none found>")
        return entries

    def _pick_lib_source(self, entries):
        """Pick (bytes_path, dest_basename) for the main library.

        Unlike rounds 2-4, symlinks are accepted when they resolve to
        real bytes: a symlink-only .libs layout would explain the
        round-4 empty search, which rejected every link outright.
        """
        cands = []
        for _path, _kind, ok, size, real in entries:
            if not ok or size <= 0 or real is None:
                continue
            base = os.path.basename(real)
            if base == "libOpenCL.so":
                rank_kind = 1
            elif re.match(r"libOpenCL[.]so[.][0-9]", base):
                if re.match(r"libOpenCL[.]so[.][0-9]+[.][0-9]", base):
                    rank_kind = 0
                else:
                    rank_kind = 1
            elif base == "libOpenCL.a":
                rank_kind = 2
            else:
                continue
            in_libs = 0 if ".libs" in real.replace(os.sep, "/") else 1
            cands.append(((rank_kind, in_libs, len(base), size, real),
                          real, base))
        if not cands:
            return None
        cands.sort(key=lambda item: item[0])
        _key, real, base = cands[0]
        return (real, base)

    def _heal_opencl_from_build(self):
        """Restore a missing libOpenCL entity from staged/live bytes.

        Round-5 route (differs from rounds 2-4, which searched the live
        build tree only and found nothing): the primary source is the
        build-time snapshot written by _stage_built_libs() into
        <build_folder>/_ocl_staged while `make` artifacts provably
        exist. The live build-tree walk (now with symlink resolution
        and full *OpenCL* evidence logging) remains as fallback.
        Absolute absence still fails fast in package() with the layout
        listing; no test is skipped or stubbed.
        """
        dest_dir = None
        for libdir in ("lib", "lib64"):
            candidate = os.path.join(self.package_folder, libdir)
            if os.path.isdir(candidate):
                dest_dir = candidate
                break
        if dest_dir is None:
            dest_dir = os.path.join(self.package_folder, "lib")
            try:
                os.makedirs(dest_dir, exist_ok=True)
            except OSError:
                pass
        # Source 1: build-time staged snapshot (primary).
        stage = os.path.join(self.build_folder, "_ocl_staged")
        try:
            staged = sorted(os.listdir(stage)) if os.path.isdir(stage) else []
        except OSError:
            staged = []
        for base in staged:
            if (base == "libOpenCL.so" or base == "libOpenCL.a"
                    or re.match(r"libOpenCL[.]so[.][0-9]", base)):
                if self._place_healed_lib(
                        os.path.join(stage, base), base, dest_dir,
                        "staged"):
                    return
        # Source 2: live build-tree search with symlink resolution.
        arts = self._collect_opencl_artifacts()
        picked = self._pick_lib_source(arts)
        if picked is None:
            self.output.warning(
                "ocl-icd: no usable libOpenCL bytes in build tree; "
                "package healing skipped")
            return
        src, base = picked
        self._place_healed_lib(src, base, dest_dir, "build-tree")

    def _place_healed_lib(self, src, base, dest_dir, origin):
        """Copy lib bytes into the package; rebuild SONAME/dev links."""
        dest = os.path.join(dest_dir, base)
        try:
            if not (os.path.isfile(dest) and not os.path.islink(dest)
                    and os.path.getsize(dest) > 0):
                try:
                    if os.path.islink(dest) or os.path.isfile(dest):
                        os.remove(dest)
                except OSError:
                    pass
                shutil.copyfile(src, dest)
                self.output.info(
                    f"ocl-icd: healed {dest} from {origin} {src} "
                    f"(size={os.path.getsize(dest)})")
        except OSError as exc:
            self.output.warning(
                f"ocl-icd: healing copy failed {src} -> {dest}: {exc!r}")
            return False
        if base.startswith("libOpenCL.so."):
            parts = base.split(".")
            if len(parts) >= 4:
                soname = ".".join(parts[:3])
                soname_path = os.path.join(dest_dir, soname)
                if not os.path.exists(soname_path):
                    try:
                        if os.path.islink(soname_path):
                            os.remove(soname_path)
                    except OSError:
                        pass
                    try:
                        os.symlink(base, soname_path)
                    except OSError:
                        try:
                            shutil.copyfile(dest, soname_path)
                        except OSError:
                            pass
                    self.output.info(
                        f"ocl-icd: (re)created {soname_path} -> {base}")
        return True

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenCL")
        self.cpp_info.set_property("cmake_target_name", "OpenCL::OpenCL")
        self.cpp_info.set_property("pkg_config_name", "OpenCL")
        self.cpp_info.set_property("pkg_config_aliases", ["ocl-icd"])
        # aarch64 autotools triplets may install to lib64 instead of lib;
        # advertise both so CMakeDeps find_library() locates libOpenCL
        # regardless of which one `make install` used.
        self.cpp_info.libdirs = ["lib", "lib64"]
        self.cpp_info.libs = ["OpenCL"]
        # ocl_icd_loader uses dlopen/dlsym plus pthreads
        # (libOpenCL_la_LIBADD = $(PTHREAD_LIBS)); consumers of the static
        # archive need them explicitly.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
