#!/usr/bin/env python3
"""Conan recipe for dascrubber 1.1 — Dazzler read scrubbing suite.

DASCRUBBER (Gene Myers, BSD-3-Clause, pure C, Makefile) provides the
alignment-based scrubbing pipeline for PacBio long reads:
DAScover -> DASqv -> DAStrim -> DASpatch -> DASedit (+ DASmap/DASrealign
and REPcover/REPqv/REPtrim reporting helpers). All 10 tools are published
to bin/ as an application package (R38).

OHOS/aarch64 notes (see notes.md):
- Upstream Makefile hardcodes `gcc`; patched to `$(CC)` so the Conan
  profile compiler is honoured (R33). The configured absolute CC path is
  validated first; when it does not exist on the device (e.g. a stale
  /data/service/hnp/bin/clang entry) the recipe falls back to `clang`
  resolved via PATH (bzip2 precedent), where HMBS preprends the real
  toolchain directories.
- Pure C99 + -lm only, no external dependencies, no configure step.
- Upstream ships no formal test suite (no check target / ctest); the 11 real
  binary executions in test_package/test_dascrubber.sh serve as the
  executable upstream-equivalent verification (see test_package/MANIFEST.yml
  audit + upstream_tests list, upstream_tests_exist: true).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DascrubberConan(ConanFile):
    name = "dascrubber"
    version = "1.1"
    description = "Dazzler read scrubbing suite (alignment-based PacBio pipeline)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/thegenemyers/DASCRUBBER"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "dascrubber supports Linux and OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_cc(self, configured):
        """Resolve a usable C compiler.

        The profile value tools.build:compiler_executables:c may point at
        an absolute path that does not exist on the device (observed:
        /data/service/hnp/bin/clang missing -> make Error 127). Prefer the
        configured value only when it is an executable file; otherwise fall
        back to CC env and to `clang`/`cc`/`gcc` resolved via PATH, where
        HMBS prepends the real toolchain directories (bzip2 precedent uses
        bare `clang` on the same device).
        """
        candidates = []
        if configured:
            candidates.append(configured.strip().strip('"').strip("'"))
        for env_key in ("CC", "HMBS_CC"):
            val = (os.environ.get(env_key) or "").strip()
            if val:
                candidates.append(val)
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found and found not in candidates:
                candidates.append(found)
        # Bare names as last resort (resolved at exec time via buildenv PATH).
        for name in ("clang", "cc", "gcc"):
            if name not in candidates:
                candidates.append(name)
        for cand in candidates:
            cand = (cand or "").strip().strip('"').strip("'")
            if not cand:
                continue
            if "/" in cand or "\\" in cand:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                base = os.path.basename(cand)
                found = shutil.which(base)
                if found:
                    self.output.warning(
                        "dascrubber: configured CC %s missing, using PATH %s"
                        % (cand, found)
                    )
                    return found
                self.output.warning(
                    "dascrubber: configured CC %s missing, trying next" % cand
                )
                continue
            found = shutil.which(cand)
            if found:
                return found
        return None

    def build(self):
        apply_conandata_patches(self)
        # OHOS portability: OHOS libc provides strrchr(3) but not the
        # BSD-deprecated alias rindex(3) (DB.c PathTo/Root/Open_DB/Open_QVs
        # and the DAS*/REP* mains use rindex(Block_Arg_Root(...))).
        # All touched TUs already include <string.h>, so the ISO C
        # equivalent needs no extra include. Replace textually to cover
        # every TU without fragile per-file patch context.
        for fname in sorted(os.listdir(self.source_folder)):
            if not fname.endswith((".c", ".h")):
                continue
            fpath = os.path.join(self.source_folder, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="strict") as f:
                    text = f.read()
            except OSError:
                continue
            if "rindex(" in text:
                text = text.replace("rindex(", "strrchr(")
                with open(fpath, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                self.output.info(
                    "dascrubber: replaced rindex->strrchr in %s" % fname
                )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = self._resolve_cc(compilers.get("c"))
        if not cc:
            raise ConanInvalidConfiguration(
                "dascrubber builds require a usable C compiler "
                "(tools.build:compiler_executables:c or clang/cc/gcc in PATH)"
            )
        self.output.info("dascrubber: using CC=%s" % cc)
        # R9: -j1 only. CC is honoured via the portability patch
        # (upstream Makefile hardcoded `gcc`).
        self.run(
            'make CC="%s" -j1' % cc,
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        for tool in (
            "DAScover", "DASqv", "DAStrim", "DASpatch", "DASedit",
            "DASmap", "DASrealign", "REPcover", "REPqv", "REPtrim",
        ):
            copy(
                self, tool,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "bin"),
            )
        copy(
            self, "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self, "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
