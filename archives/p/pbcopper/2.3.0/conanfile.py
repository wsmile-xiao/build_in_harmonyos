#!/usr/bin/env python3
"""Conan recipe for pbcopper 2.3.0.

pbcopper is the core PacBio C++ library of data structures, algorithms and
utilities (Cigar/Interval, CLI v2, JSON, logging, parallel, Pbmer, Poa).
Upstream builds with Meson (>= 0.57, C++20); the recipe obtains the versioned
Meson runner from the ohpcd prebuilt tool package (meson/1.11.0) instead of
relying on a worker-global executable.

OHOS notes:
- Meson resolves boost by scanning a root dir for headers + libraries. The
  recipe sets the Meson "boost_root" property to the Conan boost package
  folder and appends its include dir through cpp_args, the same mechanism
  used by bali-phy/4.1 (meson + boost precedent).
- Boost header gap: boost/1.91.0.1.1 only installs a filtered subset
  (filesystem/graph/iostreams/multiprecision/program_options/regex/thread)
  so header-only modules used by pbcopper (boost/numeric/ublas/* for
  AffineAlignment.cpp, boost/icl/* for Interval.h, plus their transitive
  header-only deps) are missing. At source() time the recipe fetches the
  canonical boost 1.91.0-1 cmake superproject tarball (same URL/sha256 as
  the boost/1.91.0.1.1 recipe, BSL-1.0) into boost-headers-src and merges
  every libs/*/include/boost tree into a build-folder overlay, prepended
  through cpp_args. No boost recipe is modified, no checked-in header
  copies, and no upstream algorithm code is patched.
- Upstream tests are 79 gtest source files (700 TEST/TEST_F macros) built
  into a single pbcopper_test binary plus a clang-format lint entry. The
  recipe runs the complete meson test suite inside build() and emits the
  HMBS_UPSTREAM_TEST_RESULT hard-gate marker. Counts come from the gtest
  XML report (pbcopper-gtest-unittests.xml), never from hardcoded values.
- The upstream result JSON is also packaged as res/upstream_test_result.json
  so test_package can re-emit the HMBS_UPSTREAM_TEST_RESULT marker (cppdap
  precedent).
"""

