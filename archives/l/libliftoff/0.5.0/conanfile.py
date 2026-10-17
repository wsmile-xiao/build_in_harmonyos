#!/usr/bin/env python3
"""Conan recipe — libliftoff 0.5.0 (lightweight KMS plane library, Meson).

libliftoff allocates DRM/KMS planes so that a compositor can scan out texture
planes directly instead of compositing them, which lets the display controller
skip work.  wlroots uses it from its DRM backend (`backend/drm/libliftoff.c`),
guarded by `dependency('libliftoff', version: '>=0.4.0')`.

Version note: this repository previously carried an `archives/l/libliftoff/0.1.0`
placeholder (manifest + notes only, no recipe, empty sha256).  0.1.0 cannot
satisfy wlroots' `>=0.4.0` requirement, and 0.5.0 is the latest upstream release,
so 0.5.0 is adapted here; the 0.1.0 placeholder is left untouched.

Adapted to HarmonyOS PC (aarch64).  The upstream test suite runs against a *mock*
libdrm, so it needs no DRM device — which matters here, because this machine has
none (see notes.md).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibliftoffConan(ConanFile):
    name = "libliftoff"
    version = "0.5.0"
    description = "Lightweight KMS plane library (DRM plane allocation)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/emersion/libliftoff"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libliftoff drives DRM/KMS and requires a Linux kernel, not {self.settings.os}")

    def requirements(self):
        # meson.build:30 — `dependency('libdrm', version: '>= 2.4.108')`.
        # The public header includes <xf86drmMode.h> and <xf86drm.h>
        # (include/libliftoff.h:8), so libdrm is part of libliftoff's public
        # interface: consumers must inherit its include dirs and its library,
        # exactly as upstream's own libliftoff.pc records
        # (`Requires.private: libdrm >= 2.4.108`).
        self.requires("libdrm/2.4.133", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # tar_format in conandata.yml is only for validation; get() does not
        # accept it, so pass url/sha256 explicitly.
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"],
            sha256=source_data.get("sha256", ""), strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # libdrm is resolved through pkg-config (`dependency('libdrm')`,
        # meson.build:30), so its .pc must be generated for this build.
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["c_std"] = "c11"
        # Upstream defaults `werror=true`; this toolchain (clang 15) raises a
        # different warning set than upstream's CI.  Diagnostics stay visible in
        # the build log.
        tc.project_options["werror"] = "false"
        # Upstream's whole test suite keeps its assertions (and side effects) in
        # assert(...): test_alloc.c has 18, test_prop.c 27, test_priority.c 4.
        # Release adds -DNDEBUG, assert() becomes ((void)0) and the suite would
        # report 57 green tests having executed nothing — upstream even ships a
        # sentinel (test/check_ndebug.c) that fails the run in exactly that case.
        tc.project_options["b_ndebug"] = "false"
        # The libdrm wrap fallback would try to download libdrm from the network;
        # the conan requirement supplies it instead.
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_ar_ranlib()
        self._ensure_tmpdir()

    def build(self):
        meson = Meson(self)
        meson.configure()
        self._force_live_assertions()
        meson.build()
        # The upstream suite links a mock libdrm (test/libdrm_mock.c) through
        # meson's `override_dependency`, so it exercises the real plane-allocation
        # code without touching a DRM device node — the only way to run it here.
        meson.test()

    def _force_live_assertions(self):
        """Pin b_ndebug=false after configure, then prove it took effect.

        Asking for it through `project_options` is not enough: MesonToolchain
        writes the requested value into the machine file, but conan also passes
        `--buildtype=release` on the setup command line and meson then re-derives
        b_ndebug from the build type.  Measured inside this build:
        `werror`/`default_library`/`c_std` all arrived as requested while
        `b_ndebug` came out `'true'`.

        That matters because upstream keeps every assertion (and their side
        effects) inside assert(): test_alloc.c has 18, test_prop.c 27 and
        test_priority.c 4.  Under -DNDEBUG, assert() expands to ((void)0) and the
        suite reports 57 green tests that executed nothing.  Upstream ships a
        sentinel for exactly this — test/check_ndebug.c fails when NDEBUG is
        defined, which is how this was caught — so the tests must be run with
        assertions live for the tally to mean anything.
        """
        build_dir = self.build_folder
        self.run(f'meson configure "{build_dir}" -Db_ndebug=false', env="conanbuild")

        info = os.path.join(build_dir, "liftoff-buildoptions.json")
        self.run(f'meson introspect "{build_dir}" --buildoptions > "{info}" 2>&1',
                 env="conanbuild", ignore_errors=True)
        effective = {}
        try:
            with open(info, encoding="utf-8") as handle:
                for entry in json.load(handle):
                    effective[entry.get("name")] = entry.get("value")
        except (OSError, ValueError) as exc:
            raise ConanException(f"cannot verify meson options: {exc}")

        for key in ("buildtype", "b_ndebug", "werror", "default_library"):
            self.output.info(f"LIFTOFF_MESON_OPTION {key} = {effective.get(key)!r}")
        # meson reports b_ndebug as the string "false" (combo option).
        if str(effective.get("b_ndebug")).strip().lower() != "false":
            raise ConanException(
                f"b_ndebug is {effective.get('b_ndebug')!r}: upstream assertions "
                "would be compiled out and the test tally would be meaningless")

    def package(self):
        Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            self._resign_installed_elfs()

    def package_info(self):
        # meson.build:64 — `pkgconfig.generate(liftoff_lib, filebase: 'libliftoff')`,
        # so the artifact is libliftoff.so and the .pc is libliftoff.pc.
        self.cpp_info.libs = ["liftoff"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "libliftoff")
        self.cpp_info.set_property("cmake_file_name", "libliftoff")
        self.cpp_info.set_property("cmake_target_name", "libliftoff::libliftoff")

    # ── helpers ───────────────────────────────────────────────────────

    def _ensure_tmpdir(self):
        """HarmonyOS /tmp is a read-only erofs — point TMPDIR somewhere writable."""
        tmpdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_ar_ranlib(self):
        """Point AR/RANLIB at the OHOS LLVM tools from the Conan profile."""
        compiler_executables = (
            self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            or {}
        )
        cc = compiler_executables.get("c") or ""
        ar = compiler_executables.get("ar") or (
            os.path.join(os.path.dirname(cc), "llvm-ar") if cc else "")
        ranlib = compiler_executables.get("ranlib") or (
            os.path.join(os.path.dirname(cc), "llvm-ranlib") if cc else "")
        if ar:
            os.environ["AR"] = ar
        if ranlib:
            os.environ["RANLIB"] = ranlib

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resign_installed_elfs(self):
        """Re-sign every installed ELF for the OHOS loader.

        `meson install` rewrites the RUNPATH of each ELF it installs, so the
        installed copy no longer matches the `.codesign` section embedded at link
        time and the loader refuses to map it (the failure reads
        "Error loading shared library ... " with an empty reason).  Same failure
        and fix as the wlroots and libinput recipes.
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")
        for root, _dirs, files in os.walk(self.package_folder):
            for name in sorted(files):
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path):
                    continue
                if not self._is_elf(path):
                    continue
                self.run(f'"{objcopy}" --remove-section .codesign "{path}"')
                self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
                         f'-selfSign 1')
