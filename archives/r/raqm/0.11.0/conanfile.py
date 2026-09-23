#!/usr/bin/env python3
"""Conan recipe — raqm 0.11.0 (Meson).

Raqm is a library that encapsulates complex text layout logic (bidirectional
text resolution via FriBidi, script itemization and shaping via HarfBuzz, and
FreeType face management). It is the RTL/bidi rendering middle layer used by
multiple stacks (e.g. ImageMagick/Pillow text rendering).

Build system: meson (upstream 0.11.0 ships meson.build only; the autotools
files were removed upstream after 0.9.x).

Upstream tests: 51 meson test() targets (49 .test fixtures driven by
tests/runtest.py through the raqm-test harness + grapheme-break +
detected-direction C tests). The recipe build() re-runs the whole suite via
`meson test` inside conan create; the exploration build on the OHOS aarch64
device confirmed Ok=51 / Fail=0.

Deps: freetype, harfbuzz, fribidi — resolved through PkgConfigDeps (.pc
names: freetype2 / harfbuzz / fribidi). Conan-side quirks handled by this
recipe:
  * fribidi headers live in include/fribidi/ while its .pc only exposes
    include/ — the subdirectory is injected into MesonToolchain c_args so
    `#include <fribidi.h>` resolves.
  * The ambient LD_LIBRARY_PATH can carry whitespace-polluted entries from
    the device environment; the OHOS loader then fails to resolve
    libc++_shared.so for /data/service/hnp/bin/ninja during meson setup
    ("Could not detect Ninja v1.8.2 or newer"). build() normalizes it.
  * Shared libraries produced by the toolchain chain carry a .codesign
    section that is invalid for the device loader after meson install, so
    package() re-signs libraqm.so.* with binary-sign-tool (same approach as
    the harfbuzz recipe in this repo).
"""
import glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class RaqmConan(ConanFile):
    name = "raqm"
    version = "0.11.0"
    description = "Raqm — a library for complex text layout (bidirectional text, shaping and script itemization on top of HarfBuzz, FriBidi and FreeType)"
    license = "MIT"
    homepage = "https://github.com/HOST-Oman/libraqm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("text", "bidi", "shaping", "harfbuzz", "fribidi", "freetype", "rtl")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # freetype is pulled transitively by harfbuzz, but raqm's meson.build
        # resolves freetype2 independently (raqm.c uses FT_Face directly via
        # hb-ft + raqm_set_freetype_face), so declare it explicitly.
        self.requires("freetype/2.14.3")
        self.requires("harfbuzz/14.3.0")
        self.requires("fribidi/1.0.16")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "raqm 0.11.0 is adapted for Linux/OHOS, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "docs": "false",
                "tests": "true",
                "sheenbidi": "false",
                "default_library": "shared" if self.options.shared else "static",
            }
        )
        # fribidi headers live in include/fribidi/ while its .pc only exposes
        # include/ — inject the subdirectory so `#include <fribidi.h>` (and
        # the meson dependency probe) resolves during compilation.
        fribidi_pkg = self.dependencies["fribidi"].package_folder
        fribidi_inc = os.path.join(fribidi_pkg, "include", "fribidi")
        if os.path.isdir(fribidi_inc):
            extra = "-I%s" % fribidi_inc
            if extra not in toolchain.c_args:
                toolchain.c_args.append(extra)
        toolchain.generate()

        # CI workers run meson 1.11.x whose [binaries] handling resolves bare
        # tool names ('llvm-ar') against the ambient PATH — which does NOT
        # include /data/service/hnp/bin on those workers, so meson setup dies
        # with "Unknown linker(s): [['llvm-ar']]". Rewrite the machine files
        # to pin absolute paths for ar/ranlib/nm derived from the compiler
        # directory (same approach as the harfbuzz/cputool recipes here).
        self._pin_binaries_in_machine_files()

    def _pin_binaries_in_machine_files(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c", "")
        compiler_dir = os.path.dirname(os.path.abspath(compiler)) if compiler else ""

        tool_paths = {}
        for tool in ("ar", "ranlib", "nm"):
            for candidate in (
                compiler_dir and os.path.join(compiler_dir, "llvm-%s" % tool),
                "/data/service/hnp/bin/llvm-%s" % tool,
            ):
                if candidate and os.path.isfile(candidate):
                    tool_paths[tool] = candidate
                    break

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            lines = []
            changed = False
            in_binaries = False
            saw = set()
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("[binaries]"):
                    in_binaries = True
                    lines.append(line)
                    continue
                if stripped.startswith("[") and stripped.endswith("]"):
                    if in_binaries:
                        # before leaving the section, add any missing tools
                        for tool, tp in tool_paths.items():
                            if tool not in saw:
                                lines.append("%s = '%s'" % (tool, tp))
                                changed = True
                    in_binaries = False
                    lines.append(line)
                    continue
                if in_binaries and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    saw.add(key)
                    if key in tool_paths and "/" not in value:
                        lines.append("%s = '%s'" % (key, tool_paths[key]))
                        changed = True
                        continue
                lines.append(line)
            if in_binaries:
                for tool, tp in tool_paths.items():
                    if tool not in saw:
                        lines.append("%s = '%s'" % (tool, tp))
                        changed = True
            if changed:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)

        # Device quirk: the ambient LD_LIBRARY_PATH can carry whitespace
        # injected by the system env (e.g. "...chipset-pub-sdk: /system/lib64").
        # The OHOS dynamic loader fails to resolve libc++_shared.so for
        # /data/service/hnp/bin/ninja when any colon-separated entry holds
        # leading/trailing whitespace, which breaks meson's ninja detection
        # ("Could not detect Ninja v1.8.2 or newer", exit 127 from Popen).
        # Normalize every entry before any meson subprocess runs.
        self._sanitize_ld_library_path()

        meson = Meson(self)
        meson.configure()
        meson.build()

        # Upstream test suite: 51 targets (49 runtest.py fixtures + 2 C tests).
        # Executables link the shared conan deps, so expose their libdirs via
        # LD_LIBRARY_PATH while running the suite on the device.
        test_env = Environment()
        for dep_name in ("freetype", "harfbuzz", "fribidi"):
            libdir = os.path.join(
                self.dependencies[dep_name].package_folder, "lib"
            )
            if os.path.isdir(libdir):
                test_env.append("LD_LIBRARY_PATH", libdir)
        test_env.define("MESON_TESTTHREADS", "1")
        with test_env.vars(self).apply():
            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_libs(os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "raqm")
        self.cpp_info.set_property("cmake_file_name", "raqm")
        self.cpp_info.set_property("cmake_target_name", "raqm::raqm")
        self.cpp_info.libs = ["raqm"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = [
            "freetype::freetype",
            "harfbuzz::harfbuzz",
            "fribidi::fribidi",
        ]

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_ld_library_path():
        ld = os.environ.get("LD_LIBRARY_PATH", "")
        if ld:
            cleaned = ":".join(
                seg.strip() for seg in ld.split(":") if seg.strip()
            )
            if cleaned != ld:
                os.environ["LD_LIBRARY_PATH"] = cleaned

    def _resolve_tool(self, tool, llvm=True):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)

        candidates = []
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        candidates.append(f"llvm-{tool}" if llvm else tool)
        candidates.append(tool)

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

        raise ConanInvalidConfiguration(
            "required build tool was not found: %s" % tool
        )

    def _sign_shared_libs(self, libdir):
        """Re-sign versioned shared libraries for the OHOS loader.

        The linked .so carries a .codesign section that the device loader
        rejects after meson install (ld.so reports "library not found" even
        though the file sits in LD_LIBRARY_PATH). Removing the section and
        re-signing with binary-sign-tool makes the library loadable again —
        same approach as the harfbuzz recipe in this repository.
        """
        candidates = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        candidates += glob.glob(
            os.path.join(libdir, "**", "*.so.*"), recursive=True
        )
        shared_libraries = [
            library
            for library in sorted(set(candidates))
            if not os.path.islink(library)
            and os.path.isfile(library)
            and re.search(r"\.so\.\d+(?:\.\d+)+$", library)
        ]
        if not any(
            os.path.basename(library).startswith("libraqm.so.")
            for library in shared_libraries
        ):
            raise ConanInvalidConfiguration(
                "versioned libraqm shared library is missing under %s" % libdir
            )

        objcopy = self._resolve_tool("objcopy")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        for library in shared_libraries:
            signed_library = "%s.ohos-signed" % library
            if os.path.lexists(signed_library):
                raise ConanInvalidConfiguration(
                    "stale signed-library output exists: %s" % signed_library
                )
            mode = os.stat(library).st_mode
            try:
                self.run(
                    shlex.join([objcopy, "--remove-section", ".codesign", library])
                )
                self.run(
                    shlex.join(
                        [
                            signer,
                            "sign",
                            "-inFile",
                            library,
                            "-outFile",
                            signed_library,
                            "-selfSign",
                            "1",
                        ]
                    )
                )
                if not os.path.isfile(signed_library):
                    raise ConanInvalidConfiguration(
                        "signer did not create output: %s" % signed_library
                    )
                os.chmod(signed_library, mode)
                os.replace(signed_library, library)
            finally:
                if os.path.lexists(signed_library):
                    os.remove(signed_library)

        # Re-materialize the .so / .so.<major> aliases from the freshly
        # signed versioned library (meson installs symlinks; after the
        # in-place re-sign the aliases must point at real files again).
        for library in shared_libraries:
            stem, version = library.rsplit(".so.", 1)
            aliases = [f"{stem}.so.{version.split('.', 1)[0]}", f"{stem}.so"]
            for alias in aliases:
                if os.path.lexists(alias):
                    os.remove(alias)
                shutil.copy2(library, alias)
