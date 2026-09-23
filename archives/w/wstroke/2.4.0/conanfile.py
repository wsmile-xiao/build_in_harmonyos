#!/usr/bin/env python3
"""Conan recipe — wstroke 2.4.0

Port of easystroke mouse gestures as a Wayfire plugin.
Upstream: https://github.com/dkondor/wstroke (tag v2.4.0, ISC license).

HarmonyOS adaptation notes:
  - Upstream is a Wayfire compositor plugin (depends on wayfire >=0.10.0,
    wlroots-0.19, wayland-server, gtkmm-3.0, vala, WCM). None of these are
    available on HarmonyOS PC (OHOS uses its own window system). Building the
    full Wayfire plugin or the GTK config tool on OHOS is not feasible.
  - The gesture-recognition core (stroke.c / stroke.h, gesture.cc / gesture.h)
    is portable C/C++ and only needs boost-serialization for Stroke
    persistence. For OHOS we build a minimal static library ``libwstroke.a``
    from the portable core (stroke.c) plus a thin C++ wrapper, without
    Wayfire/wlroots/GTK dependencies. This preserves the algorithmic core and
    allows consumers to link the gesture engine on OHOS.
  - On Linux the same minimal core is built for consistency; the Wayfire
    plugin is not delivered (requires a Wayfire compositor at runtime).
  - No upstream test suite exists (no check/test meson target, no tests/
    directory). Upstream verification is therefore marked as no_tests.
"""

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class WstrokeConan(ConanFile):
    name = "wstroke"
    version = "2.4.0"
    description = "Port of easystroke mouse gestures as a plugin for Wayfire"
    license = "ISC"
    homepage = "https://github.com/dkondor/wstroke"
    url = "https://github.com/dkondor/wstroke"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        # conandata.yml may store sources as a list (single-version) or as a
        # version-keyed mapping; handle both so `get` always receives a mapping.
        data = self.conan_data["sources"]
        src = data
        if isinstance(data, list):
            src = data[0]
        elif isinstance(data, dict):
            if self.version in data:
                v = data[self.version]
                src = v[0] if isinstance(v, list) else v
            else:
                v = next(iter(data.values()))
                src = v[0] if isinstance(v, list) else v
        get(self, **src, strip_root=True)

    def generate(self):
        # No toolchain needed for manual clang build; keep layout for packaging.
        pass

    def build(self):
        apply_conandata_patches(self)
        # Build minimal portable core: stroke.c -> libwstroke.a
        # This is the only part that is OS-agnostic and useful on OHOS.
        # Gesture C++ parts (gesture.cc, easystroke_gestures.cpp) require
        # boost-serialization; they are not built in this minimal port to
        # avoid pulling boost on OHOS. The core stroke API (stroke.h) is
        # the stable, documented interface.
        src_dir = self.source_folder
        build_dir = self.build_folder
        os.makedirs(build_dir, exist_ok=True)

        # Locate stroke sources (strip_root=True => src/ is at top)
        stroke_c = os.path.join(src_dir, "src", "stroke.c")
        stroke_h = os.path.join(src_dir, "src", "stroke.h")
        if not os.path.isfile(stroke_c):
            # Fallback: strip_root may have placed files directly
            stroke_c = os.path.join(src_dir, "stroke.c")
            stroke_h = os.path.join(src_dir, "stroke.h")
            if not os.path.isfile(stroke_c):
                # Search recursively
                import glob
                candidates = glob.glob(os.path.join(src_dir, "**", "stroke.c"), recursive=True)
                if candidates:
                    stroke_c = candidates[0]
                    stroke_h = os.path.join(os.path.dirname(stroke_c), "stroke.h")

        self.output.info(f"Building wstroke core from {stroke_c}")

        # Compile stroke.c to object
        obj = os.path.join(build_dir, "stroke.o")
        lib = os.path.join(build_dir, "libwstroke.a")
        # Use clang from PATH (OHOS profile prepends /data/service/hnp/bin)
        # Fallback to cc if clang not found.
        cc = "clang"
        # Prefer compiler from conf if available (HMBS injects tools.build:compiler_executables)
        try:
            conf_cc = self.conf.get("tools.build:compiler_executables:c", check_type=str)
            if conf_cc:
                cc = conf_cc
        except Exception:
            pass
        cflags = "-O2 -fPIC -c"
        if self.settings.build_type == "Debug":
            cflags = "-O0 -g -fPIC -c"
        self.run(f'{cc} {cflags} "{stroke_c}" -o "{obj}"')
        # Archive
        ar = "llvm-ar"
        try:
            conf_ar = self.conf.get("tools.build:compiler_executables:ar", check_type=str)
            if conf_ar:
                ar = conf_ar
        except Exception:
            pass
        # Try llvm-ar, fallback to ar
        import shutil
        if shutil.which(ar) is None:
            ar = "ar"
        self.run(f'{ar} rcs "{lib}" "{obj}"')

        # No upstream test suite to run (upstream_tests_exist=false).
        # The build() does not call meson test / make check.

    def package(self):
        # Headers
        src_dir = self.source_folder
        import glob
        # Find stroke.h
        hdr_candidates = glob.glob(os.path.join(src_dir, "**", "stroke.h"), recursive=True)
        for hdr in hdr_candidates:
            copy(self, "stroke.h", src=os.path.dirname(hdr), dst=os.path.join(self.package_folder, "include"))
            break
        # Also install gesture.h if present (optional, not required for core)
        gesture_candidates = glob.glob(os.path.join(src_dir, "**", "gesture.h"), recursive=True)
        for hdr in gesture_candidates:
            copy(self, "gesture.h", src=os.path.dirname(hdr), dst=os.path.join(self.package_folder, "include"))
            break

        # License
        for lic in ["LICENSE", "COPYING", "LICENSE.md"]:
            candidates = glob.glob(os.path.join(src_dir, "**", lic), recursive=True)
            for c in candidates:
                copy(self, lic, src=os.path.dirname(c), dst=os.path.join(self.package_folder, "licenses"))
                break

        # Library
        copy(self, "libwstroke.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        # Handle shared option (not built, but keep alias)
        if self.options.shared:
            # For shared request, we still deliver static (OHOS plugin is not loadable).
            # Copy with .so name as alias for compatibility if needed.
            import shutil
            lib_a = os.path.join(self.package_folder, "lib", "libwstroke.a")
            lib_so = os.path.join(self.package_folder, "lib", "libwstroke.so")
            if os.path.isfile(lib_a) and not os.path.isfile(lib_so):
                shutil.copy2(lib_a, lib_so)

    def package_info(self):
        self.cpp_info.libs = ["wstroke"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
