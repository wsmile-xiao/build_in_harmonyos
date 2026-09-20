#!/usr/bin/env python3
"""Conan recipe — libfdt 1.7.2 (device-tree flat-blob library, dtc upstream).

Upstream: dtc release tarball dtc-1.7.2.tar.xz; this package builds and ships
only the libfdt library (libfdt.a / libfdt.so.1.7.2 + fdt.h/libfdt.h/
libfdt_env.h). The sibling tool package archives/d/device-tree-compiler/1.7.2
ships the CLI tools from the same source; this recipe is the library view
(package_type=library) for C consumers (-lfdt).

Build system: plain GNU Makefile (no configure). `make libfdt` builds both
the static archive and the versioned shared object; no third-party build or
runtime dependencies (libyaml/python/valgrind are optional and disabled by
absence, same as the sibling tool package).

OHOS notes:
- R33: CC/AR come from Conan conf (tools.build:compiler_executables), never
  from shell $CC (empty on CI workers). Fall back to clang/llvm-ar on PATH.
- Clang rejects the GCC-only -Wsuggest-attribute=format under -Werror; the
  conandata patch drops that single flag (same patch as the sibling
  device-tree-compiler recipe, proven in CI).
- HOSTOS detection: HarmonyOS uname falls through to the ELF branch
  (SHAREDLIB_EXT=so, -fPIC -shared), no patch needed.
- Upstream tests: tests/Makefile.tests defines the libfdt C suite
  (LIB_TESTS 66 + LIBTREE 3 + DL 2 = 71 binaries, all linked against the
  freshly built libfdt). build() runs `make tests` then drives the official
  harness `sh tests/run_tests.sh -t libfdt` (correct argv + dtb fixtures)
  and emits HMBS_UPSTREAM_TEST_RESULT with the harness TEST SUMMARY numbers.
  The full `make check` (2070 cases incl. dtc/fdtget/fdtoverlay end-to-end)
  is owned by the sibling tool package; this library package owns the
  libfdt testset.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


# tests/Makefile.tests (dtc v1.7.2) — LIB_TESTS_L (66) + LIBTREE (3) + DL (2).
_LIB_TESTS = (
    "get_mem_rsv",
    "root_node", "find_property", "subnode_offset", "path_offset",
    "get_name", "getprop", "get_prop_offset", "get_phandle",
    "get_path", "supernode_atdepth_offset", "parent_offset",
    "node_offset_by_prop_value", "node_offset_by_phandle",
    "node_check_compatible", "node_offset_by_compatible",
    "get_alias", "get_next_tag_invalid_prop_len",
    "char_literal",
    "sized_cells",
    "notfound",
    "addr_size_cells",
    "addr_size_cells2",
    "appendprop_addrrange",
    "stringlist",
    "setprop_inplace", "nop_property", "nop_node",
    "sw_tree1", "sw_states",
    "move_and_save", "mangle-layout", "nopulate",
    "open_pack", "rw_tree1", "rw_oom", "set_name", "setprop",
    "del_property", "del_node",
    "appendprop1", "appendprop2", "propname_escapes",
    "string_escapes", "references", "path-references", "phandle_format",
    "boot-cpuid", "incbin", "relref_merge",
    "extra-terminating-null",
    "dtbs_equal_ordered",
    "dtb_reverse", "dtbs_equal_unordered",
    "add_subnode_with_nops", "path_offset_aliases",
    "utilfdt_test",
    "integer-expressions",
    "property_iterate",
    "subnode_iterate",
    "overlay", "overlay_bad_fixup",
    "check_path", "check_header", "check_full",
    "fs_tree1",
    "truncated_property", "truncated_string", "truncated_memrsv",
    "asm_tree_dump", "value-labels",
)


class LibfdtConan(ConanFile):
    name = "libfdt"
    version = "1.7.2"
    description = "Flattened Device Tree library (read/create/modify FDT blobs)"
    license = "GPL-2.0-or-later OR BSD-2-Clause"
    homepage = "https://git.kernel.org/pub/scm/utils/dtc/dtc.git"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libfdt supports Linux/OHOS only, got {}".format(self.settings.os)
            )

    def _resolve_tool(self, key, fallbacks):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = compilers.get(key)
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for tool_name in fallbacks:
            found = shutil.which(tool_name)
            if found and os.path.isfile(found):
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        return fallbacks[0]

    def source(self):
        get(self, **self.conan_data["sources"])

    def _write_upstream_result(self, marker):
        """Persist harness marker and emit dual-channel evidence.

        Writes build_folder/upstream_test_result.json (package() copies it
        to res/ for test_package re-emit on Conan cache hits where build()
        is skipped) and emits HMBS_UPSTREAM_TEST_RESULT via both
        self.output.info and bare print so the HMBS parser finds it.
        No synthesis: numbers come from the real harness run above.
        """
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(marker, f)
        except Exception as e:
            self.output.warning("write upstream_test_result.json failed: {}".format(e))
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        self.output.info(line)
        print(line)

    def _run_libfdt_tests(self):
        """Drive the official upstream harness for the libfdt testset.

        Bare `./tests/<bin>` without argv yields "Bad configuration"
        (rc=1) for ~60/71 binaries — the harness supplies the dtb args
        (tree1_tests test_tree1.dtb, ...). Uses tests/run_tests.sh -t
        libfdt and parses its TEST SUMMARY. Returns
        (discovered, executed, passed, failed, skipped).
        """
        import re

        tests_dir = os.path.join(self.source_folder, "tests")
        # Guard: `make tests` must have produced the 71 binaries + fixtures.
        missing = []
        empty = []
        for name in _LIB_TESTS:
            path = os.path.join(tests_dir, name)
            if not os.path.isfile(path):
                missing.append(name)
            elif os.path.getsize(path) == 0:
                empty.append(name)
        if missing or empty:
            raise ConanInvalidConfiguration(
                "libfdt upstream tests incomplete: missing={} empty={}".format(
                    missing, empty
                )
            )
        # Falsifiability: dumptrees fixtures must be non-empty, otherwise
        # every comparison would pass on empty files.
        dtbs = [
            os.path.join(tests_dir, f)
            for f in os.listdir(tests_dir)
            if f.endswith(".dtb")
        ]
        nonempty = [p for p in dtbs if os.path.getsize(p) > 0]
        if len(nonempty) < 5:
            raise ConanInvalidConfiguration(
                "libfdt fixtures look empty: {} .dtb, {} non-empty".format(
                    len(dtbs), len(nonempty)
                )
            )
        # Harness env: prefer the just-built libfdt (SONAME resolution on
        # musl), force GNU stat format like the sibling tool package, and
        # pass through HMBS TMPDIR (worker /tmp is read-only).
        env = dict(os.environ)
        libfdt_dir = os.path.join(self.source_folder, "libfdt")
        prev_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = (
            libfdt_dir + (os.pathsep + prev_ld if prev_ld else "")
        )
        env["STATSZ"] = "stat -c %s"
        self.output.info(
            "libfdt harness LD_LIBRARY_PATH={} TMPDIR={} STATSZ={}".format(
                env["LD_LIBRARY_PATH"],
                env.get("TMPDIR", ""),
                env["STATSZ"],
            )
        )
        proc = subprocess.run(
            ["sh", "./run_tests.sh", "-t", "libfdt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=tests_dir,
            timeout=600,
            universal_newlines=True,
        )
        out = proc.stdout or ""
        # Echo tail for preflight diagnosis (kept short).
        for line in out.strip().splitlines()[-15:]:
            self.output.info("libfdt harness: {}".format(line))
        m_total = re.search(r"Total testcases:\s*(\d+)", out)
        m_pass = re.search(r"PASS:\s*(\d+)", out)
        m_fail = re.search(r"FAIL:\s*(\d+)", out)
        m_cfg = re.search(r"Bad configuration:\s*(\d+)", out)
        m_strange = re.search(r"Strange test result:\s*(\d+)", out)
        if not (m_total and m_pass and m_fail):
            raise ConanInvalidConfiguration(
                "libfdt harness produced no TEST SUMMARY (rc={} tail={!r})".format(
                    proc.returncode,
                    out.strip().splitlines()[-5:],
                )
            )
        total = int(m_total.group(1))
        passed = int(m_pass.group(1))
        failed = int(m_fail.group(1))
        ncfg = int(m_cfg.group(1)) if m_cfg else 0
        nstrange = int(m_strange.group(1)) if m_strange else 0
        if total == 0:
            raise ConanInvalidConfiguration("libfdt harness ran 0 tests")
        self.output.info(
            "libfdt upstream: {}/{} passed ({} failed, {} bad-config, {} strange)".format(
                passed, total, failed, ncfg, nstrange
            )
        )
        skipped = ncfg + nstrange
        failed_total = failed + nstrange
        return total, total, passed, failed_total, skipped

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_tool("c", ["clang", "cc"])
        ar = self._resolve_tool("ar", ["llvm-ar", "ar"])
        if not cc:
            raise ConanInvalidConfiguration("A C compiler is required to build libfdt")
        self.output.info("libfdt CC={} AR={}".format(cc, ar))
        # -j1 per R9. EXTRA_CFLAGS carries -fPIC for the shared object even
        # when the default CFLAGS path is used; harmless for the static arc.
        make_base = "make -j1 CC={} AR={} EXTRA_CFLAGS=\"-fPIC -O2\"".format(cc, ar)
        self.run(make_base + " libfdt", cwd=self.source_folder, env="conanbuild")
        # Build the upstream libfdt C suite (tests/ binaries + .dtb fixtures)
        # plus the dtc helper binary: run_tests.sh libfdt_tests needs
        # ../dtc via TEST_BINDIR for run_dtc_test fixture generation.
        self.run(make_base + " tests", cwd=self.source_folder, env="conanbuild")
        self.run(make_base + " dtc", cwd=self.source_folder, env="conanbuild")
        if can_run(self):
            discovered, executed, passed, failed, skipped = self._run_libfdt_tests()
            marker = {
                "status": "passed" if (failed == 0 and skipped == 0) else "failed",
                "framework": "dtc-libfdt-tests",
                "command": "sh tests/run_tests.sh -t libfdt",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
            self._write_upstream_result(marker)
            if failed != 0 or skipped != 0:
                raise ConanInvalidConfiguration(
                    "libfdt upstream tests failed: {}/{} passed (failed={}, skipped={})".format(
                        passed, discovered, failed, skipped
                    )
                )
        else:
            self.output.warning("cross-building: upstream runtime tests skipped")

    def package(self):
        libdir = os.path.join(self.source_folder, "libfdt")
        copy(self, "fdt.h", src=libdir, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libfdt.h", src=libdir, dst=os.path.join(self.package_folder, "include"))
        copy(self, "libfdt_env.h", src=libdir, dst=os.path.join(self.package_folder, "include"))
        copy(self, "GPL", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "BSD-2-Clause", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.options.shared:
            # Versioned .so plus soname/alias as real copies: the worker
            # filesystem may not support symlinks (same approach as libcidr).
            built = os.path.join(libdir, "libfdt.so.1.7.2")
            if not os.path.isfile(built):
                raise ConanInvalidConfiguration("shared libfdt not built: {}".format(built))
            lib_dir = os.path.join(self.package_folder, "lib")
            copy(self, "libfdt.so.1.7.2", src=libdir, dst=lib_dir)
            for alias in ("libfdt.so.1", "libfdt.so"):
                dst = os.path.join(lib_dir, alias)
                if not os.path.isfile(dst):
                    shutil.copy2(os.path.join(lib_dir, "libfdt.so.1.7.2"), dst)
        else:
            copy(self, "libfdt.a", src=libdir, dst=os.path.join(self.package_folder, "lib"))
        try:
            json_src = os.path.join(self.build_folder, "upstream_test_result.json")
            if os.path.isfile(json_src):
                copy(self, "upstream_test_result.json", src=self.build_folder,
                     dst=os.path.join(self.package_folder, "res"))
                self.output.info("copied upstream_test_result.json to res/")
            else:
                self.output.warning("upstream_test_result.json not found in build_folder, skip copy")
        except Exception as e:
            self.output.warning("copy upstream_test_result.json failed: {}".format(e))

    def package_info(self):
        self.cpp_info.libs = ["fdt"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
