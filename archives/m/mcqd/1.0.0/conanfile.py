#!/usr/bin/env python3
"""Conan recipe — mcqd 1.0.0 (header-only max-clique library)."""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class McqdConan(ConanFile):
    name = "mcqd"
    version = "1.0.0"
    description = "MaxCliqueDyn: fast exact algorithm for finding a maximum clique in an undirected graph"
    license = "GPL-3.0-or-later"
    homepage = "https://gitlab.com/janezkonc/mcqd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("max-clique", "graph", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    # files/upstream/ holds a vendored copy of the 5 official tarball files
    # (tier-3 offline fallback, see source()). Exported with the recipe.
    exports_sources = "files/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mcqd requires a POSIX-like target (Linux or OHOS)")

    def source(self):
        # Three tiers, all from the official origin (no third-party mirror):
        #  1. official tag tarball (sha256 pinned in conandata);
        #  2. git clone of the official repository at the pinned v1.0.0
        #     commit (transport-level fallback, keeps working where only the
        #     archive endpoint is slow);
        #  3. vendored copy of the exact tarball files shipped with the
        #     recipe (offline fallback; preflight proves the whole gitlab.com
        #     host unreachable, so a local copy is the only guaranteed path).
        src = self.conan_data["sources"]
        try:
            get(self, url=src["url"], sha256=src["sha256"], strip_root=True)
            return
        except ConanException:
            self.output.warning(
                "official tarball download failed; falling back to git clone "
                "of the official repository tag v1.0.0"
            )
        clone_folder = os.path.join(self.source_folder, "_upstream")
        try:
            git = Git(self, clone_folder)
            git.clone(url=src["git_url"], target=".")
            # Pin the exact v1.0.0 commit (annotated tag points at it); full
            # clone is tiny (2 commits) so no --depth is used. Trust only
            # this just-cloned directory, do not persist a global
            # safe.directory exception.
            git.run('-c safe.directory="%s" checkout %s' % (clone_folder, src["commit"]))
            for entry in os.listdir(clone_folder):
                if entry != ".git":
                    shutil.move(os.path.join(clone_folder, entry), self.source_folder)
        except ConanException:
            self.output.warning(
                "git clone failed; using vendored copy of the official v1.0.0 files"
            )
        finally:
            shutil.rmtree(clone_folder, ignore_errors=True)
        if os.path.isfile(os.path.join(self.source_folder, "mcqd.h")):
            return
        # Tier 3: files/upstream/ was extracted from the official tarball
        # whose sha256 matches conandata, so content is identical to tiers
        # 1-2 by construction (COPYING/README/mcqd.cpp/mcqd.h/test.clq).
        copy(self, "*", os.path.join(self.export_sources_folder, "files", "upstream"), self.source_folder)
        if not os.path.isfile(os.path.join(self.source_folder, "mcqd.h")):
            raise ConanException("vendored upstream copy missing mcqd.h")

    def _resolve_cxx(self):
        # HMBS preflight proved tools.build:compiler_executables can point at
        # an inaccessible absolute path (e.g. /data/service/hnp/bin/clang++
        # reported "inaccessible or not found"). Only trust an absolute path
        # when the file exists and is executable; otherwise fall back to a
        # PATH lookup (hmbs prepends real tool dirs to buildenv PATH) and
        # finally to generic compiler names.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        candidates = []
        for key in ("cpp", "c"):
            val = compilers.get(key)
            if val:
                candidates.append(val)
                base = os.path.basename(val)
                if base and base != val:
                    candidates.append(base)
        candidates.extend(["clang++", "c++", "g++", "cc", "clang"])
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                resolved = shutil.which(cand)
                if resolved:
                    return resolved
                continue
            resolved = shutil.which(cand)
            if resolved:
                return resolved
        return compilers.get("cpp") or compilers.get("c") or "clang++"

    def build(self):
        apply_conandata_patches(self)
        cxx = self._resolve_cxx()
        self.output.info(f"mcqd: using CXX={cxx}")
        src = os.path.join(self.source_folder, "mcqd.cpp").replace("\\", "/")
        graph = os.path.join(self.source_folder, "test.clq").replace("\\", "/")
        exe = os.path.join(self.build_folder, "mcqd_upstream").replace("\\", "/")
        self.run(f'"{cxx}" -O2 -std=c++17 "{src}" -o "{exe}"', env="conanbuild")
        if not can_run(self):
            self.output.warning("cross-building: upstream example compiled, runtime check skipped on build host")
            return
        log_path = os.path.join(self.build_folder, "upstream_test.log").replace("\\", "/")
        self.run(f'"{exe}" "{graph}" > "{log_path}" 2>&1')
        with open(os.path.join(self.build_folder, "upstream_test.log"), encoding="utf-8", errors="replace") as handle:
            out = handle.read()
        if not out.strip():
            raise RuntimeError("upstream example produced empty output (fixture may not have loaded)")
        self.output.info("=== upstream mcqd example (tail) ===")
        for line in out.splitlines()[-12:]:
            self.output.info(line)
        example_headers = len(re.findall(r"---------- Example \d+", out))
        sizes = []
        for match in re.finditer(r"^Size = (\d+)\s*$", out, flags=re.MULTILINE):
            sizes.append(int(match.group(1)))
        discovered = 2
        executed = example_headers if example_headers <= discovered else discovered
        passed = len([s for s in sizes[:executed] if s > 0])
        failed = executed - passed
        skipped = 0
        status = "passed" if (executed == discovered and failed == 0 and passed == discovered) else "failed"
        result = {
            "status": status,
            "framework": "custom_example",
            "command": "mcqd test.clq (Example 1 mcq + Example 2 mcqdyn)",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if status != "passed":
            raise RuntimeError(f"upstream mcqd examples failed: executed={executed} passed={passed} sizes={sizes}")

    def package(self):
        copy(self, "mcqd.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
