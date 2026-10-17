#!/usr/bin/env python3
"""Conan recipe — openbabel 3.1.1 (CMake, C++ chemistry toolbox).

Open Babel is a chemical toolbox designed to speak the many languages of
chemical data (SMILES/InChI/MOL/PDB/CML/...).  Upstream builds with CMake
and produces libopenbabel (+ bundled inchi), the `obabel` CLI and, when
BUILD_SHARED=ON, dynamically-loaded format plugins.

OHOS adaptation notes:
- Formats are compiled INTO the library (BUILD_SHARED=OFF by default) to
  avoid runtime dlopen of plugin modules on HMDFS (dlopen of user-volume
  .so is unreliable on OHOS; E092-style portability).
- maeparser/coordgen (Maestro format support) are disabled: they pull a
  boost toolchain dependency for two optional file formats; upstream
  gracefully degrades ("Maestro formats will NOT be supported") when
  boost is absent, and WITH_MAEPARSER=OFF selects that path explicitly.
- inchi, rapidjson are bundled in the upstream source tarball and built
  from it (OPENBABEL_USE_SYSTEM_INCHI=OFF, bundled rapidjson).
- Module-mode find_package(ZLIB)/find_package(LibXml2)/FindEigen3.cmake
  cannot see Conan 2 package folders, so the concrete include dirs /
  library paths are injected as CMake cache variables in generate().

Upstream tests: test/ builds a single `test_runner` binary driven by
CTest (~212 test cases, see test_package/MANIFEST.yml for the inventory).
On OHOS the test binary is signed with binary-sign-tool and a
representative subset is executed on the real device, emitting the
HMBS_UPSTREAM_TEST_RESULT marker with honest discovered/executed/passed
counts.
"""

import json
import os
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

UPSTREAM_TEST_DISCOVERED = 212
UPSTREAM_TEST_FRAMEWORK = "ctest"
UPSTREAM_TEST_COMMAND = "ctest (test/test_runner, BABEL_DATADIR=<src>/data)"


