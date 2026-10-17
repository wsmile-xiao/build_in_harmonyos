#!/usr/bin/env python3
"""Conan recipe for libkkc-data 0.2.7 — language model data for libkkc.

libkkc-data is a data-only package: it ships the generated trie + cost
dictionary files that libkkc consumes for Japanese Kana-Kanji conversion.
The package contains no C/C++ artifacts; the only "compile" step is the
downstream data generation.

Upstream's `make` target (`data/models/Makefile.am`) is a thin wrapper
around two Python tools (tools/sortlm.py, tools/genfilter.py) that convert
the shipped 137 MB 3-gram arpa corpus into tuned lookup tables. This recipe
reproduces those exact commands so the model is always generated from the
official source corpus at build time (R19: no prebuilt artifacts).

sortlm.py needs the marisa trie twice: to save the `*.1gram.index` and
`*.input` lookup tables and to resolve every n-gram token to its key id.
Upstream does that through the `marisa` Python module. This recipe uses the
out-of-process helper `bindings/marisa_tool.cc` instead, compiled together
with the pinned upstream marisa 0.3.1 sources (conandata `marisa_sources`);
the helper performs the same marisa calls and reports every key id on stdout.
An in-process CPython extension module cannot be used here: on the OHOS build
worker the sandbox only allows loading shared objects that carry the
`hnp_file` security label, while build products live in user-owned paths
(hmdfs label), so importing a freshly compiled extension fails with
"Error loading shared library ... Permission denied" (hmmac security labels,
see knowledge entry E212).
"""
import glob
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


def _brief_error(exc):
    """One compact line describing why a compiler attempt failed."""
    text = " ".join(str(exc).split())
    return text[:240] if text else exc.__class__.__name__


