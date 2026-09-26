#!/usr/bin/env python3
"""Conan recipe - libwacom 2.13.0 (Meson).

libwacom is a library to identify wacom tablets and their model-specific
features (data-driven: DB of tablet descriptions in data/*.tablet).

OHOS adaptation notes:
- Dependencies: libgudev/238 (gudev-1.0), glib (via libgudev chain),
  libevdev/1.13.7. PkgConfigDeps supplies gudev-1.0.pc / glib-2.0.pc /
  libevdev.pc.
- Meson maps OHOS to host_machine.system() == 'harmonyos'; libwacom's
  tools/debug paths use plain libc, no platform fork needed.
- Upstream C tests (test-load, test-dbverify, test-tablet-validity,
  test-stylus-validity, test-ltversion) run on the local arm64 OHOS
  runner via `meson test`; the pytest suite (4 files) needs
  pytest-3 + pyudev + python-libevdev modules not present on OHOS ->
  not registered (see PR body for the per-case exemption).
- The `files-in-git` test only works in a git checkout (checks every
  data file is tracked by git); tarball source -> not applicable.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class LibwacomConan(ConanFile):
    name = "libwacom"
    version = "2.13.0"
    description = "Library to identify Wacom tablets and their features"
    license = "HPND"
    homepage = "https://github.com/linuxwacom/libwacom"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
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
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("libgudev/238")
        self.requires("libevdev/1.13.7")
        # glib comes transitively through libgudev (glib/2.84.0.1); keep
        # the explicit pin so PkgConfigDeps emits glib-2.0.pc/gobject-2.0.pc.

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def _ensure_tmpdir(self):
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _inject_meson_binaries(self):
        """Inject ar/ranlib/pkg-config into conan_meson_native.ini
        (libgudev 238 recipe precedent)."""
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_lines = []
            for line in content.splitlines(True):
                new_lines.append(line)
                if line.strip() == "[binaries]":
                    if ar and "\nar =" not in content:
                        new_lines.append("ar = '%s'\n" % ar)
                    if rl and "\nranlib =" not in content:
                        new_lines.append("ranlib = '%s'\n" % rl)
                    if pkg_config and "\npkg-config =" not in content:
                        new_lines.append("pkg-config = '%s'\n" % pkg_config)
            new_content = "".join(new_lines)
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)

    def _fix_glib_pc_files(self):
        """glib .pc files need glib_mkenums for meson gnome modules
        (libgudev 238 recipe precedent)."""
        gens = self.generators_folder
        glib_prefix = None
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if os.path.isfile(glib_pc):
            with open(glib_pc) as f:
                for line in f:
                    if line.startswith("prefix="):
                        glib_prefix = line.strip().split("=", 1)[1]
                        glib_prefix = glib_prefix.strip('"').strip("'")
                        break
        if not glib_prefix:
            return
        bindir = os.path.join(glib_prefix, "bin")
        for pc_name in ("glib-2.0.pc", "gobject-2.0.pc",
                        "gmodule-2.0.pc", "gthread-2.0.pc", "gio-2.0.pc"):
            pc_path = os.path.join(gens, pc_name)
            if not os.path.isfile(pc_path):
                continue
            with open(pc_path) as f:
                content = f.read()
            modified = False
            if "glib_mkenums" not in content:
                content += f"\nglib_genmarshal={bindir}/glib-genmarshal\n"
                content += f"gobject_query={bindir}/gobject-query\n"
                content += f"glib_mkenums={bindir}/glib-mkenums\n"
                modified = True
            if modified:
                with open(pc_path, "w") as f:
                    f.write(content)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_glib_pc_files()
        self._ensure_tmpdir()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["tests"] = "enabled"
        tc.project_options["documentation"] = "disabled"
        tc.project_options["udev-dir"] = "lib/udev"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        self._ensure_tmpdir()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream C test suite via `meson test` (local arm64
        OHOS runner). Exemptions: files-in-git (git-checkout-only) and
        the pytest suite (needs pytest-3/pyudev/python-libevdev)."""
        from conan.tools.env import Environment

        test_env = Environment()
        test_env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        with test_env.vars(self).apply():
            self.run(
                "meson test --no-rebuild -t 120 "
                "test-load test-dbverify test-tablet-validity "
                "test-stylus-validity test-ltversion --print-errorlogs"
            )

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """OHOS ELF codesign (binary-sign-tool), libgudev/glib precedent."""
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            return
        libdir = os.path.join(self.package_folder, "lib")
        for root, _, files in os.walk(libdir):
            for filename in files:
                if ".so" not in filename:
                    continue
                path = os.path.join(root, filename)
                if os.path.islink(path):
                    continue
                subprocess.run([objcopy, "--remove-section", ".codesign", path], check=False)
                signed = path + ".signed"
                subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"], check=True)
                os.replace(signed, path)
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libwacom")
        self.cpp_info.set_property("pkg_config_name", "libwacom")
        self.cpp_info.libs = ["wacom"]
        self.cpp_info.includedirs = ["include/libwacom-1.0"]
        self.cpp_info.system_libs = ["m"]