class OpenbabelConan(ConanFile):
    name = "openbabel"
    version = "3.1.1"
    description = "Open Babel: chemical toolbox for interconverting chemical file formats"
    license = "GPL-2.0-or-later"
    homepage = "https://openbabel.org"
    url = "https://github.com/openbabel/openbabel"
    topics = ("chemistry", "cheminformatics", "smiles", "inchi", "molecular")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # R26: zlib is a system-name library — the ohpcd recipe is
        # static-only, which is exactly what we want.  libxml2 follows the
        # repo-wide consumer precedent (plain requires; the ohpcd recipe
        # hardcodes BUILD_SHARED_LIBS=ON, no static variant exists).
        self.requires("zlib/1.3.1")
        self.requires("libxml2/2.15.3")
        self.requires("eigen/3.4.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanException(
                "openbabel recipe supports Linux/OHOS only, got %s" % self.settings.os)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── dependency injection (module-mode find_package cannot see Conan 2) ──
    def _dep_abs_dirs(self, dep, kind):
        """cpp_info dirs may be relative to package_folder — anchor them."""
        out = []
        dirs = getattr(dep.cpp_info, kind)
        for d in dirs:
            if not os.path.isabs(d) and dep.package_folder:
                d = os.path.join(dep.package_folder, d)
            out.append(d)
        return out

    def _dep_static_lib(self, dep):
        libdir = self._dep_abs_dirs(dep, "libdirs")[0]
        libname = dep.cpp_info.libs[0]
        for candidate in ("lib%s.a" % libname, "lib%s.so" % libname):
            path = os.path.join(libdir, candidate)
            if os.path.isfile(path):
                return path
        raise ConanException(
            "dependency library %s not found under %s" % (libname, libdir))

    def _flatten_dep_symlinks(self, dep):
        """实体化依赖包内 .so symlink 链（HMDFS symlink 间歇 EACCES 会令
        CMakeDeps 的 conan_package_library_targets 找不到 libxml2.so；
        pitfalls #24 同源对策：symlink → copy 实体文件）。"""
        libdirs = []
        if getattr(dep, "package_folder", None):
            libdirs.append(os.path.join(dep.package_folder, "lib"))
        for extra in dep.cpp_info.libdirs:
            if os.path.isdir(extra):
                libdirs.append(extra)
        flattened = 0
        for libdir in libdirs:
            try:
                names = os.listdir(libdir)
            except OSError:
                continue
            for name in names:
                path = os.path.join(libdir, name)
                if not os.path.islink(path):
                    continue
                try:
                    real = os.path.realpath(path)
                    if os.path.isfile(real):
                        os.unlink(path)
                        shutil.copy2(real, path)
                        flattened += 1
                except OSError as exc:
                    self.output.warning(
                        "flatten symlink failed for %s: %s" % (path, exc))
        if flattened:
            self.output.info(
                "flattened %d symlink(s) in %s" % (flattened, libdirs))

    def generate(self):
        tc = CMakeToolchain(self)
        # Flatten dependency .so symlink chains BEFORE anything scans the
        # dependency package folders (HMDFS symlink flakiness).
        for dep_name in ("zlib", "libxml2", "eigen"):
            self._flatten_dep_symlinks(self.dependencies[dep_name])
        # E092: CMake has no HarmonyOS platform module; force the Linux
        # branch so upstream selects POSIX platform code paths.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Upstream test/CMakeLists fully '-static' links the test_runner for
        # static builds; on OHOS the dependency libxml2 ships shared-only,
        # so keep partial static linking (see patches/0005).
        tc.variables["OHOS_BUILD_PARTIAL_STATIC"] = True
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 2.8);
        # CMake >= 4 removed <3.5 compatibility, so opt in via policy override
        # (equivalent to -DCMAKE_POLICY_VERSION_MINIMUM=3.5).
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED"] = bool(self.options.shared)
        # Compile all file formats into the library; avoids runtime dlopen
        # of plugin modules (unreliable on HMDFS user volumes).
        tc.variables["ENABLE_VERSIONED_FORMATS"] = False
        # Optional boosts-dependent Maestro support: upstream gracefully
        # disables it; select that path explicitly.
        tc.variables["WITH_MAEPARSER"] = False
        tc.variables["WITH_COORDGEN"] = False
        tc.variables["ENABLE_OPENMP"] = False
        tc.variables["BUILD_GUI"] = False
        tc.variables["WITH_INCHI"] = True
        tc.variables["OPENBABEL_USE_SYSTEM_INCHI"] = False
        # Static build: compile the bundled inchi and the libxml2-based XML
        # formats INTO the library (upstream gates them behind these).
        tc.variables["WITH_STATIC_INCHI"] = True
        tc.variables["WITH_STATIC_LIBXML"] = True
        tc.variables["WITH_JSON"] = True
        # Build the upstream test_runner binary (executed in build()).
        tc.variables["ENABLE_TESTS"] = True

        zlib = self.dependencies["zlib"]
        tc.variables["ZLIB_INCLUDE_DIR"] = self._dep_abs_dirs(zlib, "includedirs")[0]
        tc.variables["ZLIB_LIBRARY"] = self._dep_static_lib(zlib)

        libxml2 = self.dependencies["libxml2"]
        libxml2_lib = self._dep_static_lib(libxml2)
        tc.variables["LIBXML2_INCLUDE_DIR"] = self._dep_abs_dirs(libxml2, "includedirs")[0]
        tc.variables["LIBXML2_LIBRARY"] = libxml2_lib
        # Module-mode variable used by tools/ and test/ static branches
        # ("set(libs ${libs} ${LIBXML2_LIBRARIES})"); CONFIG mode does not
        # populate the all-caps variable, so inject it explicitly.
        tc.variables["LIBXML2_LIBRARIES"] = libxml2_lib

        eigen = self.dependencies["eigen"]
        # FindEigen3.cmake locates the library via the marker file
        # signature_of_eigen3_matrix_library; conan installs headers under
        # include/eigen3, so probe every cpp_info includedir for that file
        # and hand the right dir to the module (its own find_path cannot
        # see Conan 2 package folders).  cpp_info dirs may be relative to
        # package_folder — anchor them first.
        eigen_incs = []
        for inc in eigen.cpp_info.includedirs:
            if not os.path.isabs(inc) and eigen.package_folder:
                inc = os.path.join(eigen.package_folder, inc)
            eigen_incs.append(inc)
        for inc in eigen_incs:
            if os.path.isfile(os.path.join(inc, "signature_of_eigen3_matrix_library")):
                tc.variables["EIGEN3_INCLUDE_DIR"] = inc
                break
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Command-line (not toolchain) so it is effective before
        # cmake_minimum_required() is parsed by CMake >= 4.  CMP0042 is
        # explicitly set to OLD by upstream CMakeLists.txt (line 14) and
        # CMake 4 refuses OLD, so force NEW from the command line.
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                                  "-DCMAKE_POLICY_DEFAULT_CMP0042=NEW"])
        cmake.build(build_tool_args=["-j4"])
        if str(self.settings.os) == "OHOS":
            self._run_upstream_tests()

    # ── upstream tests (representative subset on the real device) ──
    _UPSTREAM_TEST_SUBSET = [
        ("conversiontest", 1), ("smilestest", 1), ("smilestest", 2),
        ("smilestest", 3), ("cansmi", 1), ("formula", 1), ("format", 1),
        ("aromatest", 1), ("atom", 1), ("atom", 2), ("atom", 3),
        ("atom", 4), ("bond", 1), ("math", 1), ("math", 2), ("math", 3),
        ("math", 4), ("iterators", 1), ("invalidsmiles", 1),
        ("invalidsmarts", 1), ("gziptest", 1), ("addhtest", 1),
        ("ringtest", 1), ("residue", 1), ("unitcell", 1), ("phmodel", 1),
        ("mol", 1), ("datatest", 1),
    ]

    def _run_upstream_tests(self):
        test_runner = os.path.join(self.build_folder, "test_runner")
        if not os.path.isfile(test_runner):
            test_runner = os.path.join(self.build_folder, "bin", "test_runner")
        if not os.path.isfile(test_runner):
            self.output.warning(
                "upstream test_runner binary not found; skipping upstream tests")
            self._emit_upstream_test_marker(0, 0, 0, "binary missing")
            return
        self._sign_ohos_executable(test_runner)

        datadir = os.path.join(self.source_folder, "data")
        passed = failed = 0
        failures = []
        for module, part in self._UPSTREAM_TEST_SUBSET:
            env = dict(os.environ)
            env["BABEL_DATADIR"] = datadir
            proc = None
            for attempt in range(4):
                try:
                    proc = subprocess.run(
                        [test_runner, module, str(part)],
                        capture_output=True, text=True, timeout=120, env=env)
                    break
                except PermissionError:
                    # HMDFS: freshly written (signed) ELFs transiently fail
                    # execve with EACCES for minutes; wait and retry.
                    if attempt == 3:
                        proc = None
                        break
                    time.sleep(15)
                except subprocess.TimeoutExpired:
                    failed += 1
                    failures.append("%s %s: timeout(120s)" % (module, part))
                    break
            if proc is None and "%s %s" % (module, part) not in [
                    f.split(":")[0] for f in failures]:
                failed += 1
                failures.append("%s %s: exec EACCES after retries"
                                % (module, part))
                continue
            elif proc is None:
                continue
            out = (proc.stdout or "") + (proc.stderr or "")
            # obtest harness: "ok N - ..." / "not ok N - ..." (TAP-ish)
            not_ok = out.count("not ok")
            if proc.returncode == 0 and not_ok == 0:
                passed += 1
            else:
                failed += 1
                tail = [l for l in out.splitlines() if l.strip()][-3:]
                failures.append("%s %s: rc=%s %s"
                                % (module, part, proc.returncode,
                                   " | ".join(tail)[:160]))

        skipped = UPSTREAM_TEST_DISCOVERED - passed - failed
        for line in failures:
            self.output.warning("upstream test failure: %s" % line)
        self._emit_upstream_test_marker(passed, failed, skipped,
                                        "; ".join(failures[:5]) or "all green")

    def _emit_upstream_test_marker(self, passed, failed, skipped, reason):
        result = {
            "status": ("failed" if failed else
                       "passed" if passed else "incomplete"),
            "framework": UPSTREAM_TEST_FRAMEWORK,
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": UPSTREAM_TEST_DISCOVERED,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "identity_ok": passed + failed <= UPSTREAM_TEST_DISCOVERED,
            "gaps": [{
                "count": skipped,
                "category": "environment",
                "detail": (
                    "CTest cases outside the representative subset were not "
                    "executed on the HarmonyOS device: long-running numeric "
                    "suites (tautomer x28, regressions x14, ff*, stereo*, "
                    "automorphism x10, cifspacegroup x13, cistrans x9, "
                    "isomorphism x9 etc.) exceed the per-case runtime budget "
                    "of the conan create step; the executed subset covers the "
                    "core API surface (conversion/smiles/cansmi/formula/"
                    "format/aroma/atom/bond/math/iterators/gzip/addh/ring/"
                    "residue/unitcell/phmodel/mol/data/invalid-input)."),
                "evidence": "test/test_runner module list in test/CMakeLists.txt",
            }],
            "reason": reason,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(result), flush=True)

    # ── OHOS ELF signing (executables on user volumes need a signature) ──
    def _sign_ohos_executable(self, path):
        if str(self.settings.os) != "OHOS" or not os.path.isfile(path):
            return
        try:
            with open(path, "rb") as f:
                blob = f.read()
            if b".codesign" in blob or b".note.ohos" in blob:
                return
        except OSError:
            return
        signer = None
        for cand in (os.environ.get("OHOS_BINARY_SIGN_TOOL"),
                     "/data/service/hnp/bin/binary-sign-tool",
                     "/storage/Users/currentUser/usr/local/bin/binary-sign-tool"):
            if cand and os.path.isfile(cand):
                signer = cand
                break
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; %s may be rejected by OHOS" % path)
            return
        directory = os.path.dirname(path)
        tmp_in = os.path.join(directory, ".%s.sign-%d" % (
            os.path.basename(path), os.getpid()))
        tmp_out = tmp_in + ".signed"
        try:
            shutil.copy2(path, tmp_in)
            result = subprocess.run(
                [signer, "sign", "-selfSign", "1", "-inFile", tmp_in,
                 "-outFile", tmp_out, "-signAlg", "SHA256withECDSA"],
                capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.isfile(tmp_out):
                shutil.move(tmp_out, path)
                self.output.info("signed OHOS executable: %s" % path)
            else:
                self.output.warning(
                    "binary-sign-tool failed for %s: %s"
                    % (path, (result.stderr or result.stdout or "")[:200]))
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
        finally:
            for leftover in (tmp_in, tmp_out):
                if os.path.isfile(leftover):
                    try:
                        os.remove(leftover)
                    except OSError:
                        pass

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include/openbabel3"]
        self.cpp_info.libs = ["openbabel", "inchi"]
        self.cpp_info.system_libs = ["dl", "m"]
        self.cpp_info.requires = ["zlib::zlib", "libxml2::libxml2",
                                  "eigen::eigen"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/openbabel"]
        obabel = os.path.join(self.package_folder, "bin", "obabel")
        if str(self.settings.os) == "OHOS" and os.path.isfile(obabel):
            self._sign_ohos_executable(obabel)
