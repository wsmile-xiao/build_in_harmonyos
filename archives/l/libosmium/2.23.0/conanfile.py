#!/usr/bin/env python3
"""Conan recipe - libosmium 2.23.0 (header-only).

The feature headers include external headers unconditionally
(zlib.h / bzlib.h / lz4.h / expat.h / protozero), so all five dependencies
are propagated to consumers. The upstream unit test suite (test/t, Catch
2.13.10 vendored in test/catch) is compiled and executed in build(); the
three tests gated on GEOS/GDAL (not available) stay excluded, mirroring the
upstream ENABLE_IF conditions.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# (group, name, flags) extracted from upstream test/CMakeLists.txt.
# Z=zlib B=bzip2 T=threads X=expat P=protozero SKIP=GEOS/GDAL gated.
UPSTREAM_TESTS = [
    ("area", "test_area_id", ""),
    ("area", "test_assembler", ""),
    ("area", "test_node_ref_segment", ""),
    ("osm", "test_area", "Z"),
    ("osm", "test_box", "Z"),
    ("osm", "test_changeset", "Z"),
    ("osm", "test_crc", "Z"),
    ("osm", "test_entity_bits", ""),
    ("osm", "test_location", ""),
    ("osm", "test_location_extra", ""),
    ("osm", "test_metadata", ""),
    ("osm", "test_node", "Z"),
    ("osm", "test_node_ref", ""),
    ("osm", "test_object_comparisons", ""),
    ("osm", "test_relation", "Z"),
    ("osm", "test_timestamp", ""),
    ("osm", "test_types_from_string", ""),
    ("osm", "test_way", "Z"),
    ("memory", "test_buffer_basics", ""),
    ("memory", "test_buffer_node", ""),
    ("memory", "test_buffer_purge", ""),
    ("memory", "test_callback_buffer", ""),
    ("memory", "test_item", ""),
    ("memory", "test_type_is_compatible", ""),
    ("builder", "test_attr", ""),
    ("builder", "test_object_builder", ""),
    ("geom", "test_coordinates", ""),
    ("geom", "test_exception", ""),
    ("geom", "test_factory_with_projection", ""),
    ("geom", "test_geojson", ""),
    ("geom", "test_geos", "SKIP"),
    ("geom", "test_mercator", ""),
    ("geom", "test_ogr", "SKIP"),
    ("geom", "test_ogr_wkb", "SKIP"),
    ("geom", "test_projection", ""),
    ("geom", "test_tile", ""),
    ("geom", "test_wkb", ""),
    ("geom", "test_wkt", ""),
    ("handler", "test_apply", "X"),
    ("handler", "test_check_order_handler", ""),
    ("handler", "test_dynamic_handler", ""),
    ("index", "test_dump_and_load_index", ""),
    ("index", "test_dump_sparse_as_array", ""),
    ("index", "test_file_based_index", ""),
    ("index", "test_id_set", ""),
    ("index", "test_id_to_location", ""),
    ("index", "test_nwr_array", ""),
    ("index", "test_object_pointer_collection", ""),
    ("index", "test_relations_map", ""),
    ("io", "test_compression_factory", ""),
    ("io", "test_file_formats", ""),
    ("io", "test_nocompression", ""),
    ("io", "test_output_utils", ""),
    ("io", "test_file_seek", ""),
    ("io", "test_string_table", ""),
    ("io", "test_print_width", "Z"),
    ("io", "test_bzip2", "B"),
    ("io", "test_gzip", "Z"),
    ("io", "test_opl_parser", "T"),
    ("io", "test_output_iterator", "T"),
    ("io", "test_pbf", "P"),
    ("io", "test_reader", "XP"),
    ("io", "test_reader_fileformat", "T"),
    ("io", "test_reader_with_mock_decompression", "X"),
    ("io", "test_reader_with_mock_parser", "T"),
    ("io", "test_writer", "X"),
    ("io", "test_writer_with_mock_compression", "X"),
    ("io", "test_writer_with_mock_encoder", "X"),
    ("relations", "test_members_database", ""),
    ("relations", "test_read_relations", "X"),
    ("relations", "test_relations_database", ""),
    ("relations", "test_relations_manager", "X"),
    ("storage", "test_item_stash", ""),
    ("tags", "test_filter", ""),
    ("tags", "test_operators", ""),
    ("tags", "test_tag_list", ""),
    ("tags", "test_tag_matcher", ""),
    ("tags", "test_tags_filter", ""),
    ("thread", "test_pool", "T"),
    ("thread", "test_queue", "T"),
    ("thread", "test_util", "T"),
    ("util", "test_config", ""),
    ("util", "test_delta", ""),
    ("util", "test_double", ""),
    ("util", "test_file", ""),
    ("util", "test_memory", ""),
    ("util", "test_memory_mapping", ""),
    ("util", "test_minmax", ""),
    ("util", "test_misc", ""),
    ("util", "test_options", ""),
    ("util", "test_string", ""),
    ("util", "test_string_matcher", ""),
    ("util", "test_timer_disabled", ""),
    ("util", "test_timer_enabled", ""),
]

SKIPPED_REASON = (
    "geom test_geos test_ogr test_ogr_wkb - upstream ENABLE_IF gated on "
    "GEOS/GDAL which are not available"
)


class LibosmiumConan(ConanFile):
    name = "libosmium"
    version = "2.23.0"
    description = "Osmium - fast and flexible C++ toolkit for OpenStreetMap data (header-only)"
    license = "BSL-1.0"
    homepage = "https://osmcode.org/libosmium/"
    url = "https://github.com/osmcode/libosmium"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("protozero/1.8.2")
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("lz4/1.10.0")
        self.requires("expat/2.8.2.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if not cross_building(self):
            self._run_upstream_tests()

    def _dep_paths(self, name, kind):
        dep = self.dependencies[name]
        info = dep.cpp_info
        vals = list(getattr(info, kind, None) or [])
        for comp in getattr(info, "components", {}).values():
            vals.extend(getattr(comp, kind, None) or [])
        out = []
        for d in vals:
            out.append(d if os.path.isabs(d) else os.path.join(dep.package_folder, d))
        return out

    def _dep_libs(self, name):
        dep = self.dependencies[name]
        info = dep.cpp_info
        libs = list(info.libs or [])
        for comp in getattr(info, "components", {}).values():
            libs.extend(comp.libs or [])
        return libs

    def _cxx(self):
        comp = self.conf.get("tools.build:compiler_executables")
        if comp and comp.get("cpp"):
            return comp["cpp"]
        found = shutil.which("clang++") or shutil.which("c++")
        if not found:
            raise ConanException("no C++ compiler found for upstream tests")
        return found

    def _run_upstream_tests(self):
        src = self.source_folder
        bld = self.build_folder
        incs = [os.path.join(src, "include"), os.path.join(src, "test", "include"),
                os.path.join(src, "test", "catch")]
        for name in ("protozero", "zlib", "bzip2", "lz4", "expat"):
            incs.extend(self._dep_paths(name, "includedirs"))
        inc_flags = " ".join("-I" + d for d in incs)
        cxx = self._cxx()

        lib_flags = {}
        all_libdirs = []
        for flag, dep in (("Z", "zlib"), ("B", "bzip2"), ("X", "expat")):
            dirs = self._dep_paths(dep, "libdirs")
            all_libdirs.extend(dirs)
            parts = ["-L" + d for d in dirs]
            parts += ["-l" + l for l in self._dep_libs(dep)]
            lib_flags[flag] = " ".join(parts)
        # Every test links all available compression/XML libs: FindOsmium puts
        # zlib into both OSMIUM_PBF_LIBRARIES and OSMIUM_XML_LIBRARIES, so the
        # P/XML split alone under-links io tests (probed: undefined inflate).
        # The shared libs resolve at run time via RPATH (probed: without it
        # every test dies on "Error loading shared library libexpat.so").
        rpaths = " ".join("-Wl,-rpath," + d for d in all_libdirs)
        common_libs = rpaths + " " + " ".join(lib_flags[f] for f in ("Z", "B", "X"))

        logdir = os.path.join(bld, "testlogs")
        enabled = [t for t in UPSTREAM_TESTS if t[2] != "SKIP"]
        build_cmds = []
        run_cmds = []
        for grp, name, flags in enabled:
            tid = f"{grp}_{name}"
            tu = os.path.join(src, "test", "t", grp, name + ".cpp")
            main = os.path.join(src, "test", "test_main.cpp")
            exe = os.path.join(bld, tid)
            blog = shlex.quote(os.path.join(logdir, tid + ".build.log"))
            cmd = (f"{shlex.quote(cxx)} -std=c++17 -pthread {inc_flags} "
                   f"{shlex.quote(tu)} {shlex.quote(main)} {common_libs} -o {shlex.quote(exe)}")
            build_cmds.append((tid, cmd, blog))
            run_cmds.append((tid, exe))

        lines = ["#!/bin/sh", "# generated by conanfile.py - upstream unit suite",
                 f"rm -rf '{logdir}'", f"mkdir -p '{logdir}'", "FAILED=0"]
        # OHOS musl ignores DT_RUNPATH; conanbuild's LD_LIBRARY_PATH does not
        # carry every dep libdir (probed: expat missing) - export them all.
        ldpath = ":".join(self._dep_paths(n, "libdirs")[0]
                          for n in ("protozero", "zlib", "bzip2", "lz4", "expat")
                          if self._dep_paths(n, "libdirs"))
        lines.append(f'export LD_LIBRARY_PATH="{ldpath}$LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH"')
        # File-fixture tests open "t/..." relative paths: run from test/.
        lines.append(f"cd '{os.path.join(src, 'test')}'")
        # Compile in parallel batches of 4 (independent TUs, proven safe).
        batch = 4
        for i in range(0, len(build_cmds), batch):
            lines.append("pids=")
            for tid, cmd, blog in build_cmds[i:i + batch]:
                lines.append(f"( {cmd} > {blog} 2>&1 ) & pids=\"$pids $!\"")
            lines.append("for p in $pids; do wait $p || FAILED=$((FAILED+1)); done")
        # Build failures are fatal before any run: re-check each binary exists.
        lines.append(f"for t in {' '.join(t[0] for t in run_cmds)}; do")
        lines.append(f"  [ -x \"{bld}/$t\" ] || {{ echo BUILD_FAILED $t; FAILED=$((FAILED+1)); }}")
        lines.append("done")
        lines.append("if [ $FAILED -gt 0 ]; then echo TOTAL_FAILED_BUILD $FAILED; exit 1; fi")
        # Run sequentially with per-test logs and Catch summary assertions.
        for tid, exe in run_cmds:
            rlog = shlex.quote(os.path.join(logdir, tid + ".run.log"))
            # Catch exits non-zero iff a test failed; suites without enabled
            # cases exit 0 ("No tests ran") - same as upstream ctest counting.
            lines.append(f"{shlex.quote(exe)} > {rlog} 2>&1; rc=$?")
            lines.append(f"echo RUN {tid} rc=$rc")
            lines.append("if [ $rc -ne 0 ]; then FAILED=$((FAILED+1)); fi")
        lines.append("echo TOTAL_ENABLED %d" % len(enabled))
        lines.append("echo TOTAL_FAILED $FAILED")
        lines.append("test $FAILED -eq 0")

        script = os.path.join(bld, "run_upstream_tests.sh")
        with open(script, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(script, 0o755)
        self.run(f"sh {shlex.quote(script)}", cwd=src, env="conanbuild")

        skipped = sum(1 for _, _, fl in UPSTREAM_TESTS if fl == "SKIP")
        self.output.info(
            "UPSTREAM LEDGER entries=%d executed=%d passed=%d failed=0 skipped=%d (%s)"
            % (len(UPSTREAM_TESTS), len(enabled), len(enabled), skipped, SKIPPED_REASON)
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = []
        # Cross-package component references need the "dep::component" form.
        self.cpp_info.requires = [
            "protozero::protozero",
            "zlib::zlib",
            "bzip2::bzip2",
            "lz4::lz4",
            "expat::expat",
        ]
