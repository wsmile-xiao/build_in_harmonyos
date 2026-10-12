#!/usr/bin/env python3
"""Conan recipe -- sc 7.16-1.1.3 (curses spreadsheet calculator, configure+make)."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get


class ScConan(ConanFile):
    name = "sc"
    version = "7.16-1.1.3"
    description = "Curses-based spreadsheet calculator with vi-like key bindings"
    license = "Unlicense"
    homepage = "https://github.com/n-t-roff/sc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("spreadsheet", "terminal", "ncurses", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    generators = "VirtualBuildEnv"
    no_copy_source = True

    def export_sources(self):
        # Explicit export (units-filter/4.2.1 proven pattern): the
        # exports_sources attribute flattened pregenerated/* in the
        # 2026-10-08 preflight cache (recipe_folder held only 3 files),
        # so build() could never find the files via recipe_folder.
        # copy() with keep_path preserves pregenerated/<name> under
        # export_sources_folder, where build() now looks first.
        copy(self, "pregenerated/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        self.requires("ncurses/6.6")

    # NOTE: no build_requirements() on purpose.
    # History: tool_requires("bison/3.8.2") pulled conancenter m4 from source,
    # whose recipe re-execs CONFIG_SHELL=/data/service/hnp/bin/bash and fails
    # where that path is missing; tool_requires("btyacc/3.0") resolves to the
    # conancenter CMake-based recipe whose CMakeLists uses
    # cmake_minimum_required(<3.5), removed in CMake 4.x (device cmake 4.4.3).
    # The in-repo btyacc/3.0 (plain Makefile) is not yet published, so it
    # cannot satisfy a tool_requires in preflight/CI, and a single PR may only
    # contain one library. A previous round bootstrapped a private btyacc
    # inside build() using tools.build:compiler_executables verbatim, but the
    # 2026-10-08 preflight proved that conf value (/data/service/hnp/bin/clang)
    # does not exist on that machine (make: No such file or directory).
    # Hence this recipe needs NO yacc at build time at all: gram.c/y.tab.h are
    # pre-generated from gram.y (bison 3.8.2 -y -d, pure POSIX grammar) and
    # vendored under pregenerated/, installed into the source tree before make
    # so the Makefile's `gram.c: gram.y` YACC rule never fires.

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sc targets Linux/OHOS only, got {}".format(self.settings.os)
            )

    def layout(self):
        pass

    def _select_cc(self):
        """Resolve a usable C compiler without trusting one hardcoded path.

        tools.build:compiler_executables may point at a path that does not
        exist on the actual preflight worker (observed: conf c =
        /data/service/hnp/bin/clang, make Error 127). Prefer it only when the
        file exists; otherwise fall back to PATH lookup (HMBS + VirtualBuildEnv
        put the real toolchain on PATH, same pattern as ncurses' OHOS build
        which relies on shutil.which("clang")).
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        conf_cc = compilers.get("c")
        if conf_cc and os.path.isabs(conf_cc) and os.path.isfile(conf_cc):
            return conf_cc
        for cand in ("clang", "cc", "gcc"):
            found = shutil.which(cand)
            if found:
                self.output.info(
                    "sc: conf CC {!r} unusable, using PATH {!r}".format(
                        conf_cc, found
                    )
                )
                return found
        if conf_cc:
            # Last resort: return conf value and let make report the error.
            return conf_cc
        return "clang"

    def _find_vendored(self, basename):
        """Locate a vendored file via export_sources_folder first.

        The 2026-10-08 preflight proved the previous assumption wrong:
        exports_sources files do NOT live in recipe_folder (cache listing
        held only conandata.yml/conanfile.py/conanmanifest.txt despite
        the export log showing gram.c+y.tab.h copied). They live in
        export_sources_folder. Search there first (both the preserved
        pregenerated/<name> path and a basename walk), then fall back to
        the old recipe_folder walk for local development layouts.
        """
        roots = []
        for attr in ("export_sources_folder", "base_export_sources_folder",
                     "recipe_folder", "base_source_folder",
                     "base_recipe_folder"):
            try:
                value = getattr(self, attr, None)
            except Exception:
                value = None
            if value and os.path.isdir(value) and value not in roots:
                roots.append(value)
        for root in roots:
            exact = os.path.join(root, "pregenerated", basename)
            if os.path.isfile(exact):
                return exact
            # attribute-style export may have flattened to root level
            flat = os.path.join(root, basename)
            if os.path.isfile(flat):
                return flat
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                if basename in filenames:
                    return os.path.join(dirpath, basename)
        return None

    def _install_pregenerated_gram(self):
        """Install vendored gram.c/y.tab.h so make never invokes YACC."""
        src = self.source_folder
        gram_c = os.path.join(src, "gram.c")
        dot_h = os.path.join(src, "y.tab.h")
        if os.path.isfile(gram_c) and os.path.isfile(dot_h):
            return
        # Fast path (units-filter pattern): direct copy via conan copy tool
        # from export_sources_folder/pregenerated into the source tree.
        # Falls through to _find_vendored search when layout differs.
        try:
            exp = self.export_sources_folder
        except Exception:
            exp = None
        if exp and os.path.isdir(os.path.join(exp, "pregenerated")):
            try:
                copy(self, "*", src=os.path.join(exp, "pregenerated"),
                     dst=src)
            except Exception as e:
                self.output.warning(
                    "sc: direct pregenerated copy failed: {}".format(e))
        if os.path.isfile(gram_c) and os.path.isfile(dot_h):
            pass
        else:
            vend_c = self._find_vendored("gram.c")
            vend_h = self._find_vendored("y.tab.h")
            missing = [p for p, v in (("gram.c", vend_c), ("y.tab.h", vend_h)) if not v]
            if missing:
                diag = []
                for attr in ("export_sources_folder", "recipe_folder",
                             "base_source_folder"):
                    try:
                        d = getattr(self, attr, None)
                    except Exception:
                        d = None
                    if not d or not os.path.isdir(d):
                        diag.append("{}=<missing {}>".format(attr, d))
                        continue
                    try:
                        top = sorted(os.listdir(d))[:20]
                    except OSError:
                        top = ["<unlistable>"]
                    diag.append("{}={} top={}".format(attr, d, top))
                    hits = []
                    for dirpath, _dn, fns in os.walk(d):
                        for fn in fns:
                            if fn in ("gram.c", "y.tab.h"):
                                hits.append(os.path.join(dirpath, fn))
                                if len(hits) >= 10:
                                    break
                        if len(hits) >= 10:
                            break
                    diag.append("  vendored-hits={}".format(hits))
                raise ConanInvalidConfiguration(
                    "sc: vendored parser missing: {} ({})".format(
                        ", ".join(missing), "; ".join(diag)
                    )
                )
            if not os.path.isfile(gram_c):
                shutil.copy(vend_c, gram_c)
            if not os.path.isfile(dot_h):
                shutil.copy(vend_h, dot_h)
        # Ensure make treats generated files as newer than gram.y.
        gram_y = os.path.join(src, "gram.y")
        try:
            newer = os.path.getmtime(gram_y) + 5
            os.utime(gram_c, (newer, newer))
            os.utime(dot_h, (newer, newer))
        except OSError:
            pass
        self.output.info("sc: installed vendored gram.c/y.tab.h (no YACC needed)")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        cc = self._select_cc()
        make_cmd = os.environ.get("HMBS_MAKE") or "make"

        ncurses_pkg = self.dependencies["ncurses"].package_folder
        nc_inc = os.path.join(ncurses_pkg, "include")
        nc_lib = os.path.join(ncurses_pkg, "lib")
        self.output.info("sc: using CC={!r}".format(cc))
        os.environ["CC"] = cc
        cppflags = "-I{} -I{}/ncursesw".format(nc_inc, nc_inc)
        ldflags = "-L{}".format(nc_lib)
        if os.environ.get("CPPFLAGS"):
            cppflags = cppflags + " " + os.environ["CPPFLAGS"]
        if os.environ.get("LDFLAGS"):
            ldflags = ldflags + " " + os.environ["LDFLAGS"]
        os.environ["CPPFLAGS"] = cppflags
        os.environ["CFLAGS"] = cppflags
        os.environ["LDFLAGS"] = ldflags

        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        self.run("sh ./configure", cwd=self.source_folder, env="conanbuild")
        self._install_pregenerated_gram()
        self.run(
            '{} -j1 CC="{}" prefix="{}"'.format(
                make_cmd, cc, self.package_folder
            ),
            cwd=self.source_folder,
            env="conanbuild",
        )

        self.run("./psc -v", cwd=self.source_folder, env="conanbuild")

        upstream = {
            "status": "no_tests",
            "framework": "custom",
            "command": "no upstream test target",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "sc 7.16_1.1.3 audited: no tests/ or test/ directory, no TESTS/check target in Makefile.in, no ctest/gtest/pytest registration; only tutorial.sc sample file",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    def package(self):
        os.environ["PATH"] = "/system/bin:" + os.environ.get("PATH", "")
        self.run(
            'make install prefix="{}"'.format(self.package_folder),
            cwd=self.source_folder,
            env="conanbuild",
        )
        copy(self, "LICENSE", src=str(self.source_folder),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
