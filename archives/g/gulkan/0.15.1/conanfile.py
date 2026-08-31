#!/usr/bin/env python3
"""Conan recipe — gulkan 0.15.1 (Vulkan utility library, GObject-based)

gulkan wraps Vulkan context creation / textures / buffers with GLib/GObject
types. Build system: Meson.

OHOS adaptation notes:
  - Vulkan loader: ohpcd registry has no published "vulkan-loader" package
    (its recipe is merged in main but publication stalled — platform wish-1927
    is pending human triage). HarmonyOS PC ships the Khronos loader as a
    system component at /system/lib64/libvulkan.so, so we generate a
    hand-written vulkan.pc (Cflags from published vulkan-headers, Libs
    pointing at the system loader) in the generators folder. The package
    itself does NOT ship libvulkan — no R26 pollution, consumers resolve it
    from the system at runtime.
  - Shaders (shaders/meson.build) require glslangValidator at configure time
    (glslc/shaderc absent) -> tool_requires glslang (published).
  - GResource compilation requires glib-compile-resources on PATH ->
    tool_requires glib as well as host requires.
  - meson_options.txt only defines api_doc/introspection; examples/tests
    subdirs are dependency-gated (glfw/shaderc/json-glib are optional and
    absent -> skipped automatically). Do NOT pass -Dexamples/-Dtests.

Task: contrib-521 (积分赛, claimed wanderlust_0823)
"""
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GulkanConan(ConanFile):
    name = "gulkan"
    version = "0.15.1"
    description = ("Vulkan utility library for creating contexts and managing "
                   "textures/buffers (GLib/GObject wrapper)")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xrdesktop/gulkan"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # transitive_headers: gulkan's PUBLIC headers include glib/gobject,
        # gdk-pixbuf, graphene and vulkan/vulkan.h, so consumers need them.
        self.requires("glib/2.84.0.1", transitive_headers=True,
                      transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True,
                      transitive_libs=True)
        self.requires("graphene/1.10.8", transitive_headers=True,
                      transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True,
                      transitive_libs=True)
        # headers only (build-scripts); the pc we hand-write points at them
        self.requires("vulkan-headers/vulkan-sdk-1.4.357.0",
                      transitive_headers=True)
        # glib2/2.88.0 (via graphene) pins zlib/1.3.1 (static, no -fPIC,
        # E005) while glib/gdk-pixbuf/cairo pull zlib/1.3.1.1 (-fPIC, E234).
        # Unify on 1.3.1.1 — same resolution as merged awf-gtk/4.2.0.
        self.requires("zlib/1.3.1.1", override=True)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")
        # glslangValidator for shaders/meson.build (no glslc on OHOS)
        self.tool_requires("glslang/vulkan-sdk-1.3.290.0")
        # NOTE: do NOT tool_require glib for glib-compile-resources! Its lib/
        # ships proxy-libintl.so.8; VirtualBuildEnv prepends it to
        # LD_LIBRARY_PATH, which (musl: LD_LIBRARY_PATH beats RUNPATH) shadows
        # the real gettext libintl that hnp python links — meson then dies
        # with "libintl_gettext: symbol not found". PATH-only injection
        # instead (see generate()).

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        # gnome.compile_resources() path: meson's find_tool() checks
        # [binaries] FIRST, then gio-2.0's pkgconfig var (which conan's
        # generated gio-2.0.pc lacks -> MesonException "Could not get
        # pkg-config variable" before ever falling back to PATH).
        # Register the tool explicitly from the host glib package.
        # NOTE: tool_requires(glib) is NOT an option: VirtualBuildEnv would
        # prepend glib/lib to LD_LIBRARY_PATH; its libintl.so.8 exports only
        # the g_*-prefixed proxy symbols and shadows the real gettext libintl
        # that hnp python needs (musl: LD_LIBRARY_PATH > RUNPATH), breaking
        # meson itself with "libintl_gettext: symbol not found".
        glib_pkg = self.dependencies["glib"].package_folder
        tc.binaries["glib-compile-resources"] = os.path.join(
            glib_pkg, "bin", "glib-compile-resources")
        # Force absolute binutils paths: MesonToolchain otherwise falls back
        # to bare 'llvm-ar' (resolved from global.conf/PATH), which is absent
        # from PATH on OHOS CI workers -> meson project() dies with
        # "Unknown linker(s): [['llvm-ar']]" (verified on PR #7121 build
        # 34233). Derive them from the configured compiler location.
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cc_path = ce.get("c") or ""
        bindir = os.path.dirname(cc_path) if os.sep in cc_path else ""
        if bindir:
            for key, names in (("ar", ("llvm-ar", "ar")),
                               ("ranlib", ("llvm-ranlib", "ranlib"))):
                for name in names:
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        tc.binaries[key] = cand
                        break
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.generate()

        # Hand-written vulkan.pc: meson dependency('vulkan') would otherwise
        # fail (no conan "vulkan" pkg in registry). Link the OHOS system
        # loader; headers come from the published vulkan-headers package.
        vh_dep = self.dependencies["vulkan-headers"]
        hdrs = vh_dep.package_folder
        # report the vulkan SDK/API version from the headers package so the
        # .pc Version never drifts from what we compile against.
        vh_ver = str(vh_dep.ref.version).replace("vulkan-sdk-", "")
        pc_path = os.path.join(self.generators_folder, "vulkan.pc")
        with open(pc_path, "w", encoding="utf-8") as f:
            f.write(
                "prefix=/system\n"
                "libdir=/system/lib64\n"
                f"includedir={hdrs}/include\n"
                "\n"
                "Name: Vulkan-Loader\n"
                "Description: Vulkan loader (HarmonyOS PC system component)\n"
                f"Version: {vh_ver}\n"
                "Cflags: -I${includedir}\n"
                "Libs: -L${libdir} -lvulkan\n"
            )

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Run the retained upstream tests (test_instance/device/client) that
        # do not need a GPU/ICD: vkCreateInstance works on the system Vulkan
        # loader (/system/lib64/libvulkan.so) without a physical device.
        meson.test()

    def package(self):
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"))
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))
        self._self_sign_elfs()

    def _self_sign_elfs(self):
        # OHOS enforces ELF code signing at load time (dlopen/exec of an ELF
        # whose .codesign section is zero-filled -> EACCES on HarmonyOS PC,
        # cf. "ELF must be signed or it cannot execute"). Sign locally with
        # selfSign when the SDK tool is present; keep the package runnable on
        # device without depending on the later release-pipeline step. Fully
        # guarded: never fails the build.
        if str(self.settings.os) != "OHOS":
            return
        import glob as _glob
        import shutil
        import subprocess
        tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(tool):
            self.output.info("binary-sign-tool absent; skipping self-sign")
            return
        pkg = self.package_folder
        targets = (_glob.glob(os.path.join(pkg, "lib", "*.so*")) +
                   _glob.glob(os.path.join(pkg, "bin", "*")))
        signed = 0
        for path in targets:
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            try:
                out = path + ".signed"
                r = subprocess.run(
                    [tool, "sign", "-selfSign", "1", "-signAlg",
                     "SHA256withECDSA", "-inFile", path, "-outFile", out],
                    capture_output=True, timeout=60)
                if r.returncode == 0 and os.path.isfile(out):
                    shutil.copymode(path, out)
                    os.replace(out, path)
                    signed += 1
                elif os.path.isfile(out):
                    os.remove(out)  # don't ship a half-written artifact
            except Exception as e:  # noqa: BLE001 - best effort by design
                self.output.warn(f"self-sign skipped for {path}: {e}")
        self.output.info(f"self-signed {signed} ELF file(s) in package")

    def package_info(self):
        # matches the installed lib/pkgconfig/gulkan-0.15.pc
        self.cpp_info.set_property("pkg_config_name", "gulkan-0.15")
        self.cpp_info.libs = ["gulkan-0.15"]
        self.cpp_info.includedirs = [os.path.join("include", "gulkan-0.15")]
        # NOTE: cpp_info.requires intentionally not set — gulkan public
        # headers expose GObject/Vk types, so the full dependency set must
        # propagate to consumers; default propagation covers component
        # naming differences across the glib-family packages.
