#!/usr/bin/env python3
"""Conan recipe — boxfort 0.1.2 (Meson).

BoxFort is the portable process-sandboxing C library powering Criterion.
Upstream builds a static library only (src/meson.build hardcodes
`static_library`), so this recipe offers no shared option.

Key adaptation points (all in patches/, all runtime-detected with pure
POSIX — no platform macros, so upstream behavior is untouched wherever
the probe succeeds, e.g. stock Linux):

- Code-page integrity (e.g. OpenHarmony XPM) kills or rejects any write
  to executable pages: mprotect(R|W|X) fails with EINVAL, mprotect(R|W)
  on a text page is killed with SIGSEGV, /proc/self/mem writes fail with
  EPERM, and MAP_FIXED over an executable mapping is fatal. Upstream's
  sandbox handshake re-execs the process and patches `main`'s machine
  code with a trampoline, which cannot work under that policy. The
  patched code probes text-page writability once (in a disposable
  forked child) and, when it is unavailable, runs the sandbox function
  directly in the forked child and exits with its return value
  (0003-src-sandbox-posix.c.patch, 0002/0004 context helpers).
- User-space VA can be capped near 512 GiB (39 bits, e.g. OpenHarmony):
  MAP_FIXED beyond ~0x8000000000 fails with EINVAL, so the arena
  placement window probes the default base once and falls back to
  [4 GiB, ~259 GiB) when rejected (0001-src-arena.c.patch).

No external Conan dependencies: upstream only needs the system thread
library plus optional librt/libm probes, all satisfied by the OHOS musl.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class BoxfortConan(ConanFile):
    name = "boxfort"
    version = "0.1.2"
    description = "A simple, cross-platform process sandboxing C library"
    license = "MIT"
    homepage = "https://github.com/Snaipe/BoxFort"
    url = "https://github.com/Snaipe/BoxFort"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # conan.tools.meson has no meson_layout in Conan 2.29; basic_layout
        # is the proven bubblewrap pattern for meson recipes here.
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # R26: static library; upstream only supports static anyway.
        tc.project_options["default_library"] = "static"
        # Build the upstream samples/tests inside the package build so the
        # meson test suite (4 sample executables) runs against the packaged
        # sources; the cram functional test stays unregistered because the
        # cram program is not installed on this environment (upstream marks
        # it `required: false`).
        tc.project_options["tests"] = "true"
        tc.project_options["samples"] = "true"
        tc.generate()
        self._inject_meson_tools()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Upstream test suite: the 4 sample executables registered by
            # sample/meson.build (nested, callback, context, timeout).
            self.run('meson test -C "{}" --print-errorlogs'.format(
                self.build_folder))

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["boxfort"]
        # Mirror upstream's pkg-config extra_cflags: consumers of the
        # static library build with BXF_STATIC_LIB so BXF_API stays a
        # plain symbol instead of a visibility attribute.
        self.cpp_info.defines = ["BXF_STATIC_LIB=1"]
        self.cpp_info.set_property("cmake_file_name", "boxfort")
        self.cpp_info.set_property("cmake_target_name", "boxfort::boxfort")

    # ── helpers ──────────────────────────────────────────────────────────

    def _build_environment(self):
        environment = Environment()
        # /var/tmp does not exist on OHOS and root '/' is read-only; give
        # tools a writable temp area inside the build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # CI worker: SDK lld depends on libxml2.so.16 in the SDK llvm/lib
        # dir; without it meson's linker probe fails. Prepend the SDK lib
        # dir (version-agnostic glob) so lld resolves its own libxml2.
        for sdk_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")):
            environment.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return environment

    def _inject_meson_tools(self):
        """Inject ar/ranlib/pkg-config absolute paths into the meson
        machine file (bubblewrap-proven pattern)."""
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            sdk_bindirs = [bindir]
            ndk_home = os.environ.get("OHOS_NDK_HOME")
            if ndk_home:
                sdk_bindirs.append(os.path.join(ndk_home, "llvm", "bin"))
            for sdk in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin")):
                sdk_bindirs.append(sdk)
            for directory in sdk_bindirs:
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")

            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and "\npkg-config =" not in content \
                    and "\npkgconfig =" not in content:
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1
                )
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