import json
import os
import re
import shutil
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PbcopperConan(ConanFile):
    name = "pbcopper"
    version = "2.3.0"
    description = (
        "Core C++ library for data structures, algorithms, and utilities "
        "for PacBio applications"
    )
    license = "BSD-3-Clause-Clear"
    homepage = "https://github.com/PacificBiosciences/pbcopper"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("pacbio", "bioinformatics", "cigar", "alignment", "ngs")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "tests": True,
    }
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanException(
                "pbcopper requires a POSIX-like target (Linux or OHOS), "
                "not %s" % self.settings.os
            )

    def requirements(self):
        # boost 1.91.0.1.1 ships OHOS binaries; pbcopper uses header-only
        # plus compiled boost libs via dependency('boost'). Transitive
        # flags propagate to consumers (R27: no bare version ranges).
        self.requires(
            "boost/1.91.0.1.1", transitive_headers=True, transitive_libs=True
        )
        # gtest as a host-context requirement (not test_requires): Meson
        # resolves dependency('gtest', main:true) via pkg-config
        # (gtest.pc/gtest_main.pc). A build-context test_requires is not
        # emitted under the plain 'gtest' pkg-config name, so the previous
        # PkgConfigDeps + test_requires round still reported "GTest found:
        # NO". Host context guarantees plain gtest.pc. Not propagated to
        # consumers (only the pbcopper_test binary links it).
        if bool(self.options.tests):
            self.requires(
                "gtest/1.17.0.1",
                transitive_headers=False,
                transitive_libs=False,
            )

    def build_requirements(self):
        # Meson is a published Conan build tool in ohpcd. Pin 1.11.0, the
        # version verified by canfigger/0.3.2 on OHOS.
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Canonical boost 1.91.0-1 superproject: header-only overlay source.
        # Same URL/sha256 as boost/1.91.0.1.1; extracted next to the pbcopper
        # sources so generate() can merge every libs/*/include/boost tree.
        get(
            self,
            **self.conan_data["boost_headers"],
            destination=os.path.join(self.source_folder, "boost-headers-src"),
            strip_root=True,
        )

    def generate(self):
        tc = MesonToolchain(self)
        tc.cpp_std = "c++20"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["default_library"] = (
            "shared" if bool(self.options.shared) else "static"
        )
        # Upstream registers the gtest suite when tests=true; build-docs
        # stays off (doxygen not in CI).
        tc.project_options["tests"] = (
            "true" if bool(self.options.tests) else "false"
        )
        tc.project_options["build-docs"] = "false"
        # Meson boost lookup: point at the Conan boost package folder and
        # add its headers explicitly (bali-phy/4.1 precedent). The canonical
        # header overlay comes first so missing header-only modules (icl,
        # ublas, ...) resolve even though the filtered boost package does
        # not install them; compiled libs still come from the Conan package.
        boost = self.dependencies["boost"]
        boost_pkg = boost.package_folder
        tc.properties["boost_root"] = [boost_pkg]
        tc.cpp_args.append("-I" + self._stage_boost_headers_overlay())
        tc.cpp_args.append("-I" + os.path.join(boost_pkg, "include"))
        tc.generate()
        # gtest is a host-context requirement when tests=True. Meson
        # dependency('gtest', main:true) resolves via pkg-config name
        # 'gtest_main' (mesonbuild/dependencies/dev.py: GTestDependencyPC
        # rewrites the name when main=True; cmake is not in the gtest
        # factory methods, so CMakeDeps cannot help). The two previous
        # rounds relied on PkgConfigDeps auto-generated filenames and
        # still reported "GTest found: NO" on the preflight machine, so
        # this round writes minimal gtest.pc/gtest_main.pc files with
        # guaranteed names pointing at the Conan gtest package instead
        # of depending on PkgConfigDeps component filename mapping.
        if bool(self.options.tests):
            self._write_gtest_pc_files()
        self._inject_archive_tools()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._meson_environment().vars(self).apply():
            meson.configure()
            self.run('meson compile -C "%s" -j1' % self.build_folder)
            if bool(self.options.tests):
                if cross_building(self):
                    self.output.warning(
                        "Skipping executable upstream tests during a cross "
                        "build; the pbcopper_test binary was compiled."
                    )
                else:
                    self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream meson test suite and emit the hard-gate marker.

        Counts come from the gtest XML report
        (pbcopper-gtest-unittests.xml, written by tests/meson.build via
        --gtest_output=xml:), falling back to parsing [  PASSED  ] /
        [  FAILED  ] lines in the meson test log. Never hardcoded.
        """
        log_path = os.path.join(self.build_folder, "meson_test.log")
        test_cmd = (
            'meson test -C "%s" --no-rebuild --print-errorlogs '
            '> "%s" 2>&1' % (self.build_folder, log_path)
        )
        self.run(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                out = handle.read()
        self.output.info("=== upstream meson test (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        discovered, passed, failed, skipped = self._parse_gtest_xml()
        if discovered == 0:
            discovered, passed, failed, skipped = self._parse_gtest_log(out)
        executed = passed + failed
        # Identity check: passed + failed must equal executed; executed must
        # not exceed discovered. Repair the data source, never the numbers.
        if not (
            discovered >= 0
            and executed >= 0
            and passed >= 0
            and failed >= 0
            and skipped >= 0
            and passed + failed == executed
            and executed <= discovered
            and executed + skipped <= discovered + skipped
        ):
            raise ConanException(
                "upstream test count identity failed: "
                "discovered=%d executed=%d passed=%d failed=%d skipped=%d"
                % (discovered, passed, failed, skipped)
            )
        gate_ok = (
            discovered > 0 and executed > 0 and failed == 0 and skipped == 0
        )
        status = "passed" if gate_ok else "failed"
        result = {
            "status": status,
            "framework": "gtest",
            "command": test_cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        # Package the result so test_package can re-emit it (cppdap precedent).
        res_dir = os.path.join(self.build_folder, "hmbs_res")
        os.makedirs(res_dir, exist_ok=True)
        save(
            self,
            os.path.join(res_dir, "upstream_test_result.json"),
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        if status != "passed":
            raise ConanException(
                "upstream pbcopper tests failed: executed=%d failed=%d "
                "skipped=%d" % (executed, failed, skipped)
            )

    def _parse_gtest_xml(self):
        """Parse pbcopper-gtest-unittests.xml; return (d, p, f, s)."""
        xml_path = os.path.join(
            self.build_folder, "pbcopper-gtest-unittests.xml"
        )
        if not os.path.isfile(xml_path):
            return (0, 0, 0, 0)
        try:
            root = ET.parse(xml_path).getroot()
            tests = int(root.get("tests", "0"))
            failures = int(root.get("failures", "0"))
            disabled = int(root.get("disabled", "0"))
            skipped = int(root.get("skipped", "0"))
            errors = int(root.get("errors", "0"))
            failed = failures + errors
            passed = tests - failed - skipped
            if passed < 0:
                return (0, 0, 0, 0)
            return (tests, passed, failed, skipped)
        except Exception as exc:
            self.output.warning(
                "pbcopper: gtest XML parse failed (%s); trying log fallback"
                % exc
            )
            return (0, 0, 0, 0)

    def _parse_gtest_log(self, out):
        """Fallback: parse gtest summary lines from the meson test log."""
        passed = 0
        failed = 0
        skipped = 0
        m = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s*test", out)
        if m:
            passed = int(m.group(1))
        m = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s*test", out)
        if m:
            failed = int(m.group(1))
        m = re.search(r"\[\s*SKIPPED\s*\]\s*(\d+)\s*test", out)
        if m:
            skipped = int(m.group(1))
        run = re.findall(r"^\[\s*RUN\s*\]", out, flags=re.MULTILINE)
        discovered = len(run) if run else passed + failed + skipped
        return (discovered, passed, failed, skipped)

    def package(self):
        with self._meson_environment().vars(self).apply():
            Meson(self).install()
        # Propagate the header-only boost overlay to consumers: the public
        # Interval.h includes boost/icl/*, so a build-folder-only -I is not
        # enough for test_package/CI consumers. Merge the staged overlay
        # boost/ tree (same 1.91.0 sources as the boost package) into this
        # package's include/ dir; compiled boost libs still come from the
        # boost/1.91.0.1.1 dependency.
        self._package_boost_headers_overlay()
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Ship the upstream result for test_package re-emission.
        res_src = os.path.join(self.build_folder, "hmbs_res")
        if os.path.isdir(res_src):
            copy(
                self,
                "upstream_test_result.json",
                src=res_src,
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )
        if bool(self.options.shared):
            self._materialize_shared_aliases()

    def package_info(self):
        self.cpp_info.libs = ["pbcopper"]
        self.cpp_info.set_property("cmake_file_name", "pbcopper")
        self.cpp_info.set_property("cmake_target_name", "pbcopper::pbcopper")
        self.cpp_info.set_property("pkg_config_name", "pbcopper")

    def _boost_headers_overlay_dir(self):
        return os.path.join(self.build_folder, "boost-headers-overlay")

    def _package_boost_headers_overlay(self):
        """Copy staged overlay boost/ headers into the package include dir."""
        overlay_boost = os.path.join(
            self._stage_boost_headers_overlay(), "boost"
        )
        if not os.path.isdir(overlay_boost):
            raise ConanException(
                "pbcopper: overlay boost dir missing at %s" % overlay_boost
            )
        dst_boost = os.path.join(self.package_folder, "include", "boost")
        os.makedirs(dst_boost, exist_ok=True)
        try:
            shutil.copytree(overlay_boost, dst_boost, dirs_exist_ok=True)
        except TypeError:
            for root, _dirs, files in os.walk(overlay_boost):
                rel = os.path.relpath(root, overlay_boost)
                dst_root = (
                    dst_boost if rel == "." else os.path.join(dst_boost, rel)
                )
                os.makedirs(dst_root, exist_ok=True)
                for name in files:
                    shutil.copy2(
                        os.path.join(root, name),
                        os.path.join(dst_root, name),
                    )
        for probe in (
            os.path.join(dst_boost, "icl", "discrete_interval.hpp"),
            os.path.join(dst_boost, "numeric", "ublas", "matrix.hpp"),
        ):
            if not os.path.isfile(probe):
                raise ConanException(
                    "pbcopper: packaged overlay incomplete, missing %s"
                    % probe
                )
        self.output.info(
            "pbcopper: packaged boost header overlay into %s" % dst_boost
        )

    def _stage_boost_headers_overlay(self):
        """Merge canonical boost header trees; return the overlay dir.

        Walks boost-headers-src for every include/boost subtree (depth
        agnostic: libs/*/include and libs/numeric/ublas/include alike) and
        merges each boost/ tree into one overlay include dir, plus a
        top-level boost/ dir when the superproject provides one. Markers
        for both previously-missing modules (icl + ublas) must exist.
        """
        staging = self._boost_headers_overlay_dir()
        markers = (
            os.path.join(staging, "boost", "icl", "discrete_interval.hpp"),
            os.path.join(
                staging, "boost", "numeric", "ublas", "matrix.hpp"
            ),
        )
        if all(os.path.isfile(m) for m in markers):
            return staging
        src_root = os.path.join(self.source_folder, "boost-headers-src")
        if not os.path.isdir(src_root):
            raise ConanException(
                "pbcopper: boost-headers-src missing in %s "
                "(conandata boost_headers not fetched)" % src_root
            )
        merged = 0
        for dirpath, dirnames, _filenames in os.walk(src_root):
            if os.path.basename(dirpath) != "include":
                continue
            boost_dir = os.path.join(dirpath, "boost")
            if not os.path.isdir(boost_dir):
                continue
            dst_boost = os.path.join(staging, "boost")
            os.makedirs(dst_boost, exist_ok=True)
            try:
                shutil.copytree(boost_dir, dst_boost, dirs_exist_ok=True)
            except TypeError:
                # Python < 3.8 fallback without dirs_exist_ok.
                for root, _dirs, files in os.walk(boost_dir):
                    rel = os.path.relpath(root, boost_dir)
                    dst_root = (
                        dst_boost
                        if rel == "."
                        else os.path.join(dst_boost, rel)
                    )
                    os.makedirs(dst_root, exist_ok=True)
                    for name in files:
                        shutil.copy2(
                            os.path.join(root, name),
                            os.path.join(dst_root, name),
                        )
            merged += 1
        top_boost = os.path.join(src_root, "boost")
        if os.path.isdir(top_boost):
            try:
                shutil.copytree(
                    top_boost,
                    os.path.join(staging, "boost"),
                    dirs_exist_ok=True,
                )
            except TypeError:
                pass
            merged += 1
        if merged == 0:
            raise ConanException(
                "pbcopper: no include/boost trees found under %s" % src_root
            )
        missing = [m for m in markers if not os.path.isfile(m)]
        if missing:
            raise ConanException(
                "pbcopper: boost header overlay incomplete, missing %s "
                "(merged %d trees from %s)" % (missing, merged, src_root)
            )
        self.output.info(
            "pbcopper: staged canonical boost header overlay (%d trees) "
            "into %s" % (merged, staging)
        )
        return staging

    def _write_gtest_pc_files(self):
        """Write guaranteed-name gtest.pc/gtest_main.pc for Meson.

        Meson looks up pkg-config name 'gtest_main' when main:true; the
        file names are fixed here instead of inheriting PkgConfigDeps
        component mapping. Paths come from the Conan gtest package.
        """
        gtest = self.dependencies["gtest"]
        pkg = gtest.package_folder
        libdir = os.path.join(pkg, "lib")
        includedir = os.path.join(pkg, "include")
        try:
            version = str(gtest.ref.version)
        except Exception:
            version = "1.17.0"
        base = (
            "prefix=%s\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: %s\n"
            "Description: GoogleTest %s\n"
            "Version: %s\n"
            "URL: https://github.com/google/googletest\n"
        ) % (pkg, "%s", "%s", version)
        gtest_pc = base % ("gtest", "without main() function") + (
            "Libs: -L${libdir} -lgtest\n"
            "Libs.private: -lpthread -lm\n"
            "Cflags: -I${includedir} -DGTEST_HAS_PTHREAD=1\n"
        )
        gtest_main_pc = base % ("gtest_main", "with main() function") + (
            "Requires: gtest\n"
            "Libs: -L${libdir} -lgtest_main\n"
            "Cflags: -I${includedir} -DGTEST_HAS_PTHREAD=1\n"
        )
        save(self, os.path.join(self.generators_folder, "gtest.pc"), gtest_pc)
        save(
            self,
            os.path.join(self.generators_folder, "gtest_main.pc"),
            gtest_main_pc,
        )
        self.output.info(
            "pbcopper: wrote manual gtest pc files libdir=%s includedir=%s "
            "version=%s" % (libdir, includedir, version)
        )

    def _meson_environment(self):
        """Return a Conan-scoped environment for Meson."""
        environment = Environment()
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir and os.path.isdir(bindir):
            environment.prepend_path("PATH", bindir)
        # Manual gtest.pc/gtest_main.pc live in the generators folder;
        # point pkg-config there so meson dependency('gtest', main:true)
        # resolves to the Conan test requirement.
        if bool(self.options.tests):
            environment.prepend_path(
                "PKG_CONFIG_PATH", self.generators_folder
            )
        return environment

    def _inject_archive_tools(self):
        """Add llvm-ar/llvm-ranlib when the profile omits Meson's names."""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or executables.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        ar = executables.get("ar") or (
            os.path.join(bindir, "llvm-ar") if bindir else ""
        )
        ranlib = executables.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else ""
        )
        for filename in ("conan_meson_cross.ini", "conan_meson_native.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not ar or not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content or "\nar =" in content:
                continue
            insertion = "[binaries]\nar = %r\n" % ar
            if ranlib:
                insertion += "ranlib = %r\n" % ranlib
            content = content.replace("[binaries]\n", insertion, 1)
            with open(machine_file, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _materialize_shared_aliases(self):
        """Copy versioned .so aliases as real files for the OHOS loader."""
        library_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(library_dir):
            return
        for name in os.listdir(library_dir):
            path = os.path.join(library_dir, name)
            if os.path.islink(path) and os.path.isfile(path):
                target = os.path.realpath(path)
                os.unlink(path)
                shutil.copy2(target, path)