class LibkkcDataConan(ConanFile):
    name = "libkkc-data"
    version = "0.2.7"
    description = "Language model data for the libkkc Japanese Kana-Kanji converter"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/ueno/libkkc"
    url = "https://github.com/ueno/libkkc"

    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "marisa_tool.cc",
             src=os.path.join(self.recipe_folder, "bindings"),
             dst=os.path.join(self.export_sources_folder, "bindings"))

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(self, **self.conan_data["marisa_sources"], strip_root=True,
            destination=self._marisa_root())

    def build(self):
        apply_conandata_patches(self)
        marisa_tool = self._build_marisa_tool()
        self._generate_model(marisa_tool)

    def package(self):
        src = os.path.join(self.build_folder, "sorted3")
        dst = os.path.join(self.package_folder, "lib", "libkkc", "models", "sorted3")
        os.makedirs(dst, exist_ok=True)
        for f in ("data.input", "data.1gram.index", "data.1gram", "data.2gram",
                  "data.2gram.filter", "data.3gram", "data.3gram.filter",
                  "metadata.json"):
            copy(self, f, src=src, dst=dst)

    def package_info(self):
        self.cpp_info.resdirs = ["lib"]

    def _marisa_root(self):
        """Directory holding the extracted upstream marisa 0.3.1 sources.

        Kept out of the libkkc source tree so the two extractions cannot be
        confused with each other, and out of `data/`, `tools/` and `bindings/`
        so nothing upstream globs the helper build by accident.
        """
        return os.path.join(self.source_folder, "build-tools", "marisa-trie")

    def _build_marisa_tool(self):
        """Compile bindings/marisa_tool.cc for the machine running the tools.

        The helper must execute where the data generation runs, so it is built
        for the build machine's own platform and never through the OHOS target
        flags/sysroot the profile applies to the package itself. marisa is
        compiled from the same pinned source in the same single command, so the
        helper and the trie implementation it links always share one ABI.

        Neither the compiler location nor the linker flags that work here are
        knowable in advance, so every candidate is compiled *and* executed: the
        selftest is the only proof that a compiler/flags combination yields a
        helper this machine can run. If none does, the build fails with the
        full attempt list rather than leaving a binary that cannot start.
        """
        bindings = os.path.join(self.source_folder, "bindings")
        marisa_root = self._marisa_root()
        marisa_src = sorted(glob.glob(os.path.join(
            marisa_root, "lib", "marisa", "**", "*.cc"), recursive=True))
        if not marisa_src:
            raise RuntimeError(
                "marisa sources not found under {0}; source() did not extract them".format(
                    marisa_root))
        out = os.path.join(self.build_folder,
                           "marisa_tool" + (".exe" if sys.platform == "win32" else ""))
        sources = " ".join('"{0}"'.format(s) for s in
                           [os.path.join(bindings, "marisa_tool.cc")] + marisa_src)
        include_flags = '-I"{0}" -I"{1}"'.format(
            os.path.join(marisa_root, "include"), os.path.join(marisa_root, "lib"))

        attempts = []
        for compiler in self._cxx_candidates():
            for flags in self._marisa_tool_flag_variants():
                label = "{0} [{1}]".format(compiler, " ".join(flags))
                if os.path.isfile(out):
                    os.remove(out)
                # R9: a single compiler process, matching the worker's parallel constraint.
                cmd = '"{cc}" {flags} {inc} {sources} -o "{out}"'.format(
                    cc=compiler, flags=" ".join(flags), inc=include_flags,
                    sources=sources, out=out)
                try:
                    self.run(cmd, env="conanbuild")
                except Exception as exc:
                    attempts.append("{0}: compile failed: {1}".format(label, _brief_error(exc)))
                    continue
                if not os.path.isfile(out):
                    attempts.append("{0}: compile produced no binary".format(label))
                    continue
                # Only a helper that actually starts on this machine is usable.
                try:
                    self.run('"{0}" selftest'.format(out), env="conanbuild")
                except Exception as exc:
                    attempts.append("{0}: selftest failed: {1}".format(label, _brief_error(exc)))
                    os.remove(out)
                    continue
                self.output.info("marisa_tool built with {0}".format(label))
                return out

        raise RuntimeError(
            "could not produce a runnable marisa_tool on this machine; attempts:\n  {0}"
            .format("\n  ".join(attempts)))

    # Last-resort build-machine C++ compilers. The CI worker keeps its toolchain
    # outside the recipe interpreter's PATH (/data/service/hnp/bin), so the
    # profile conf and these absolute paths are what makes the helper buildable
    # there at all; each one is still validated by compiling and running it.
    _CXX_FALLBACK_PATHS = (
        "/data/service/hnp/bin/clang++",
        "/data/service/hnp/bin/g++",
        "/data/service/hnp/bin/c++",
        "/usr/bin/clang++",
        "/usr/bin/g++",
        "/usr/bin/c++",
        "/bin/clang++",
        "/bin/g++",
        "/bin/c++",
    )

    def _cxx_candidates(self):
        """Ordered, de-duplicated C++ compilers that exist on the build machine.

        An explicit CXX and PATH come first so a build machine that exposes its
        compiler normally is used as-is; only then do the profile toolchain and
        the well-known install locations step in.
        """
        candidates = []

        def add(path):
            if not path:
                return
            path = str(path).strip()
            if path and path not in candidates:
                candidates.append(path)

        add(os.environ.get("CXX"))
        for name in ("c++", "g++", "clang++", "clang", "cc", "gcc"):
            add(shutil.which(name))
        executables = self.conf.get("tools.build:compiler_executables", default=None) or {}
        add(executables.get("cpp"))
        add(executables.get("c"))
        for path in self._CXX_FALLBACK_PATHS:
            add(path)

        usable = [path for path in candidates if os.path.isfile(path)]
        if not usable:
            raise RuntimeError(
                "no C++ compiler available for the build machine; looked for: {0}".format(
                    ", ".join(candidates) or "(nothing)"))
        return usable

    def _marisa_tool_flag_variants(self):
        """Flag sets to try, most self-contained first.

        `-static-libstdc++` embeds the C++ runtime in the helper (verified:
        OHOS clang++ then needs only libc.so instead of libc++_shared.so), so
        the helper starts without the SDK lib directory on the loader path; the
        plain build stays as a fallback for toolchains without the static
        archives. The selftest run after each attempt decides what really
        works, so a rejected flag only costs one compile.
        """
        base = ["-std=c++20", "-O2"]
        if sys.platform == "win32":
            # marisa's Mapper uses PrefetchVirtualMemory (Windows 8+); older
            # MinGW headers hide it behind this macro.
            return [base + ["-D_WIN32_WINNT=0x0A00"], base + ["-D_WIN32_WINNT=0x0A00", "-static"]]
        return [
            base + ["-static-libstdc++"],
            base,
            base + ["-static"],
        ]

    def _generate_model(self, marisa_tool):
        """Reproduce upstream data/models/Makefile.am sorted3-data.stamp."""
        py = sys.executable
        src = self.source_folder
        sortlm = os.path.join(src, "tools", "sortlm.py")
        genfilter = os.path.join(src, "tools", "genfilter.py")
        arpa = os.path.join(src, "data", "models", "text3", "data.arpa")
        sorted3 = os.path.join(self.build_folder, "sorted3")
        os.makedirs(sorted3, exist_ok=True)
        data = os.path.join(sorted3, "data")
        self.run('"{p}" -B "{s}" --marisa-tool "{t}" "{a}" "{d}"'.format(
                     p=py, s=sortlm, t=marisa_tool, a=arpa, d=data),
                 env="conanbuild")
        self.run('"{p}" -B "{g}" "{d}.2gram" "{d}.2gram.filter" 12'.format(
                     p=py, g=genfilter, d=data),
                 env="conanbuild")
        self.run('"{p}" -B "{g}" "{d}.3gram" "{d}.3gram.filter" 10'.format(
                     p=py, g=genfilter, d=data),
                 env="conanbuild")
        copy(self, "metadata.json",
             src=os.path.join(src, "data", "models", "sorted3"), dst=sorted3)
